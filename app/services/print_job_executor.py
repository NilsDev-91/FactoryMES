from typing import List, Optional
import logging
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.models.core import Job, Printer, JobStatusEnum
from app.services.filament_manager import FilamentManager
from app.services.printer.commander import PrinterCommander
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("PrintJobExecutionService")

class PrintJobExecutionService:
    def __init__(
        self,
        session: AsyncSession,
        filament_manager: FilamentManager,
        printer_commander: PrinterCommander
    ):
        self.session = session
        self.filament_manager = filament_manager
        self.printer_commander = printer_commander

    async def execute_print_job(self, job_id: int, printer_serial: str) -> None:
        """
        Orchestrates the safe execution of a print job.
        1. Loads Job and Printer data.
        2. Validates filament colors using FilamentManager (FMS).
        3. Dispatches via PrinterCommander if valid.
        """
        logger.info(f"Attempting to execute Job {job_id} on Printer {printer_serial}")

        # 1. Fetch Data
        job_query = select(Job).where(Job.id == job_id)
        result = await self.session.exec(job_query)
        job = result.first()

        if not job:
            logger.error(f"Job {job_id} not found.")
            raise ValueError(f"Job {job_id} not found.")

        # Concurrency Check: Ensure job is still pending
        await self.session.refresh(job)
        if job.status != JobStatusEnum.PENDING:
            msg = f"Job {job_id} is already in state {job.status}. Aborting execution."
            logger.warning(msg)
            return # Bail out gracefully

        # Eager load printer with AMS slots
        printer_query = (
            select(Printer)
            .where(Printer.serial == printer_serial)
            .options(selectinload(Printer.ams_slots))
        )
        result = await self.session.exec(printer_query)
        printer = result.first()
        
        if not printer:
            logger.error(f"Printer {printer_serial} not found.")
            raise ValueError(f"Printer {printer_serial} not found.")

        # Safety Latch Check
        if not printer.is_plate_cleared:
            msg = f"Safety Latch ENGAGED: Printer {printer_serial} plate is not cleared."
            logger.warning(msg)
            # Do NOT fail the job. Just stop execution attempt.
            # The worker's queue processor should catch this.
            raise ValueError(msg)

        # 2. The Guardian Check (FMS)
        # Extract target hex from job requirements
        target_hex = None
        if job.filament_requirements:
            # Assumes filament_requirements is a list of dicts or a dict
            reqs = job.filament_requirements
            if isinstance(reqs, list) and reqs:
                target_hex = reqs[0].get("color_hex") or reqs[0].get("hex_color") or reqs[0].get("color")
            elif isinstance(reqs, dict):
                 target_hex = reqs.get("color_hex") or reqs.get("hex_color") or reqs.get("color")

        if not target_hex:
            logger.warning(f"Job {job_id} has no filament requirements (target_hex). Skipping FMS check.")
            # Depending on policy, we might fail or allow.
            job.status = JobStatusEnum.FAILED
            job.error_message = "Missing filament requirements"
            await self.session.commit()
            raise ValueError("Missing filament requirements for FMS check.")

        match_slot_idx = await self.filament_manager.find_matching_slot(printer.ams_slots, target_hex)

        # 3. Branching Logic
        if match_slot_idx is None:
            # IF NO MATCH
            msg = f"Delta E verification failed for Job {job_id} on Printer {printer_serial}. Target: {target_hex}"
            logger.warning(msg)
            
            # Do NOT fail the job permanently. Leave it PENDING so it can be retried 
            # (e.g. if filament is changed or another printer becomes available).
            # job.status = JobStatusEnum.FAILED <--- DISABLED
            # job.error_message = "MATERIAL_MISMATCH: " + msg
            # await self.session.commit()
            
            # Raise domain exception to stop execution here
            raise ValueError("MATERIAL_MISMATCH: " + msg) 

        else:
            # IF MATCH FOUND
            logger.info(f"Match found for Job {job_id} in Slot {match_slot_idx} (Delta E < 5.0).")
            
            # Construct MQTT Payload (handled by commander, we just pass mapping)
            # The commander expects a LIST of ints for ams_mapping.
            # CRITICAL FIX: The 3MF file might contain hardcoded tool commands (e.g. T2).
            # We must map ALL potential virtual tools (0-15) to the selected physical slot
            # to override the slicer's default assignment.
            ams_mapping = [match_slot_idx] * 16

            # DEBUG LOGGING (High Visibility)
            logger.error(f"🖨️ DISPATCHING JOB {job_id}:")
            logger.error(f"   Target: {target_hex}")
            logger.error(f"   FMS Match: Slot {match_slot_idx} (Index)")
            logger.error(f"   Mapping Sent: {ams_mapping}")
            
            try:
                await self.printer_commander.start_job(printer, job, ams_mapping)
                
                # Success Update
                # Refresh to ensure we don't overwrite other updates
                await self.session.refresh(job)
                await self.session.refresh(printer)

                job.status = JobStatusEnum.PRINTING 
                
                # ENGAGE SAFETY LATCH (Plate is now dirty/occupied)
                printer.is_plate_cleared = False
                self.session.add(printer)
                
                await self.session.commit()
                
            except Exception as e:
                logger.error(f"Failed to dispatch Job {job_id}: {e}")
                job.status = JobStatusEnum.FAILED
                job.error_message = str(e)
                await self.session.commit()
                raise e