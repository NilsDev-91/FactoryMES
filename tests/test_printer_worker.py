import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from app.services.printer.mqtt_worker import PrinterMqttWorker
from app.models.core import Job

@pytest.mark.asyncio
async def test_process_queue_success():
    """Test successful queue processing."""
    worker = PrinterMqttWorker()
    
    # Mock Dependencies within the method (context manager)
    mock_session = AsyncMock()
    
    # We need to mock async_session_maker to return our mock_session
    with patch("app.services.printer.mqtt_worker.async_session_maker") as mock_maker:
        mock_maker.return_value.__aenter__.return_value = mock_session
        
        with patch("app.services.printer.mqtt_worker.JobService") as MockJobService, \
             patch("app.services.printer.mqtt_worker.PrintJobExecutionService") as MockExecutor, \
             patch("app.services.printer.mqtt_worker.FilamentManager") as MockFMS, \
             patch("app.services.printer.mqtt_worker.PrinterCommander") as MockCommander:
             
             # Configure JobService Mock
             mock_job_service_inst = MockJobService.return_value
             # Specifically make get_next_pending_job an AsyncMock
             mock_job_service_inst.get_next_pending_job = AsyncMock(return_value=Job(id=99))
             
             # Configure Executor Mock
             mock_executor_inst = MockExecutor.return_value
             mock_executor_inst.execute_print_job = AsyncMock()
             
             # Call Method
             await worker._process_queue_for_printer("P1")
             
             # Verify
             mock_executor_inst.execute_print_job.assert_awaited_once_with(99, "P1")

@pytest.mark.asyncio
async def test_process_queue_retry_logic():
    """Test retry logic when executor fails with mismatch."""
    worker = PrinterMqttWorker()
    
    mock_session = AsyncMock()
    
    with patch("app.services.printer.mqtt_worker.async_session_maker") as mock_maker:
        mock_maker.return_value.__aenter__.return_value = mock_session
        
        with patch("app.services.printer.mqtt_worker.JobService") as MockJobService, \
             patch("app.services.printer.mqtt_worker.PrintJobExecutionService") as MockExecutor, \
             patch("app.services.printer.mqtt_worker.FilamentManager"), \
             patch("app.services.printer.mqtt_worker.PrinterCommander"):
             
             mock_job_service_inst = MockJobService.return_value
             mock_executor_inst = MockExecutor.return_value
             
             # Setup Data: 
             job_a = Job(id=101)
             job_b = Job(id=102)
             
             mock_job_service_inst.get_next_pending_job = AsyncMock(side_effect=[job_a, job_b])
             
             # Executor Fails First, Succeeds Second
             mock_executor_inst.execute_print_job = AsyncMock(side_effect=[ValueError("Mismatch"), None])
             
             await worker._process_queue_for_printer("P2")
             
             # Verify
             assert mock_executor_inst.execute_print_job.call_count == 2
             mock_executor_inst.execute_print_job.assert_has_calls([
                 call(101, "P2"), # Awaited? pytest.call checks structure.
                 call(102, "P2")
             ])

@pytest.mark.asyncio
async def test_process_queue_empty():
    """Test when no jobs are pending."""
    worker = PrinterMqttWorker()
    mock_session = AsyncMock()
    
    with patch("app.services.printer.mqtt_worker.async_session_maker") as mock_maker:
        mock_maker.return_value.__aenter__.return_value = mock_session
        
        with patch("app.services.printer.mqtt_worker.JobService") as MockJobService, \
             patch("app.services.printer.mqtt_worker.PrintJobExecutionService") as MockExecutor, \
             patch("app.services.printer.mqtt_worker.FilamentManager"), \
             patch("app.services.printer.mqtt_worker.PrinterCommander"):
             
             mock_job_service_inst = MockJobService.return_value
             mock_executor_inst = MockExecutor.return_value
             
             mock_job_service_inst.get_next_pending_job = AsyncMock(return_value=None)
             mock_executor_inst.execute_print_job = AsyncMock()
             
             await worker._process_queue_for_printer("P3")
             
             mock_executor_inst.execute_print_job.assert_not_called()
