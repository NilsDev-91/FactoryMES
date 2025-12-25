
import asyncio
import logging
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import SQLModel, select, create_engine
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
from models import Printer, Product, PrinterStatusEnum, PrinterTypeEnum

# Configure Test Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DBTest")

# Use SQLite for testing (in-memory)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

async_session_maker = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

async def test_json_storage():
    logger.info("Starting JSON Storage Test...")
    
    # 1. Create Schema
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # 2. Insert Printer with AMS Data
    ams_data_input = [
        {"slot": 0, "type": "PLA", "color": "#FF0000", "remaining": 100},
        {"slot": 1, "type": "PETG", "color": "#00FF00", "remaining": 50}
    ]
    
    async with async_session_maker() as session:
        printer = Printer(
            serial="TEST_SERIAL_001",
            name="Test Printer",
            type=PrinterTypeEnum.A1,
            ams_data=ams_data_input
        )
        session.add(printer)
        await session.commit()
        await session.refresh(printer)
        
        # Verify
        logger.info(f"Inserted Printer AMS Data type: {type(printer.ams_data)}")
        logger.info(f"Inserted Printer AMS Data content: {printer.ams_data}")
        
        assert isinstance(printer.ams_data, list), "AMS Data should be a list"
        assert len(printer.ams_data) == 2, "Should have 2 slots"
        assert printer.ams_data[0]['type'] == "PLA", "First slot should be PLA"
        
        logger.info("Write Test PASSED.")

    # 3. Read back
    async with async_session_maker() as session:
        result = await session.execute(select(Printer).where(Printer.serial == "TEST_SERIAL_001"))
        fetched_printer = result.scalars().first()
        
        assert fetched_printer is not None
        assert fetched_printer.ams_data[1]['color'] == "#00FF00"
        
        logger.info("Read Test PASSED.")

async def test_product_requirements():
    logger.info("\nStarting Product Requirements Test...")
    async with async_session_maker() as session:
        prod = Product(
            name="Test Cube",
            sku="CUBE001",
            file_path_3mf="/tmp/cube.3mf",
            required_filament_type="PLA-CF",
            required_filament_color="#000000"
        )
        session.add(prod)
        await session.commit()
        await session.refresh(prod)
        
        assert prod.required_filament_type == "PLA-CF"
        
        logger.info("Product Storage Test PASSED.")

async def main():
    await test_json_storage()
    await test_product_requirements()
    logger.info("\nALL INTEGRATION TESTS PASSED.")

if __name__ == "__main__":
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
