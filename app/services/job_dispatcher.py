
import logging
from typing import List, Optional, Tuple
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Printer, Job, PrinterStatusEnum, JobStatusEnum, PrinterTypeEnum
from app.services.logic.color_matcher import color_matcher
from app.services.printer.commander import PrinterCommander

logger = logging.getLogger("JobDispatcher")

class JobDispatcher:
    """
    FMS Job Dispatcher - Phase 9
    Handles intelligent routing of jobs to printers based on active AMS telemetry.
    """
    
    def __init__(self):
        self.commander = PrinterCommander()

    async def dispatch_next_job(self, session: AsyncSession):
        """
        Main entry point for dispatching.
        Fetches idle printers and pending jobs, then attempts to match them.
        """
        # 1. Fetch Idle & Ready Printers
        printer_stmt = (
            select(Printer)
            .where(Printer.current_status == PrinterStatusEnum.IDLE)
            .where(Printer.is_plate_cleared == True)
            .options(selectinload(Printer.ams_slots))
        )
        printers = (await session.execute(printer_stmt)).scalars().all()
        
        if not printers:
            logger.debug("No idle and cleared printers available.")
            return

        # 2. Fetch Pending Jobs (by priority)
        job_stmt = (
            select(Job)
            .where(Job.status == JobStatusEnum.PENDING)
            .order_by(Job.priority.desc())
        )
        pending_jobs = (await session.execute(job_stmt)).scalars().all()
        
        if not pending_jobs:
            logger.debug("No pending jobs in queue.")
            return

        logger.info(f"Dispatching: {len(printers)} printers vs {len(pending_jobs)} jobs.")

        # 3. Match Loop
        for job in pending_jobs:
            # Basic Requirement Check (Job must have filament requirements)
            if not job.filament_requirements:
                logger.warning(f"Job {job.id} has no filament requirements! Skipping.")
                continue

            for printer in printers:
                # Rule: Capability (Continuous -> A1)
                # We check job metadata or product associated with it
                # For this implementation, we assume continuous jobs are marked in metadata
                is_continuous = job.job_metadata.get("is_continuous", False)
                if is_continuous and printer.type != PrinterTypeEnum.A1:
                    continue

                # Rule: Filament Matching
                match_result = self._find_matching_ams_slot(printer, job)
                if match_result:
                    slot_id, ams_mapping = match_result
                    logger.info(f"MATCH FOUND: Job {job.id} -> Printer {printer.serial} (Slot ID {slot_id})")
                    
                    # 4. Trigger Action
                    await self._assign_and_launch(session, job, printer, ams_mapping)
                    
                    # Remove printer from availability list for this cycle
                    printers.remove(printer)
                    break # Move to next job

    def _find_matching_ams_slot(self, printer: Printer, job: Job) -> Optional[Tuple[int, List[int]]]:
        """
        Finds a slot that matches the job's primary filament requirement.
        Returns (slot_id, ams_mapping) or None.
        """
        # Assuming single-material job for now as per "slot_id" requirement
        # Simple Case: Job.filament_requirements[0]
        try:
            req = job.filament_requirements[0]
            req_material = req.get("material")
            req_color = req.get("hex_color") or req.get("color")
        except (IndexError, KeyError):
            return None

        for slot in printer.ams_slots:
            # Rule: Material Match
            if not slot.material or slot.material.upper() != req_material.upper():
                continue
            
            # Rule: Color Match (Delta E < 5.0)
            if color_matcher.is_color_match(req_color, slot.color_hex):
                # We found a match!
                # ams_mapping for Sanitized 3MF (T0 Master)
                # Index 0 is the physical slot (1-based for Bambu)
                ams_mapping = [slot.slot_id + 1] 
                return slot.slot_id, ams_mapping
                
        return None

    async def _assign_and_launch(self, session: AsyncSession, job: Job, printer: Printer, ams_mapping: List[int]):
        """Assignment and starting logic."""
        try:
            # Phase 8 Logic: Lock status to prevent double-start
            job.status = JobStatusEnum.UPLOADING
            job.assigned_printer_serial = printer.serial
            printer.current_status = PrinterStatusEnum.PRINTING # Mark as busy immediately
            
            session.add(job)
            session.add(printer)
            await session.commit()
            
            # Start via Commander
            # Note: Commander expects List[int] mapping
            await self.commander.start_job(printer, job, ams_mapping)
            
            # Final Status Update (Normally handled by MQTT Worker, but we set it here for immediate UI feedback)
            job.status = JobStatusEnum.PRINTING
            session.add(job)
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to launch Job {job.id} on {printer.serial}: {e}")
            job.status = JobStatusEnum.FAILED
            job.error_message = str(e)
            printer.current_status = PrinterStatusEnum.IDLE # Release printer
            session.add(job)
            session.add(printer)
            await session.commit()

# Singleton
job_dispatcher = JobDispatcher()
