
import asyncio
import logging
from typing import Optional
from sqlmodel import select
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker
from app.models.core import Job, Printer, Product, JobStatusEnum, PrinterStatusEnum
from app.models.order import Order, OrderStatusEnum
from app.models.product_sku import ProductSKU
from app.models.print_file import PrintFile
from app.services.job_dispatcher import JobDispatcher

logger = logging.getLogger("ProductionDispatcher")

class ProductionDispatcher:
    def __init__(self):
        self.job_dispatcher = JobDispatcher()
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
            # The new JobDispatcher handles the full matching and launch logic
            # including ready checks, capability checks, and FMS matching.
            await self.job_dispatcher.dispatch_next_job(session)

    async def assign_and_execute_job(self, session, job: Job, printer_serial: str, ams_mapping: list):
        """
        Locks the job/printer and triggers execution.
        """
        try:
            # --- LOCKING & VALIDATION ---
            # Refresh to get latest DB status (preventing race with MQTT worker/dispatcher loop)
            await session.refresh(job)
            if job.status != JobStatusEnum.PENDING:
                logger.warning(f"Job {job.id} is no longer PENDING (Status: {job.status}). Aborting assignment.")
                return

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
                # Refresh to ensure we don't overwrite telemetry updates from MQTT worker
                await session.refresh(job)
                await session.refresh(printer)
                
                job.status = JobStatusEnum.PRINTING
                session.add(job)
                await session.commit()
                logger.info(f"Job {job.id}: Execution started successfully on {printer_serial}.")
                
            except Exception as exec_err:
                logger.error(f"Job {job.id}: Execution Failed - {exec_err}", exc_info=True)
                
                # --- REVERT ---
                # Re-fetch valid state
                await session.refresh(job)
                await session.refresh(printer)
                
                printer.current_status = PrinterStatusEnum.IDLE
                job.status = JobStatusEnum.FAILED
                job.error_message = f"{type(exec_err).__name__}: {str(exec_err)}"
                job.assigned_printer_serial = None 
                
                session.add(printer)
                session.add(job)
                await session.commit()

        except Exception as e:
            logger.error(f"Error during assignment transaction for Job {job.id}: {e}", exc_info=True)
