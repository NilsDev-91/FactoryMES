import asyncio
import logging
from sqlalchemy import select
from app.core.database import async_session_maker
from app.models.core import Printer, ClearingStrategyEnum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Config")

async def configure():
    async with async_session_maker() as session:
        # Serial for A1 Real
        serial = "03919C461802608"
        
        stmt = select(Printer).where(Printer.serial == serial)
        result = await session.execute(stmt)
        printer = result.scalars().first()
        
        if not printer:
            logger.error(f"Printer {serial} not found!")
            return
            
        logger.info(f"Configuring {printer.name} ({serial})...")
        printer.can_auto_eject = True
        printer.clearing_strategy = ClearingStrategyEnum.A1_INERTIAL_FLING
        printer.thermal_release_temp = 60.0 # Set high for immediate test if bed is warm
        
        session.add(printer)
        await session.commit()
        logger.info(f"Configuration updated: Strategy={printer.clearing_strategy}, Threshold={printer.thermal_release_temp}C")

if __name__ == "__main__":
    asyncio.run(configure())
