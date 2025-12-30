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

from app.models.printer import PrinterCreate
from app.models.core import PrinterStatusEnum

@router.post("", response_model=PrinterRead)
async def create_printer(printer: PrinterCreate, session: AsyncSession = Depends(get_session)):
    # Check if exists (with eager loading for relationships to avoid MissingGreenlet)
    statement = select(Printer).where(Printer.serial == printer.serial).options(selectinload(Printer.ams_slots))
    existing_printer = (await session.exec(statement)).first()

    if existing_printer:
        # Update existing
        existing_printer.name = printer.name
        existing_printer.ip_address = printer.ip_address
        existing_printer.access_code = printer.access_code
        existing_printer.type = printer.type
        session.add(existing_printer)
        await session.commit()
        await session.refresh(existing_printer)
        return existing_printer

    else:
        # Create new
        new_printer = Printer(
            serial=printer.serial,
            name=printer.name,
            ip_address=printer.ip_address,
            access_code=printer.access_code,
            type=printer.type,
            current_status=PrinterStatusEnum.IDLE,
            current_temp_nozzle=0,
            current_temp_bed=0,
            current_progress=0
        )
        session.add(new_printer)
        await session.commit()
        await session.refresh(new_printer)
        # Explicitly set ams_slots to empty list to avoid lazy load error on return
        new_printer.ams_slots = [] 
        return new_printer

@router.delete("/{serial}")
async def delete_printer(serial: str, session: AsyncSession = Depends(get_session)):
    # Verify printer exists and load relationships to prevent MissingGreenlet/Cascade issues
    statement = select(Printer).where(Printer.serial == serial).options(
        selectinload(Printer.ams_slots),
        selectinload(Printer.jobs)
    )
    printer = (await session.exec(statement)).first()
    
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    # Manually delete jobs if cascade isn't set up in DB (Safety)
    for job in printer.jobs:
        await session.delete(job)

    # Manually delete AMS slots if cascade isn't set up
    for slot in printer.ams_slots:
        await session.delete(slot)
        
    await session.delete(printer)
    await session.commit()
    return {"ok": True}

@router.post("/{serial}/action/clear-plate")
async def clear_plate(serial: str, session: AsyncSession = Depends(get_session)):
    """
    Manually marks the printer plate as cleared.
    This is used when a human operator removes the physical print.
    Triggers 'Auto-Start' re-evaluation on next tick.
    """
    statement = select(Printer).where(Printer.serial == serial)
    printer = (await session.exec(statement)).first()
    
    if not printer:
         raise HTTPException(status_code=404, detail="Printer not found")
         
    printer.is_plate_cleared = True
    
    # Optional: We could manually trigger a job check here, 
    # but the background worker will pick it up on next MQTT heartbeat 
    # or Poll interval (every 2s).
    
    session.add(printer)
    await session.commit()
    await session.refresh(printer)
    
    return {"message": "Plate Cleared. Auto-Start re-enabled."}

