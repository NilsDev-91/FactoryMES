
import asyncio
import sys
from sqlmodel import select, SQLModel
from database import engine, async_session_maker
from models import Printer, Order, PlatformEnum, PrinterTypeEnum, PrinterStatusEnum, OrderStatusEnum
from datetime import datetime
import uuid

async def init_db():
    print("Creating tables...")
    async with engine.begin() as conn:
        # Create all tables defined in models.py (imported via SQLModel)
        await conn.run_sync(SQLModel.metadata.create_all)
    print("Tables created successfully.")
    
    # Seed data
    async with async_session_maker() as session:
        print("Checking for existing data...")
        
        # Check for Printer
        result = await session.execute(select(Printer))
        printers = result.scalars().all()
        
        if not printers:
            print("Seeding Printer...")
            printer = Printer(
                serial="A1_TEST_SERIAL",
                name="Bambu Lab A1 - Test",
                ip_address="192.168.2.213",
                access_code="05956746",
                type=PrinterTypeEnum.A1,
                current_status=PrinterStatusEnum.IDLE
            )
            session.add(printer)
        
        # Check for Order
        result = await session.execute(select(Order))
        orders = result.scalars().all()
        
        if not orders:
            print("Seeding Order...")
            order = Order(
                platform=PlatformEnum.ETSY,
                platform_order_id=str(uuid.uuid4())[:8],
                sku="BENCHY_TEST",
                quantity=1,
                purchase_date=datetime.now(),
                status=OrderStatusEnum.OPEN
            )
            session.add(order)
            
        await session.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_db())
