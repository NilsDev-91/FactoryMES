from typing import Optional, List
from sqlmodel import select, col
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import PrintJob as Job, JobStatus as JobStatusEnum, Printer

class JobService:
    """
    Service for managing retrieval and updates of Print Jobs.
    """

    async def get_next_pending_job(self, session: AsyncSession) -> Optional[Job]:
        """
        Retrieves the oldest PENDING job.
        Note: This is still used by the dispatcher for global scheduling.
        """
        statement = (
            select(Job)
            .where(Job.status == JobStatusEnum.PENDING)
            .order_by(Job.priority.desc(), Job.created_at.asc())
        )
        result = await session.execute(statement) # Fixed: session.exec -> session.execute
        return result.scalars().first()

    async def get_next_compatible_job_for_printer(
        self, 
        session: AsyncSession, 
        printer: Printer, 
        filament_manager: any
    ) -> Optional[Job]:
        """
        Peeks at the top of the queue and finds the first job this printer can handle.
        Bypasses deadlocks where an incompatible job blocks the FIFO queue.
        """
        # Fetch top N to find a compatible one without scanning the entire DB
        statement = (
            select(Job)
            .where(Job.status == JobStatusEnum.PENDING)
            .order_by(Job.priority.desc(), Job.created_at.asc())
            .limit(10)
        )
        result = await session.execute(statement)
        jobs = result.scalars().all()

        for job in jobs:
            if filament_manager.can_printer_print_job(printer, job):
                return job
            else:
                import logging
                logging.getLogger("JobService").debug(f"Skipping Job {job.id} for Printer {printer.serial} (Filament Mismatch)")
        
        return None
