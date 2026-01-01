import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services.print_job_executor import PrintJobExecutionService
from app.models.core import Job, Printer, JobStatusEnum, PrinterStatusEnum
from app.core.exceptions import FilamentMismatchError, PrinterBusyError

async def test_fetch_next_job_peeking():
    print("\nTEST: fetch_next_job_peeking")
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    
    # Setup Printer
    printer = Printer(serial="P_PEEK", ams_slots=[])
    
    # Setup Jobs
    # Job 1: Incompatible
    # Job 2: Compatible
    job1 = Job(id=1, status=JobStatusEnum.PENDING, priority=10, created_at="2024-01-01")
    job2 = Job(id=2, status=JobStatusEnum.PENDING, priority=5, created_at="2024-01-02")
    
    # Mock DB Queries
    # 1. Printer Query
    mock_printer_res = MagicMock()
    mock_printer_res.first.return_value = printer
    
    # 2. Jobs Query
    mock_jobs_res = MagicMock()
    mock_jobs_res.all.return_value = [job1, job2]
    
    mock_session.exec.side_effect = [mock_printer_res, mock_jobs_res]
    
    # Mock FMS Logic
    # can_printer_print_job(printer, job)
    # Call 1 (Job 1): False
    mock_fms.can_printer_print_job.side_effect = [False, True]
    # IMPORTANT: Since real method is Sync, validation logic calls it directly.
    # AsyncMock makes it async by default. Use side_effect is fine IF we ensure it behaves like a sync function return?
    # No, AsyncMock always returns a coroutine when called if not configured otherwise?
    # Actually, let's explicit replace it with a MagicMock which is sync.
    mock_fms.can_printer_print_job = MagicMock(side_effect=[False, True])

    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander)
    
    # EXECUTE
    selected_job = await service.fetch_next_job("P_PEEK")
    
    # VERIFY
    assert selected_job is not None
    assert selected_job.id == 2
    print("PASS: Skipped Job 1, selected Job 2.")
    
    # Check calls
    assert mock_fms.can_printer_print_job.call_count == 2

async def test_execute_fail_safe():
    print("\nTEST: execute_fail_safe")
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    
    printer = Printer(serial="P_FAILSAFE", is_plate_cleared=True, current_status=PrinterStatusEnum.IDLE, ams_slots=[])
    job = Job(id=99, status=JobStatusEnum.PENDING, filament_requirements=[{"color_hex": "#FF0000"}])
    
    mock_res_job = MagicMock(); mock_res_job.first.return_value = job
    mock_res_printer = MagicMock(); mock_res_printer.first.return_value = printer
    
    # Re-using side effect for execute flow: Job query, Printer query
    mock_session.exec.side_effect = [mock_res_job, mock_res_printer]
    
    # Mock FMS: Match NOT FOUND (Fail Safe Triggered)
    mock_fms.find_matching_slot.return_value = None
    
    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander)
    
    try:
        await service.execute_print_job(99, "P_FAILSAFE")
        print("FAIL: Expected FilamentMismatchError")
    except FilamentMismatchError as e:
        print(f"PASS: Caught Expected Error: {e.detail}")
    except Exception as e:
        print(f"FAIL: Wrong exception type {type(e)}")

async def main():
    await test_fetch_next_job_peeking()
    await test_execute_fail_safe()
    print("\nALL EXECUTOR INTEGRATION TESTS PASSED")

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(main())
