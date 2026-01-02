from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.core.database import get_session
from app.models.core import Printer
from app.models.printer import PrinterRead
from sqlalchemy.orm import selectinload
import os

from app.services.printer_service import PrinterService
from app.services.stream_service import StreamService

router = APIRouter(prefix="/printers", tags=["Printers"])

# Initialize PrinterService
# Initialize Services
printer_service = PrinterService()
stream_service = StreamService()

@router.get("", response_model=List[PrinterRead])
async def get_printers(session: AsyncSession = Depends(get_session)):
    """Fetch all printers with real-time hot state from Redis."""
    return await printer_service.get_printers(session)

@router.get("/{serial}", response_model=PrinterRead)
async def get_printer(serial: str, session: AsyncSession = Depends(get_session)):
    """Fetch a single printer with real-time hot state."""
    printer = await printer_service.get_printer(session, serial)
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    return printer

@router.get("/{serial}/stream")
async def get_printer_stream(serial: str, session: AsyncSession = Depends(get_session)):
    """
    Returns the WebRTC stream URL for a printer.
    Dynamically registers the stream with go2rtc if needed.
    """
    statement = select(Printer).where(Printer.serial == serial)
    printer = (await session.exec(statement)).first()
    
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
        
    stream_url = await stream_service.get_stream_url(printer)
    
    # In production, this should return the public URL of go2rtc
    # For now, we return the WebRTC path which the frontend will append to the go2rtc host
    return {"stream_url": stream_url}

    # NOTE: last_job temporarily disabled due to Pydantic V2 serialization issues
    # The forward reference JobRead causes serialization failures
    # for printer in printers:
    #     if printer.jobs:
    #         sorted_jobs = sorted(
    #             [j for j in printer.jobs if j.status in [JobStatusEnum.FINISHED, JobStatusEnum.PRINTING, JobStatusEnum.FAILED]], 
    #             key=lambda x: x.updated_at or x.created_at, 
    #             reverse=True
    #         )
    #         if sorted_jobs:
    #             printer.last_job = sorted_jobs[0]
    #         else:
    #             printer.last_job = None
    #     else:
    #         printer.last_job = None
            
    return printers

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


@router.post("/{serial}/confirm-clearance", response_model=dict)
async def confirm_clearance(serial: str, session: AsyncSession = Depends(get_session)):
    """
    Manual clearance confirmation - transitions printer from AWAITING_CLEARANCE to IDLE.
    
    This is the fallback for printers where:
    - Auto-sweep is disabled (can_auto_eject=False)
    - Part height < 50mm (unsafe for Gantry Sweep)
    - User wants manual intervention
    
    ## Pre-requisite: 
    Printer status must be AWAITING_CLEARANCE.
    
    ## Effect:
    - Status transitions to IDLE
    - is_plate_cleared = True
    - Printer becomes eligible for next job
    """
    statement = select(Printer).where(Printer.serial == serial).options(selectinload(Printer.ams_slots))
    printer = (await session.exec(statement)).first()
    
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    # Verify the printer is actually waiting for clearance
    if printer.current_status != PrinterStatusEnum.AWAITING_CLEARANCE:
        raise HTTPException(
            status_code=409, 
            detail=f"Printer is not awaiting clearance. Current status: {printer.current_status.value}"
        )
    
    # Transition to IDLE
    printer.current_status = PrinterStatusEnum.IDLE
    printer.is_plate_cleared = True
    
    session.add(printer)
    await session.commit()
    await session.refresh(printer)
    
    return {
        "message": f"Clearance confirmed. Printer {serial} is now IDLE.",
        "status": printer.current_status.value,
        "is_plate_cleared": printer.is_plate_cleared
    }


