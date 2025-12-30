
import asyncio
import logging
from typing import Optional
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.core import Job, Printer, Product, JobStatusEnum, PrinterStatusEnum, OrderStatusEnum
from app.models.order import Order
from app.services.logic.filament_manager import FilamentManager
from app.services.printer.commander import PrinterCommander

logger = logging.getLogger("ProductionDispatcher")

class ProductionDispatcher:
    def __init__(self):
        self.commander = PrinterCommander()
        self.filament_manager = FilamentManager()
        self.is_running = False

    async def start(self):
        """Starts the infinite dispatch loop."""
        self.is_running = True
        logger.info("Production Dispatcher Started.")
        while self.is_running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Error in Dispatch Loop: {e}", exc_info=True)
            
            await asyncio.sleep(10)

    async def stop(self):
        """Stops the loop."""
        self.is_running = False
        logger.info("Production Dispatcher Stopping...")

    async def run_cycle(self):
        """Single iteration of the dispatch logic."""
        async with async_session_maker() as session:
            # 0. Manual Clearance Protocol Check
            # Check availability to avoid churning if blocked
            idle_stmt = select(Printer).where(Printer.current_status == PrinterStatusEnum.IDLE)
            awaiting_stmt = select(Printer).where(Printer.current_status == PrinterStatusEnum.AWAITING_CLEARANCE)
            
            idle_printers = (await session.exec(idle_stmt)).all()
            awaiting_printers = (await session.exec(awaiting_stmt)).all()
            
            if not idle_printers and awaiting_printers:
                logger.info(f"Waiting for manual plate clearance ({len(awaiting_printers)} waiting)...")
                await asyncio.sleep(5)
                return

            # 1. Fetch PENDING Jobs
            statement = select(Job).where(Job.status == JobStatusEnum.PENDING)
            result = await session.exec(statement)
            pending_jobs = result.all()
            
            if not pending_jobs:
                return

            logger.info(f"Found {len(pending_jobs)} PENDING jobs.")

            for job in pending_jobs:
                # 2. Get Product Requirements
                prod_stmt = select(Product).where(Product.file_path_3mf == job.gcode_path)
                prod_result = await session.exec(prod_stmt)
                product = prod_result.first()
                
                if not product:
                    logger.warning(f"Job {job.id}: Product not found for gcode {job.gcode_path}. Skipping.")
                    continue

                # Attach product to job for the logic service
                # (The logic service expects job.product or logic to find it)
                # job.product = product <--- REMOVED
                
                # Check basic requirement existence locally or let service handle?
                # Service returns None if no match.
                # Only skip if no material defined?
                if not product.required_filament_type:
                     logger.warning(f"Job {job.id}: Product has no material defined. Skipping.")
                     continue
                
                # 3. Find Printer
                # New Signature: find_best_printer(session, job, product)
                match = await self.filament_manager.find_best_printer(session, job, product=product)
                
                if match:
                    printer, ams_mapping = match
                    
                    logger.info(f"Job {job.id}: Matched to Printer {printer.serial} (AMS: {ams_mapping})")
                    
                    # 4. Lock & Execute
                    await self.assign_and_execute_job(session, job, printer.serial, ams_mapping)
                else:
                    logger.debug(f"Job {job.id}: No matching IDLE printer found.")

    async def assign_and_execute_job(self, session, job: Job, printer_serial: str, ams_mapping: list):
        """
        Locks the job/printer and triggers execution.
        """
        try:
            # --- LOCKING ---
            printer = await session.get(Printer, printer_serial)
            if not printer or printer.current_status != PrinterStatusEnum.IDLE:
                 logger.warning(f"Printer {printer_serial} no longer IDLE. Aborting assignment.")
                 return

            # Update statuses
            job.assigned_printer_serial = printer_serial
            job.status = JobStatusEnum.UPLOADING
            
            printer.current_status = PrinterStatusEnum.PRINTING
            
            if job.order_id:
                order = await session.get(Order, job.order_id)
                if order:
                    order.status = OrderStatusEnum.PRINTING
                    session.add(order)
            
            session.add(job)
            session.add(printer)
            await session.commit()
            
            # --- EXECUTION ---
            try:
                # Use High-Level Commander
                # Note: commander.start_job expects Printer object with IP/Access Code.
                # Our 'printer' object here is attached to session.
                
                await self.commander.start_job(printer, job, ams_mapping)
                
                # Success Update
                job.status = JobStatusEnum.PRINTING
                session.add(job)
                await session.commit()
                logger.info(f"Job {job.id}: Execution started successfully on {printer_serial}.")
                
            except Exception as exec_err:
                logger.error(f"Job {job.id}: Execution Failed - {exec_err}")
                
                # --- REVERT ---
                # Re-fetch valid state
                await session.refresh(job)
                await session.refresh(printer)
                
                printer.current_status = PrinterStatusEnum.IDLE
                job.status = JobStatusEnum.FAILED
                job.error_message = str(exec_err)
                job.assigned_printer_serial = None 
                
                session.add(printer)
                session.add(job)
                await session.commit()

        except Exception as e:
            logger.error(f"Error during assignment transaction for Job {job.id}: {e}")
