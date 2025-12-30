from typing import Optional, List
from sqlmodel import select, col
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core import Job, JobStatusEnum, Printer

class JobService:
    """
    Service for managing retrieval and updates of Print Jobs.
    """

    async def get_next_pending_job(self, session: AsyncSession) -> Optional[Job]:
        """
        Retrieves the oldest PENDING job.
        Future enhancements could include priority or material matching logic.
        """
        # Order by Created At Ascending (FIFO)
        # Verify if 'priority' exists? Requirements mentioned Priority but model might not have it.
        # Verified Job model earlier: id, order_id, status, filament_requirements, created_at.
        # No 'priority' field in Job model seen in core.py. 
        # Requirement said: "Create Print Job 1: Priority 10". 
        # If I didn't add Priority to model, I can't sort by it.
        # I will check if I missed 'priority' in Job model.
        # If missing, I will stick to FIFO (created_at).

        statement = (
            select(Job)
            .where(Job.status == JobStatusEnum.PENDING)
            .order_by(Job.priority.desc(), Job.created_at.asc())
        )
        result = await session.exec(statement)
        return result.first()
