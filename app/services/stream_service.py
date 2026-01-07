import httpx
import logging
import urllib.parse
import os
from app.models import Printer

logger = logging.getLogger("StreamService")

class StreamService:
    def __init__(self, go2rtc_url: str = None):
        # Default to localhost for local dev, use env var for Docker
        self.go2rtc_url = go2rtc_url or os.getenv("GO2RTC_URL", "http://localhost:1984")

    async def get_stream_url(self, printer: Printer) -> str:
        """
        Registers the printer's RTSPS stream with go2rtc and returns the WebRTC playback URL.
        """
        if not printer.ip_address or not printer.access_code:
            logger.warning(f"Printer {printer.serial} missing IP or Access Code. Streaming unavailable.")
            return ""

        # 1. Construct Source URL
        # Bambu RTSPS: rtsps://bblp:{access_code}@{ip}:322/streaming/live/1
        encoded_code = urllib.parse.quote(printer.access_code)
        source_url = f"rtsps://bblp:{encoded_code}@{printer.ip_address}:322/streaming/live/1"

        # 2. Register with go2rtc
        # PUT /api/streams?src={url}&name={serial}
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "src": source_url,
                    "name": printer.serial
                }
                response = await client.put(f"{self.go2rtc_url}/api/streams", params=params)
                response.raise_for_status()
                logger.info(f"Registered stream for {printer.serial} with go2rtc.")
        except Exception as e:
            logger.error(f"Failed to register stream for {printer.serial}: {e}")
            # we still return the URL as it might work if already registered
            pass

        # 3. Return Stream URL (Browser Access)
        # Using stream.html with mode=mse for better compatibility
        # mse = Media Source Extensions, works in most modern browsers
        return f"http://localhost:1984/stream.html?src={printer.serial}&mode=mse"
