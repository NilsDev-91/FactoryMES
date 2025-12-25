
import asyncio
import logging
import random
from sqlalchemy import select
from database import async_session_maker as AsyncSessionLocal
from models import Printer, PrinterTypeEnum, PrinterStatusEnum

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SeedFleet")

REAL_PRINTER = {
    "serial": "03919C461802608",
    "name": "Bambu A1 - Master",
    "ip_address": "192.168.2.213",
    "access_code": "05956746",
    "type": PrinterTypeEnum.A1
}

async def seed_printers():
    logger.info("Starting Fleet Seeding...")
    
    async with AsyncSessionLocal() as session:
        # Check if DB is already populated
        result = await session.execute(select(Printer))
        existing_printers = result.scalars().all()
        
        if len(existing_printers) > 0:
            logger.info(f"Database already contains {len(existing_printers)} printers. Skipping seed.")
            return

        printers_to_add = []

        # 1. Add Real Printer
        logger.info(f"Adding Real Printer: {REAL_PRINTER['name']}")
        real_p = Printer(
            serial=REAL_PRINTER["serial"],
            name=REAL_PRINTER["name"],
            ip_address=REAL_PRINTER["ip_address"],
            access_code=REAL_PRINTER["access_code"],
            type=REAL_PRINTER["type"],
            current_status=PrinterStatusEnum.IDLE # Assume online initially for testing
        )
        printers_to_add.append(real_p)

        # 2. Add 49 Dummy Printers
        logger.info("Generating 49 Dummy Printers...")
        for i in range(1, 50):
            dummy_serial = f"DUMMY-{i:03d}"
            dummy_p = Printer(
                serial=dummy_serial,
                name=f"Farm Printer #{i}",
                ip_address=f"10.0.0.{100+i}",
                access_code="12345678",
                type=random.choice(list(PrinterTypeEnum)),
                current_status=PrinterStatusEnum.OFFLINE
            )
            printers_to_add.append(dummy_p)

        # Bulk Insert
        session.add_all(printers_to_add)
        await session.commit()
        
        logger.info(f"Successfully seeded {len(printers_to_add)} printers into the database.")

if __name__ == "__main__":
    asyncio.run(seed_printers())
