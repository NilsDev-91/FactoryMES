
import asyncio
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
    Consolidated to prevent double-dispatch race conditions.
    """
    
    def __init__(self):
        self.commander = PrinterCommander()
        self._lock = asyncio.Lock()

    async def dispatch_next_job(self, session: Optional[AsyncSession] = None, target_printer_serial: Optional[str] = None):
        """
        Main entry point for dispatching.
        Fetches idle printers and pending jobs, then attempts to match them.
        Uses a lock to prevent concurrent dispatch cycles from racing.
        """
        if session is None:
            from app.core.database import async_session_maker
            async with async_session_maker() as new_session:
                return await self._dispatch_with_lock(new_session, target_printer_serial)
        else:
            return await self._dispatch_with_lock(session, target_printer_serial)

    async def _dispatch_with_lock(self, session: AsyncSession, target_printer_serial: Optional[str] = None):
        async with self._lock:
            # 1. Fetch Idle & Ready Printers
            printer_stmt = (
                select(Printer)
                .where(Printer.current_status == PrinterStatusEnum.IDLE)
                .where(Printer.is_plate_cleared == True)
                .options(selectinload(Printer.ams_slots))
            )
            
            if target_printer_serial:
                printer_stmt = printer_stmt.where(Printer.serial == target_printer_serial)
                
            printers = (await session.execute(printer_stmt)).scalars().all()
            
            if not printers:
                if target_printer_serial:
                    logger.debug(f"Target printer {target_printer_serial} is not idle or not cleared.")
                else:
                    logger.debug("No idle and cleared printers available.")
                return

            # 2. Fetch Pending Jobs (by priority)
            job_stmt = (
                select(Job)
                .where(Job.status == JobStatusEnum.PENDING)
                .order_by(Job.priority.desc(), Job.created_at.asc())
            )
            pending_jobs = (await session.execute(job_stmt)).scalars().all()
            
            if not pending_jobs:
                logger.debug("No pending jobs in queue.")
                return

            logger.info(f"Dispatching: {len(printers)} printers vs {len(pending_jobs)} jobs.")

            # 3. Match Loop
            for job in pending_jobs:
                if not job.filament_requirements:
                    continue

                for printer in printers:
                    # Capability Check
                    is_continuous = job.job_metadata.get("is_continuous", False)
                    if is_continuous and printer.type != PrinterTypeEnum.A1:
                        continue

                    # Filament Match
                    match_result = self._find_matching_ams_slot(printer, job)
                    if match_result:
                        slot_id, ams_mapping = match_result
                        logger.info(f"MATCH FOUND: Job {job.id} -> Printer {printer.serial} (Slot ID {slot_id})")
                        
                        await self._assign_and_launch(session, job, printer, ams_mapping)
                        printers.remove(printer)
                        break 

    def _find_matching_ams_slot(self, printer: Printer, job: Job) -> Optional[Tuple[int, List[int]]]:
        try:
            req = job.filament_requirements[0]
            req_material = req.get("material")
            req_color = req.get("hex_color") or req.get("color")
        except (IndexError, KeyError):
            return None

        for slot in printer.ams_slots:
            if not slot.material or slot.material.upper() != req_material.upper():
                continue
            
            if color_matcher.is_color_match(req_color, slot.color_hex):
                # Map to all 16 slots just to be safe (Bambu broadcast)
                ams_mapping = [slot.slot_id + 1] * 16
                return slot.slot_id, ams_mapping
                
        return None

    async def _assign_and_launch(self, session: AsyncSession, job: Job, printer: Printer, ams_mapping: List[int]):
        try:
            # 1. State Locking
            job.status = JobStatusEnum.UPLOADING
            job.assigned_printer_serial = printer.serial
            printer.current_status = PrinterStatusEnum.PRINTING
            printer.is_plate_cleared = False # ENGAGE LATCH
            printer.current_job_id = job.id
            
            session.add(job)
            session.add(printer)
            await session.commit()
            
            # 2. Physical Start
            # Extract part height for A1 sweep
            part_height = job.job_metadata.get("part_height_mm") or job.job_metadata.get("model_height_mm") or 38.0
            
            result = await self.commander.start_job(printer, job, ams_mapping, part_height_mm=part_height)
            
            # 3. Success Confirmation
            await session.refresh(job)
            job.status = JobStatusEnum.PRINTING
            
            # Phase 10: Store deterministic eject status from the result
            if job.job_metadata is None:
                job.job_metadata = {}
            job.job_metadata["is_auto_eject_enabled"] = result.is_auto_eject_enabled
            
            session.add(job)
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to launch Job {job.id} on {printer.serial}: {e}")
            job.status = JobStatusEnum.FAILED
            job.error_message = str(e)
            printer.current_status = PrinterStatusEnum.IDLE
            printer.is_plate_cleared = True # Release on failure
            session.add(job)
            session.add(printer)
            await session.commit()

# Singleton
job_dispatcher = JobDispatcher()
