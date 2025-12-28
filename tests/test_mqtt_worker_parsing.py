import asyncio
import json
import logging
import sys
import os
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.printer.mqtt_worker import PrinterMqttWorker
from app.models.core import PrinterStatusEnum, Printer

async def test_message_parsing():
    worker = PrinterMqttWorker()
    
    # Mock payload from Bambu Lab printer
    payload_data = {
        "print": {
            "nozzle_temper": 210.5,
            "bed_temper": 60.0,
            "gcode_state": "RUNNING",
            "mc_percent": 45
        }
    }
    payload = json.dumps(payload_data).encode('utf-8')
    
    # Mock printer object
    mock_printer = Printer(
        serial="TEST001",
        name="Test",
        type="A1"
    )
    
    # Mocking the database session and session maker
    with patch("app.services.printer.mqtt_worker.async_session_maker") as mock_maker:
        mock_session = AsyncMock()
        mock_maker.return_value.__aenter__.return_value = mock_session
        
        # Mock session.get to return our printer
        mock_session.get.return_value = mock_printer
        
        # Mock session.add to be synchronous (MagicMock)
        mock_session.add = MagicMock()

        # Remove incorrect execute mock
        # mock_result = MagicMock()
        # mock_result.scalar_one_or_none.return_value = mock_printer
        # mock_session.execute.return_value = mock_result
        
        # Call the message handler
        await worker._handle_message("TEST001", payload_data)
        
        # Assertions
        assert mock_printer.current_temp_nozzle == 210.5
        assert mock_printer.current_temp_bed == 60.0
        assert mock_printer.current_status == PrinterStatusEnum.PRINTING
        assert mock_printer.current_progress == 45
        
        logger.info("Telemetry parsing test PASSED")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Test")
    asyncio.run(test_message_parsing())
