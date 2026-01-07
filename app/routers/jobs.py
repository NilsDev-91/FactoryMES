from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.core.database import get_session
from app.models.job import PrintJob

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("", response_model=List[PrintJob])
async def get_jobs(session: AsyncSession = Depends(get_session)):
    """
    Returns all print jobs ordered by creation date (descending).
    """
    statement = select(PrintJob).order_by(PrintJob.created_at.desc())
    result = await session.execute(statement)
    return result.scalars().all()
