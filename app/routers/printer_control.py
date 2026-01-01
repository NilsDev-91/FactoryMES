from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional

from app.core.database import get_session
from app.models.core import Printer, PrinterStatusEnum
from app.models.printer import PrinterRead

router = APIRouter(prefix="/printers", tags=["Printer Control"])

from sqlalchemy.orm import selectinload

@router.post("/{printer_id}/confirm-clearance", response_model=PrinterRead)
async def confirm_clearance(printer_id: str, session: AsyncSession = Depends(get_session)):
    """
    Manually confirm that a printer has been cleared.
    Transition from AWAITING_CLEARANCE -> IDLE.
    Resets current_job_id to None.
    """
    statement = select(Printer).where(Printer.serial == printer_id).options(selectinload(Printer.ams_slots))
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

@router.post("/{printer_id}/control/jog")
async def jog_printer(
    printer_id: str, 
    axis: str, 
    distance: float, 
    speed: Optional[int] = 1500,
    session: AsyncSession = Depends(get_session)
):
    """Jogs a printer axis."""
    statement = select(Printer).where(Printer.serial == printer_id)
    printer = (await session.exec(statement)).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    from app.services.printer.commander import PrinterCommander
    commander = PrinterCommander()
    try:
        await commander.jog_axis(printer, axis, distance, speed)
        return {"status": "success", "axis": axis, "distance": distance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{printer_id}/control/test-sweep")
async def test_sweep_printer(printer_id: str, session: AsyncSession = Depends(get_session)):
    """Executes a safe Test Sweep (Teach-In Mode)."""
    statement = select(Printer).where(Printer.serial == printer_id)
    printer = (await session.exec(statement)).first()
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")

    from app.services.printer.commander import PrinterCommander
    commander = PrinterCommander()
    
    # Safe Test Macro: Lift -> Park -> Sweep -> Home
    macro = [
        "G90",
        "G1 Z100 F3000",
        "G1 X0 Y0 F12000",
        "G1 Y256 F1500",
        "M400",
        "G1 Z100 F3000",
        "G28 X Y"
    ]
    
    try:
        await commander.send_raw_gcode(printer, macro)
        return {"status": "success", "message": "Test sweep initiated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
