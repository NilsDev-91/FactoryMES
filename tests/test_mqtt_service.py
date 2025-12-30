import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiomqtt
from app.services.mqtt_service import MqttService

@pytest.mark.asyncio
async def test_publish_command_success():
    """Test successful command publishing."""
    payload = {"test": "data"}
    service = MqttService(broker_host="test.broker")
    
    # Mock aiomqtt.Client
    # The Client is used as a context manager: async with Client(...) as client:
    # So we need to mock the return value of __aenter__
    
    mock_client_instance = AsyncMock()
    
    with patch("aiomqtt.Client") as MockClient:
        # Configure the Context Manager
        mock_ctx = MockClient.return_value
        mock_ctx.__aenter__.return_value = mock_client_instance
        mock_ctx.__aexit__.return_value = None
        
        await service.publish_command("P1", "start", payload)
        
        # Verify Publish Call
        mock_client_instance.publish.assert_awaited_once()
        args, kwargs = mock_client_instance.publish.call_args
        assert args[0] == "factory/printer/P1/command/start"
        assert kwargs["payload"] == '{"test": "data"}'
        assert kwargs["qos"] == 1

@pytest.mark.asyncio
async def test_publish_command_connection_error():
    """Test handling of MQTT connection errors."""
    service = MqttService()
    
    with patch("aiomqtt.Client") as MockClient:
        # Simulate connection error (Client.__aenter__ raises)
        mock_ctx = MockClient.return_value
        mock_ctx.__aenter__.side_effect = aiomqtt.MqttError("Connection failed")
        
        with pytest.raises(ConnectionError, match="Failed to publish MQTT command"):
            await service.publish_command("P1", "stop", {})
