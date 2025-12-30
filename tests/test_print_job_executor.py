import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.print_job_executor import PrintJobExecutionService
from app.models.core import Job, Printer, JobStatusEnum

@pytest.mark.asyncio
async def test_execute_print_job_success():
    """Test successful job execution with valid filament match."""
    # Mock Dependencies
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    
    # Mock Data
    job = Job(id=1, status=JobStatusEnum.PENDING, filament_requirements=[{"color_hex": "#FFFFFF"}])
    printer = Printer(serial="P1", ams_slots=[])
    
    # Setup Session Mocks
    # session.exec() returns a Result object (Sync or Async?) 
    # In SQLModel with AsyncSession, session.exec is async.
    # It returns a scalar-like result that supports .first(), .all() etc.
    # So: await session.exec() -> Result
    # Result.first() -> Item
    
    # We need a Mock object for the Result
    mock_result_job = MagicMock()
    mock_result_job.first.return_value = job
    
    mock_result_printer = MagicMock()
    mock_result_printer.first.return_value = printer
    
    # session.exec is called twice. 
    # Side effects for the AWAITED return value.
    mock_session.exec.side_effect = [mock_result_job, mock_result_printer]
    
    # Setup FMS Mock (Match found at slot 0)
    mock_fms.find_matching_slot.return_value = 0
    
    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander)
    
    await service.execute_print_job(1, "P1")
    
    # Verification
    # Note: Checking call args on async mocks can be tricky if not awaited.
    # But find_matching_slot IS awaited.
    mock_fms.find_matching_slot.assert_awaited_once_with(printer.ams_slots, "#FFFFFF")
    mock_commander.start_job.assert_awaited_once_with(printer, job, [0])
    assert job.status == JobStatusEnum.PRINTING
    mock_session.commit.assert_awaited()

@pytest.mark.asyncio
async def test_execute_print_job_material_mismatch():
    """Test job execution failing due to FMS mismatch."""
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    
    job = Job(id=2, status=JobStatusEnum.PENDING, filament_requirements=[{"color_hex": "#FF0000"}])
    printer = Printer(serial="P2", ams_slots=[])
    
    mock_result_job = MagicMock()
    mock_result_job.first.return_value = job
    
    mock_result_printer = MagicMock()
    mock_result_printer.first.return_value = printer

    mock_session.exec.side_effect = [mock_result_job, mock_result_printer]
    
    # Setup FMS Mock (No Match)
    mock_fms.find_matching_slot.return_value = None
    
    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander)
    
    with pytest.raises(ValueError) as excinfo:
        await service.execute_print_job(2, "P2")
    
    # Debug print
    print(f"Caught exception: {excinfo.value}")
    assert "MATERIAL_MISMATCH" in str(excinfo.value)
    assert job.status == JobStatusEnum.FAILED
    assert "MATERIAL_MISMATCH" in job.error_message
    mock_session.commit.assert_awaited()

@pytest.mark.asyncio
async def test_execute_print_job_missing_requirements():
    """Test job execution failing due to missing requirements."""
    mock_session = AsyncMock()
    mock_fms = AsyncMock()
    mock_commander = AsyncMock()
    
    job = Job(id=3, status=JobStatusEnum.PENDING, filament_requirements=[]) # Empty reqs
    printer = Printer(serial="P3")
    
    mock_result_job = MagicMock()
    mock_result_job.first.return_value = job
    
    mock_result_printer = MagicMock()
    mock_result_printer.first.return_value = printer
    
    mock_session.exec.side_effect = [mock_result_job, mock_result_printer]
    
    service = PrintJobExecutionService(mock_session, mock_fms, mock_commander)
    
    with pytest.raises(ValueError, match="Missing filament requirements"):
        await service.execute_print_job(3, "P3")
        
    assert job.status == JobStatusEnum.FAILED
