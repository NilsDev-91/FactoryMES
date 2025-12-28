from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.core.database import get_session
from app.models.core import Printer
from app.models.printer import PrinterRead
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/printers", tags=["Printers"])

@router.get("", response_model=List[PrinterRead])
async def get_printers(session: AsyncSession = Depends(get_session)):
    statement = select(Printer).options(selectinload(Printer.ams_slots))
    result = await session.exec(statement)
    return result.all()
