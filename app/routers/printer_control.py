from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from app.core.database import get_session
from app.models.core import Printer, PrinterStatusEnum
from app.models.printer import PrinterRead

router = APIRouter(prefix="/printers", tags=["Printer Control"])

@router.post("/{printer_id}/confirm-clearance", response_model=PrinterRead)
async def confirm_clearance(printer_id: str, session: AsyncSession = Depends(get_session)):
    """
    Manually confirm that a printer has been cleared.
    Transition from AWAITING_CLEARANCE -> IDLE.
    Resets current_job_id to None.
    """
    statement = select(Printer).where(Printer.serial == printer_id)
    printer = (await session.exec(statement)).first()

    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    if printer.current_status != PrinterStatusEnum.AWAITING_CLEARANCE:
        raise HTTPException(
            status_code=400, 
            detail=f"Printer is in state {printer.current_status}, but must be AWAITING_CLEARANCE to confirm."
        )

    # Action
    printer.current_status = PrinterStatusEnum.IDLE
    printer.current_job_id = None
    
    session.add(printer)
    await session.commit()
    await session.refresh(printer)

    return printer
