import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock
from app.services.print_job_executor import PrintJobExecutionService
from app.models.core import Job, Printer, JobStatusEnum, PrinterStatusEnum, ClearingStrategyEnum
from app.services.production.bed_clearing_service import BedClearingService

async def test_execute_print_job_state_lock():
    print("TEST: execute_print_job_state_lock")
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    
    # Setup Printer in Locked State
    printer = Printer(serial="P_LOCKED", current_status=PrinterStatusEnum.CLEARING_BED, ams_slots=[])
    job = Job(id=99, status=JobStatusEnum.PENDING, filament_requirements=[{"color_hex": "#FFFFFF"}])
    
    # Mock DB Returns
    mock_result_job = MagicMock()
    mock_result_job.first.return_value = job
    mock_result_printer = MagicMock()
    mock_result_printer.first.return_value = printer
    mock_session.exec.side_effect = [mock_result_job, mock_result_printer] # Job query, then Printer query
    
    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander)
    
    try:
        await service.execute_print_job(99, "P_LOCKED")
        print("FAIL: Expected ValueError not raised")
        sys.exit(1)
    except ValueError as e:
        if "Cannot execute job" in str(e):
            print("PASS: Correctly blocked job execution.")
        else:
            print(f"FAIL: Wrong error message: {e}")
            sys.exit(1)

async def test_handle_print_finished_auto_eject():
    print("\nTEST: handle_print_finished_auto_eject")
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    mock_clearing_service = MagicMock(spec=BedClearingService)
    
    printer = Printer(
        serial="P_AUTO", 
        can_auto_eject=True, 
        clearing_strategy=ClearingStrategyEnum.A1_INERTIAL_FLING,
        current_job_id=101,
        is_plate_cleared=False
    )
    job = Job(id=101, status=JobStatusEnum.PRINTING)
    
    mock_session.get.side_effect = [printer, job] 
    
    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander, mock_clearing_service)
    
    await service.handle_print_finished("P_AUTO")
    
    # Verification
    if job.status != JobStatusEnum.FINISHED:
        print(f"FAIL: Job status mismatch. Got {job.status}")
        sys.exit(1)
    if printer.current_job_id is not None:
        print("FAIL: current_job_id not cleared")
        sys.exit(1)
    if printer.current_status != PrinterStatusEnum.COOLDOWN:
        print(f"FAIL: Printer status mismatch. Expected COOLDOWN, got {printer.current_status}")
        sys.exit(1)
    if not mock_session.commit.called:
        print("FAIL: Commit not called")
        sys.exit(1)
    print("PASS: Auto-eject logic correct.")

async def test_handle_print_finished_manual():
    print("\nTEST: handle_print_finished_manual")
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    
    printer = Printer(
        serial="P_MANUAL", 
        can_auto_eject=False, 
        current_job_id=102
    )
    job = Job(id=102, status=JobStatusEnum.PRINTING)
    
    mock_session.get.side_effect = [printer, job]
    
    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander)
    
    await service.handle_print_finished("P_MANUAL")
    
    if job.status != JobStatusEnum.FINISHED:
         print("FAIL: Job not finished")
         sys.exit(1)
    if printer.current_status != PrinterStatusEnum.AWAITING_CLEARANCE:
         print(f"FAIL: Expected AWAITING_CLEARANCE, got {printer.current_status}")
         sys.exit(1)
    print("PASS: Manual logic correct.")

async def test_trigger_clearing():
    print("\nTEST: trigger_clearing")
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    mock_clearing_service = MagicMock(spec=BedClearingService)
    
    printer = Printer(serial="P_CLEAR", current_status=PrinterStatusEnum.COOLDOWN)
    mock_session.get.return_value = printer
    
    # Mock Path
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_clearing_service.create_maintenance_3mf.return_value = mock_path
    
    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander, mock_clearing_service)
    
    await service.trigger_clearing("P_CLEAR")
    
    if printer.current_status != PrinterStatusEnum.CLEARING_BED:
        print(f"FAIL: Expected CLEARING_BED, got {printer.current_status}")
        sys.exit(1)
    
    mock_clearing_service.create_maintenance_3mf.assert_called_once_with(printer)
    mock_commander.start_maintenance_job.assert_awaited_once_with(printer, mock_path)
    print("PASS: Clearing trigger correct.")

async def main():
    await test_execute_print_job_state_lock()
    await test_handle_print_finished_auto_eject()
    await test_handle_print_finished_manual()
    await test_trigger_clearing()
    print("\nALL TESTS PASSED")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
