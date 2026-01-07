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
        printer = (await self.session.execute(printer_query)).scalars().first()
        if not printer:
            return None

        # 2. Fetch PENDING Jobs
        stmt = (
            select(Job)
            .where(Job.status == JobStatusEnum.PENDING)
            .order_by(Job.priority.desc(), Job.created_at.asc())
        )
        jobs = (await self.session.execute(stmt)).scalars().all()
        
        logger.info(f"Peeking through {len(jobs)} pending jobs for Printer {printer_serial}")

        for job in jobs:
            if job.assigned_printer_serial:
                if job.assigned_printer_serial != printer_serial:
                    continue 
                if not self.filament_manager.can_printer_print_job(printer, job):
                    logger.warning(f"Job {job.id} explicitly assigned to {printer_serial} but incompatible filament.")
                    continue 
            
            if self.filament_manager.can_printer_print_job(printer, job):
                logger.info(f"Job {job.id} matched for Printer {printer_serial}. Ready to pull.")
                return job
                
        return None

    async def execute_print_job(self, job_id: int, printer_serial: str) -> None:
        """
        Orchestrates the safe execution of a print job.
        Note: JobDispatcher is now the preferred entry point for PUSH logic.
        """
        from app.core.exceptions import FilamentMismatchError
        
        logger.info(f"Attempting to execute Job {job_id} on Printer {printer_serial}")

        # 1. Fetch Data
        job_query = select(Job).where(Job.id == job_id)
        job = (await self.session.execute(job_query)).scalars().first()

        if not job:
            raise ValueError(f"Job {job_id} not found.")

        await self.session.refresh(job)
        if job.status != JobStatusEnum.PENDING:
            return 

        printer_query = (
            select(Printer)
            .where(Printer.serial == printer_serial)
            .options(selectinload(Printer.ams_slots))
        )
        printer = (await self.session.execute(printer_query)).scalars().first()
        
        if not printer:
            raise ValueError(f"Printer {printer_serial} not found.")

        if printer.current_status in [PrinterStatusEnum.PRINTING, PrinterStatusEnum.CLEARING_BED, PrinterStatusEnum.AWAITING_CLEARANCE]:
             from app.core.exceptions import PrinterBusyError
             raise PrinterBusyError(printer_serial, printer.current_status)

        if not printer.is_plate_cleared:
            raise ValueError(f"Safety Latch ENGAGED: Printer {printer_serial} plate is not cleared.")

        # 2. FMS Check
        target_hex = None
        if job.filament_requirements and len(job.filament_requirements) > 0:
            target_hex = job.filament_requirements[0].get("hex_color") or job.filament_requirements[0].get("color")

        if not target_hex:
            raise ValueError("Missing filament requirements for FMS check.")

        match_slot_idx = await self.filament_manager.find_matching_slot(printer.ams_slots, target_hex)

        if match_slot_idx is None:
            raise FilamentMismatchError(printer_serial, target_hex)

        # 3. Dispatch
        ams_mapping = [match_slot_idx + 1] * 16 # 1-based for broadcast
        is_calibration_due = (printer.jobs_since_calibration >= printer.calibration_interval) or (printer.jobs_since_calibration == 0)
        part_height_mm = job.job_metadata.get("part_height_mm") or job.job_metadata.get("model_height_mm") or 38.0
        
        try:
            result = await self.printer_commander.start_job(printer, job, ams_mapping, is_calibration_due=is_calibration_due, part_height_mm=part_height_mm)
            
            await self.session.refresh(job)
            job.status = JobStatusEnum.PRINTING 
            
            # Phase 10: Store deterministic eject status and safety metadata
            # We re-assign the dict to ensure SQLAlchemy detects the change
            current_metadata = dict(job.job_metadata or {})
            current_metadata["is_auto_eject_enabled"] = result.is_auto_eject_enabled
            current_metadata["detected_height"] = result.detected_height
            job.job_metadata = current_metadata
            
            printer.is_plate_cleared = False
            printer.current_job_id = job.id
            printer.current_status = PrinterStatusEnum.PRINTING
            
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
        2. EITHER triggers auto-clearing (if enabled) OR sets AWAITING_CLEARANCE based on G-Code injection.
        """
        logger.info(f"Handling FINISH event for Printer {printer_serial}")
        
        # Reload printer to get latest state
        printer = await self.session.get(Printer, printer_serial)
        if not printer:
            logger.error(f"Printer {printer_serial} not found during finish handling.")
            return

        # Handle Job Completion
        target_job_id = job_id or printer.current_job_id
        job: Optional[Job] = None
        if target_job_id:
            job = await self.session.get(Job, target_job_id)
            if job:
                logger.info(f"Marking Job {target_job_id} as FINISHED.")
                job.status = JobStatusEnum.FINISHED
                job.updated_at = datetime.now(timezone.utc)
                self.session.add(job)
            printer.current_job_id = None # Clear active job

            # Lifecycle Increment
            interval = printer.calibration_interval
            current_val = printer.jobs_since_calibration
            was_calibration_run = (current_val >= interval) or (current_val == 0)
            
            if was_calibration_run:
                printer.jobs_since_calibration = 1
            else:
                printer.jobs_since_calibration += 1

            self.session.add(printer)
            await self.session.commit()

        # Decide on Clearing Strategy (Phase 10 Deterministic Feedback)
        is_auto_eject_active = False
        if job and job.job_metadata:
            is_auto_eject_active = job.job_metadata.get("is_auto_eject_enabled", False)
            logger.info(f"Job {target_job_id} Metadata Eject Status: {is_auto_eject_active}")

        if is_auto_eject_active and printer.can_auto_eject:
            # Deterministic Safety: G-code contains ejections footers AND hardware is capable.
            if printer.clearing_strategy == ClearingStrategyEnum.MANUAL:
                logger.warning(f"Printer {printer_serial} has Eject Footers but Strategy=MANUAL. Safety Stop.")
                printer.current_status = PrinterStatusEnum.AWAITING_CLEARANCE
                if job:
                    job.status = JobStatusEnum.COMPLETED # End of life as auto-eject failed safety check
            else:
                logger.info(f"Verified Safe Ejection. Transitioning {printer_serial} to COOLDOWN and Job to BED_CLEARING.")
                printer.current_status = PrinterStatusEnum.COOLDOWN
                if job:
                    job.status = JobStatusEnum.BED_CLEARING
        else:
            # Safety Stop: Ejection was disabled during sanitization (likely height safety) or hardware incapable.
            reason = "Hardware Incapable" if not printer.can_auto_eject else "Safety Stop: G-Code inhibited (Insufficient part height or unknown)"
            logger.warning(f"Printer {printer_serial} requires manual clearance. REASON: {reason}.")
            printer.current_status = PrinterStatusEnum.AWAITING_CLEARANCE
            if job:
                job.status = JobStatusEnum.COMPLETED
        
        printer.is_plate_cleared = False
        self.session.add(printer)
        if job:
            self.session.add(job)
        await self.session.commit()

    async def trigger_clearing(self, printer_serial: str) -> None:
        """
        Triggers the actual physical clearing process (Agent -> Printer).
        """
        logger.info(f"Triggering Bed Clearing for {printer_serial}")
        
        printer = await self.session.get(Printer, printer_serial)
        if not printer: return

        try:
            printer.current_status = PrinterStatusEnum.CLEARING_BED
            self.session.add(printer)
            await self.session.commit()

            # Smart Sweep: Use height from last job (now in BED_CLEARING state)
            last_job_stmt = (
                select(Job)
                .where(Job.assigned_printer_serial == printer_serial, Job.status == JobStatusEnum.BED_CLEARING)
                .order_by(Job.updated_at.desc())
                .limit(1)
            )
            last_job = (await self.session.execute(last_job_stmt)).scalars().first()
            
            model_height = 50.0 
            if last_job and last_job.job_metadata:
                model_height = last_job.job_metadata.get("model_height_mm", 50.0)
            
            from app.services.job_executor import executor as job_executor
            from app.schemas.job import PartMetadata
            
            logger.info(f"Dispatching MONITORED SWEEP via JobExecutor for {printer_serial}")
            success = await job_executor.execute_monitored_sweep(
                printer, 
                PartMetadata(height_mm=model_height)
            )
            
            if not success:
                logger.error(f"Monitored sweep failed for {printer_serial}. Falling back to AWAITING_CLEARANCE.")
                printer.current_status = PrinterStatusEnum.AWAITING_CLEARANCE
                self.session.add(printer)
                await self.session.commit()
                
        except Exception as e:
            logger.error(f"Failed to trigger clearing for {printer_serial}: {e}")
            printer.current_status = PrinterStatusEnum.AWAITING_CLEARANCE
            self.session.add(printer)
            await self.session.commit()

    async def handle_manual_clearance(self, printer_id: str) -> Printer:
        """
        Operator manually confirms bed empty.
        Short-circuits the background loop for instant job handoff.
        """
        logger.info(f"Operator CONFIRMED CLEARANCE for {printer_id}. Triggering instant handoff.")
        
        # 1. Fetch & Validate
        printer_query = (
            select(Printer)
            .where(Printer.serial == printer_id)
            .options(selectinload(Printer.ams_slots))
        )
        printer = (await self.session.execute(printer_query)).scalars().first()
        
        if not printer:
            raise ValueError(f"Printer {printer_id} not found.")

        # Allow clearance from these states
        allowed_states = [
            PrinterStatusEnum.AWAITING_CLEARANCE,
            PrinterStatusEnum.ERROR,
            PrinterStatusEnum.PAUSED,
            PrinterStatusEnum.IDLE
        ]
        
        if printer.current_status not in allowed_states:
            logger.warning(f"Manual clearance attempted on {printer_id} in state {printer.current_status}. Proceeding anyway.")

        # 2. Reset State
        printer.current_status = PrinterStatusEnum.IDLE
        printer.is_plate_cleared = True
        printer.current_job_id = None
        
        self.session.add(printer)
        await self.session.commit()
        await self.session.refresh(printer)

        # 3. Instant Queue Check (The Short Circuit)
        next_job = await self.fetch_next_job(printer_id)
        
        if next_job:
            logger.info(f"🚀 Reactive Loop: Instant Handoff! Starting Job {next_job.id} on {printer_id}.")
            try:
                await self.execute_print_job(next_job.id, printer_id)
                # Re-fetch for return
                await self.session.refresh(printer)
            except Exception as e:
                logger.error(f"Instant handoff failed for {printer_id}: {e}")
                # Printer remains IDLE/Cleared, background loop will retry later
        else:
            logger.info(f"Reactive Loop: No compatible jobs for {printer_id} right now.")

        return printer