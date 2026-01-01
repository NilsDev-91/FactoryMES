from typing import List, Optional
import logging
from pathlib import Path
from datetime import datetime, timezone
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.core import Job, Printer, JobStatusEnum, PrinterStatusEnum, ClearingStrategyEnum
from app.services.filament_manager import FilamentManager
from app.services.printer.commander import PrinterCommander
from app.services.production.bed_clearing_service import BedClearingService

logger = logging.getLogger("PrintJobExecutionService")

class PrintJobExecutionService:
    def __init__(
        self,
        session: AsyncSession,
        filament_manager: FilamentManager,
        printer_commander: PrinterCommander,
        bed_clearing_service: Optional[BedClearingService] = None
    ):
        self.session = session
        self.filament_manager = filament_manager
        self.printer_commander = printer_commander
        self.bed_clearing_service = bed_clearing_service or BedClearingService()

    async def fetch_next_job(self, printer_serial: str) -> Optional[Job]:
        """
        Retrieves the next eligible job for a specific printer (PULL Strategy).
        Implements 'Peeking' logic: Skips jobs that do not match loaded filaments.
        """
        # 1. Get Printer State for validation
        printer_query = (
            select(Printer)
            .where(Printer.serial == printer_serial)
            .options(selectinload(Printer.ams_slots))
        )
        printer = (await self.session.exec(printer_query)).first()
        if not printer:
            return None

        # 2. Fetch PENDING Jobs
        # Order by Priority DESC, CreatedAt ASC
        stmt = (
            select(Job)
            .where(Job.status == JobStatusEnum.PENDING)
            .order_by(Job.priority.desc(), Job.created_at.asc())
        )
        jobs = (await self.session.exec(stmt)).all()
        
        logger.info(f"Peeking through {len(jobs)} pending jobs for Printer {printer_serial}")

        for job in jobs:
            # Check Explicit Assignment
            if job.assigned_printer_serial:
                if job.assigned_printer_serial != printer_serial:
                    continue # Assigned to someone else
                
                # Assigned to US. Must check compatibility.
                # If incompatible, we CANNOT skip it (it's assigned). 
                # We must flag the printer or warn.
                if not self.filament_manager.can_printer_print_job(printer, job):
                    logger.warning(f"Job {job.id} explicitly assigned to {printer_serial} but incompatible filament. Requires User Attention.")
                    # Optional: printer.current_status = "ATTENTION_REQUIRED"
                    continue # Cannot print right now
            
            # Unassigned (or assigned to us and we are checking compatibility)
            # Check Compatibility (The Peek)
            if self.filament_manager.can_printer_print_job(printer, job):
                logger.info(f"Job {job.id} matched for Printer {printer_serial}. Ready to pull.")
                return job
            else:
                 logger.debug(f"Job {job.id} skipped for {printer_serial} (Filament Mismatch).")

        return None

    async def execute_print_job(self, job_id: int, printer_serial: str) -> None:
        """
        Orchestrates the safe execution of a print job.
        1. Loads Job and Printer data.
        2. Validates filament colors using FilamentManager (FMS).
        3. Dispatches via PrinterCommander if valid.
        """
        from app.core.exceptions import FilamentMismatchError
        
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

        # Safety Latch Check & State Lock
        # STRICT LOCK: Cannot print if clearing bed or awaiting clearance
        if printer.current_status in [PrinterStatusEnum.CLEARING_BED, PrinterStatusEnum.AWAITING_CLEARANCE]:
             msg = f"Printer {printer_serial} is in {printer.current_status}. Cannot execute job."
             logger.warning(msg)
             from app.core.exceptions import PrinterBusyError
             raise PrinterBusyError(printer_serial, printer.current_status)

        if not printer.is_plate_cleared:
            msg = f"Safety Latch ENGAGED: Printer {printer_serial} plate is not cleared."
            logger.warning(msg)
            # Do NOT fail the job. Just stop execution attempt.
            # The worker's queue processor should catch this.
            raise ValueError(msg)

        # 2. The Guardian Check (FMS) - FAIL SAFE
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
            logger.warning(f"Job {job.id} has no filament requirements (target_hex). Skipping FMS check.")
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
            logger.error(msg)
            
            # Fail-Safe Tripped
            raise FilamentMismatchError(printer_serial, target_hex)

        else:
            # IF MATCH FOUND
            logger.info(f"Match found for Job {job_id} in Slot {match_slot_idx}. Proceeding.")
            
            # Construct MQTT Payload (handled by commander, we just pass mapping)
            ams_mapping = [match_slot_idx] * 16
            
            # Phase 5: Dynamic Calibration Check
            # Logic: If jobs_since >= interval (or 0 aka fresh), we calibrate.
            is_calibration_due = (printer.jobs_since_calibration >= printer.calibration_interval) or (printer.jobs_since_calibration == 0)

            # DEBUG LOGGING (High Visibility)
            logger.error(f"🖨️ DISPATCHING JOB {job_id}:")
            logger.error(f"   Target: {target_hex}")
            logger.error(f"   FMS Match: Slot {match_slot_idx}")
            logger.error(f"   Mapping Sent: {ams_mapping}")
            # PHASE 6: Safe Sweep Optimization
            # Extract part height from metadata (DB source of truth)
            part_height_mm = 50.0  # Safe Default
            if job.job_metadata:
                part_height_mm = job.job_metadata.get("part_height_mm") or job.job_metadata.get("model_height_mm") or 50.0
            
            try:
                await self.printer_commander.start_job(printer, job, ams_mapping, is_calibration_due=is_calibration_due, part_height_mm=part_height_mm)
                
                # Success Update
                # Refresh to ensure we don't overwrite other updates
                await self.session.refresh(job)
                await self.session.refresh(printer)

                job.status = JobStatusEnum.PRINTING 
                
                # ENGAGE SAFETY LATCH (Plate is now dirty/occupied)
                printer.is_plate_cleared = False
                printer.current_job_id = job.id
                self.session.add(printer)
                self.session.add(job)
                
                await self.session.commit()
                
            except Exception as e:
                logger.error(f"Failed to dispatch Job {job_id}: {e}")
                job.status = JobStatusEnum.FAILED
                job.error_message = str(e)
                self.session.add(job)
                await self.session.commit()
                raise e

    async def handle_print_finished(self, printer_serial: str, job_id: Optional[int] = None) -> None:
        """
        Handles the 'FINISH' event from the printer.
        1. Marks current job as FINISHED.
        2. EITHER triggers auto-clearing (if enabled) OR sets AWAITING_CLEARANCE.
        """
        logger.info(f"Handling FINISH event for Printer {printer_serial}")
        
        # Reload printer to get latest state
        printer = await self.session.get(Printer, printer_serial)
        if not printer:
            logger.error(f"Printer {printer_serial} not found during finish handling.")
            return

        # Handle Job Completion
        target_job_id = job_id or printer.current_job_id
        if target_job_id:
            job = await self.session.get(Job, target_job_id)
            if job:
                logger.info(f"Marking Job {target_job_id} as FINISHED.")
                job.status = JobStatusEnum.FINISHED
                # Ensure Updated At is set (for ordering)
                job.updated_at = datetime.now(timezone.utc)
                self.session.add(job)
            printer.current_job_id = None # Clear active job

            # Phase 5: Lifecycle Increment (RESET vs INCREMENT)
            interval = printer.calibration_interval
            current_val = printer.jobs_since_calibration
            
            # Did we just run a calibration?
            # If we were at >= interval (or 0), we triggered calibration.
            was_calibration_run = (current_val >= interval) or (current_val == 0)
            
            if was_calibration_run:
                logger.info(f"Calibration run completed (Counter: {current_val}). Resetting to 0 -> 1.")
                printer.jobs_since_calibration = 1 # Reset (0) + Increment (1)
            else:
                logger.info(f"Standard run completed (Counter: {current_val}). Incrementing to {current_val + 1}.")
                printer.jobs_since_calibration += 1

            self.session.add(printer)
            await self.session.commit()

        # Decide on Clearing Strategy
        if printer.can_auto_eject:
            logger.info(f"Printer {printer_serial} supports Auto-Ejection. Checking strategy...")
            
            if printer.clearing_strategy == ClearingStrategyEnum.MANUAL:
                 # Configuration Error: Auto-Eject True but Strategy Manual? Treat as Manual.
                 logger.warning(f"Printer {printer_serial} has Auto-Eject=True but Strategy=MANUAL. Fallback to Manual.")
                 printer.current_status = PrinterStatusEnum.AWAITING_CLEARANCE
                 printer.is_plate_cleared = False
                 self.session.add(printer)
            else:
                 # Valid Auto-Strategy
                 # COOLDOWN or IMMEDIATE?
                 # Start by going to COOLDOWN. The thermal monitor in MQTT worker will trigger ejection
                 # when temp is low enough.
                 logger.info(f"Transitioning {printer_serial} to COOLDOWN for thermal release.")
                 printer.current_status = PrinterStatusEnum.COOLDOWN
                 printer.is_plate_cleared = False # Still dirty
                 self.session.add(printer)

        else:
            # Manual Clearance Required
            logger.info(f"Printer {printer_serial} requires manual clearance. Setting AWAITING_CLEARANCE.")
            printer.current_status = PrinterStatusEnum.AWAITING_CLEARANCE
            printer.is_plate_cleared = False
            self.session.add(printer)
        
        await self.session.commit()

    async def trigger_clearing(self, printer_serial: str) -> None:
        """
        Triggers the actual physical clearing process (Agent -> Printer).
        Called by Thermal Monitor or Manually.
        """
        logger.info(f"Triggering Bed Clearing for {printer_serial}")
        
        printer = await self.session.get(Printer, printer_serial)
        if not printer: return

        try:
            # 1. Update Status
            printer.current_status = PrinterStatusEnum.CLEARING_BED
            self.session.add(printer)
            await self.session.commit()

            # 2. Phase 5: Fetch Geometry for Smart Sweep
            # We need model_height_mm from the LAST finished job
            last_job_stmt = (
                select(Job)
                .where(Job.assigned_printer_serial == printer_serial, Job.status == JobStatusEnum.FINISHED)
                .order_by(Job.updated_at.desc()) # Assuming updated_at changes on finish
                .limit(1)
            )
            last_job = (await self.session.exec(last_job_stmt)).first()
            
            model_height = 50.0 # Default safe height
            if last_job and last_job.job_metadata:
                model_height = last_job.job_metadata.get("model_height_mm", 50.0)
                logger.info(f"Smart Gantry Sweep: Retrieved height {model_height}mm from Job {last_job.id}")
            else:
                logger.warning("Smart Gantry Sweep: No job metadata found. Defaulting to 50mm.")

            # 3. Generate G-Code 3MF
            maint_3mf_path = self.bed_clearing_service.create_maintenance_3mf(printer, model_height_mm=model_height)
            
            # 3. Send to Printer
            await self.printer_commander.start_maintenance_job(printer, maint_3mf_path)
            
            # Cleanup
            if maint_3mf_path.exists():
                maint_3mf_path.unlink()
                
        except Exception as e:
            logger.error(f"Failed to trigger clearing for {printer_serial}: {e}")
            # Revert to Manual intervention
            printer.current_status = PrinterStatusEnum.AWAITING_CLEARANCE
            self.session.add(printer)
            await self.session.commit()