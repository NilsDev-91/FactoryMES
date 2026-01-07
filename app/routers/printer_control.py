from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Optional
import logging

from app.core.database import get_session
from app.models.printer import Printer, PrinterState
from app.models import PrinterRead
from app.services.job_executor import JobExecutionService
from app.services.filament_service import FilamentService
from app.services.printer.commander import PrinterCommander

router = APIRouter(prefix="/printers", tags=["Printer Control"])

from sqlalchemy.orm import selectinload

@router.post("/{printer_id}/confirm-clearance", response_model=PrinterRead)
async def confirm_clearance(
    printer_id: str, 
    session: AsyncSession = Depends(get_session)
):
    """
    Manually confirm that a printer has been cleared.
    Transition from AWAITING_CLEARANCE -> IDLE.
    Triggers instant job handoff (Reactive Loop).
    """
    # 1. Setup Services
    filament_service = FilamentService(session)
    commander = PrinterCommander()
    executor = JobExecutionService(session)
    
    try:
        updated_printer = await executor.handle_manual_clearance(printer_id)
        return updated_printer
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        logging.error(f"Failed to handle manual clearance: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

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


@router.post("/{printer_id}/control/force-clear", response_model=PrinterRead)
async def force_clear_printer(printer_id: str, session: AsyncSession = Depends(get_session)):
    """
    Manually trigger a bed clearing sweep sequence.
    Use when the system hangs or a print was removed manually but status didn't update.
    
    Allowed states: IDLE, COOLDOWN, AWAITING_CLEARANCE
    """
    statement = select(Printer).where(Printer.serial == printer_id)
    printer = (await session.exec(statement)).first()
    
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    allowed_states = [
        PrinterState.IDLE,
        PrinterState.COOLDOWN,
        PrinterState.AWAITING_CLEARANCE
    ]
    
    if printer.current_state not in allowed_states:
        raise HTTPException(
            status_code=400,
            detail=f"Force clear not allowed in state {printer.current_state}. Allowed: IDLE, COOLDOWN, AWAITING_CLEARANCE"
        )
    
    # Simplified implementation: Just update status without MQTT commands
    # Full MQTT clearing is currently blocked by Python 3.14/Windows asyncio issues
    logger = logging.getLogger(__name__)
    logger.info(f"Force-clear triggered for {printer_id}, updating status to CLEARING_BED")
    
    try:
        printer.current_state = PrinterState.CLEARING_BED
        session.add(printer)
        await session.commit()
        await session.refresh(printer)
        return printer
    except Exception as e:
        logger.error(f"Failed to update printer status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger clearing: {str(e)}")


from app.models.printer import AutomationConfigUpdate

@router.patch("/{printer_id}/automation-config", response_model=PrinterRead)
async def update_automation_config(
    printer_id: str,
    config: AutomationConfigUpdate,
    session: AsyncSession = Depends(get_session)
):
    """
    Update automation configuration parameters for a printer.
    
    - can_auto_eject: Enable/disable the Infinite Loop
    - thermal_release_temp: Temperature threshold for bed release (°C)
    - clearing_strategy: MANUAL, A1_GANTRY_SWEEP, A1_TOOLHEAD_PUSH, or X1_MECHANICAL_SWEEP
    """
    statement = select(Printer).where(Printer.serial == printer_id)
    printer = (await session.exec(statement)).first()
    
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    # Apply updates
    update_data = config.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(printer, field, value)
    
    session.add(printer)
    await session.commit()
    await session.refresh(printer)
    
    return printer