@router.post("/{serial}/clear-error", response_model=dict)
async def clear_error(serial: str, session: AsyncSession = Depends(get_session)):
    """
    Phase 7: HMS Watchdog - Clear error and reset printer.
    
    Acknowledges a hardware error and transitions printer from ERROR/PAUSED back to IDLE.
    
    ## Pre-requisite:
    Printer status must be ERROR or PAUSED.
    
    ## Effect:
    - Clears last_error_code, last_error_time, last_error_description
    - Transitions status to IDLE
    - Printer becomes eligible for next job
    
    ## Operator Responsibility:
    The operator MUST physically verify the error condition is resolved before calling this endpoint.
    """
    statement = select(Printer).where(Printer.serial == serial).options(selectinload(Printer.ams_slots))
    printer = (await session.exec(statement)).first()
    
    if not printer:
        raise HTTPException(status_code=404, detail="Printer not found")
    
    # Verify the printer is in error state
    if printer.current_status not in [PrinterStatusEnum.ERROR, PrinterStatusEnum.PAUSED]:
        raise HTTPException(
            status_code=409, 
            detail=f"Printer is not in error state. Current status: {printer.current_status.value}"
        )
    
    # Log the error being cleared
    cleared_error = printer.last_error_description or printer.last_error_code or "Unknown"
    
    # Clear error fields
    printer.last_error_code = None
    printer.last_error_time = None
    printer.last_error_description = None
    
    # Transition to IDLE
    printer.current_status = PrinterStatusEnum.IDLE
    
    session.add(printer)
    await session.commit()
    await session.refresh(printer)
    
    return {
        "message": f"Error cleared on {serial}. Printer is now IDLE.",
        "cleared_error": cleared_error,
        "status": printer.current_status.value
    }


from app.schemas.tool_definitions import PrinterActionRequest, PrinterActionEnum
from app.core.exceptions import PrinterBusyError, ResourceNotFoundError
from app.services.print_job_executor import PrintJobExecutionService
from app.services.filament_manager import FilamentManager
from app.services.printer.commander import PrinterCommander

@router.post("/{serial}/command", response_model=dict)
async def send_command(
    serial: str, 
    command: PrinterActionRequest, 
    session: AsyncSession = Depends(get_session)
):
    """
    Executes a high-level operational command on a specific printer.
    
    ## Usage Instructions for AI Agents:
    - **PAUSE**: Use when you need to temporarily halt printing (e.g. for inspection).
    - **RESUME**: Use to continue a paused print.
    - **STOP**: Emergency halt. Cancels the job and stops heaters. Use only if failure is detected.
    - **CLEAR_BED**: Initiates the automated bed clearing sequence. 
      - **Pre-requisite**: Printer status must be SUCCESS or AWAITING_CLEARANCE.
      - **Warning**: Do not use if the printer is currently printing unless `force=True` is set (dangerous).
    
    ## Error Handling:
    - **404 Not Found**: Printer does not exist.
    - **409 Conflict**: Printer is busy (e.g. printing) and `force=False`. 
      - *Reasoning*: The agent should check the printer status and decide whether to wait or force.
    """
    statement = select(Printer).where(Printer.serial == serial)
    printer = (await session.exec(statement)).first()
    
    if not printer:
        raise ResourceNotFoundError("Printer", serial)
        
    # Check Busy State for invasive commands
    if command.action in [PrinterActionEnum.CLEAR_BED] and not command.force:
        # Strict lock: fail if busy
        if printer.current_status in [PrinterStatusEnum.PRINTING, PrinterStatusEnum.CLEARING_BED, PrinterStatusEnum.COOLDOWN]:
            raise PrinterBusyError(serial, printer.current_status)

    # Dispatch Command via Executor/Commander
    # Ideally we use an injected service. For now, instantiate standard services.
    commander = PrinterCommander()
    
    if command.action == PrinterActionEnum.CLEAR_BED:
         # Use the centralized Executor logic
         fms = FilamentManager()
         executor = PrintJobExecutionService(session, fms, commander)
         await executor.trigger_clearing(printer.serial)
         return {"message": f"Clearing sequence initiated for {serial}"}
         
    elif command.action == PrinterActionEnum.PAUSE:
        # TODO: Implement pause in Commander
        pass 
    elif command.action == PrinterActionEnum.RESUME:
        # TODO: Implement resume in Commander
        pass
    elif command.action == PrinterActionEnum.STOP:
        # TODO: Implement stop in Commander
        pass
    elif command.action == "CONFIRM_CLEARANCE":
        # Reactive Loop: Instant handoff
        fms = FilamentManager()
        executor = PrintJobExecutionService(session, fms, commander)
        await executor.handle_manual_clearance(serial)
        return {"message": f"Manual clearance confirmed for {serial}. Instant handoff triggered."}

    return {"message": f"Command {command.action} executed (Simulation)"}
