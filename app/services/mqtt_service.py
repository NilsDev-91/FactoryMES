import asyncio
import json
import logging
import ssl
from typing import Any, Dict, Optional

import aiomqtt
from app.core.config import settings

logger = logging.getLogger("MqttService")

class MqttService:
    """
    Generic MQTT Service for publishing commands to the internal factory bus.
    Uses aiomqtt for robust asyncio support.
    """

    def __init__(self, broker_host: str = "localhost", broker_port: int = 8883):
        # We allow overrides but default to localhost/8883 if not provided
        # Ideally, these come from settings.
        self.broker_host = broker_host
        self.broker_port = broker_port

    async def publish_command(self, printer_id: str, command: str, payload: Dict[str, Any]) -> None:
        """
        Publishes a command to a specific printer.
        
        Topic: factory/printer/{printer_id}/command/{command}
        QoS: 1
        """
        topic = f"factory/printer/{printer_id}/command/{command}"
        
        try:
            message_json = json.dumps(payload)
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to serialize payload for {topic}: {e}")
            raise ValueError(f"Invalid payload for MQTT publish: {e}")

        # Configure SSL (Required for Port 8883 usually, though internal broker might be self-signed)
        # Using a loose context for internal ease, similar to other services in this project.
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        logger.info(f"Publishing to {topic} on {self.broker_host}:{self.broker_port}...")

        try:
            # aiomqtt Client is a context manager
            async with aiomqtt.Client(
                hostname=self.broker_host,
                port=self.broker_port,
                tls_context=context
            ) as client:
                await client.publish(topic, payload=message_json, qos=1)
                
            logger.info(f"Successfully published to {topic}")

        except aiomqtt.MqttError as e:
            logger.error(f"MQTT Connection/Publish Error for {printer_id}: {e}")
            # Raise a generic or specific exception based on governance
            raise ConnectionError(f"Failed to publish MQTT command: {e}")
        except Exception as e:
            logger.error(f"Unexpected error publishing to {topic}: {e}")
            raise e
