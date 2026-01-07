
import asyncio
import sys
from sqlmodel import select, SQLModel
from app.core.database import engine, async_session_maker
from app.models.printer import Printer, PrinterState
from app.models.core import Product, PlatformEnum, OrderStatusEnum
from app.models.order import Order, OrderItem
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
                model="A1",
                current_state=PrinterState.IDLE
            )
            session.add(printer)
        
        # Check for Order
        result = await session.execute(select(Order))
        orders = result.scalars().all()
        
        if not orders:
            print("Seeding Order...")
            order = Order(
                ebay_order_id=str(uuid.uuid4())[:8],
                buyer_username="test_buyer",
                total_price=19.99,
                currency="EUR",
                status="OPEN"
            )
            session.add(order)
            await session.flush()
            
            item = OrderItem(
                order_id=order.id,
                sku="BENCHY_TEST",
                title="Test Benchy",
                quantity=1,
                variation_details="Color: Red"
            )
            session.add(item)
            
        # Check for Product
        result = await session.execute(select(Product))
        products = result.scalars().all()
        
        if not products:
            print("Seeding Product...")

            
            # Create a dummy 3mf file path or use a placeholder
            # ideally this should point to a real file if we want to print, but for now placeholder
            product = Product(
                name="Benchy Test",
                sku="BENCHY_TEST",
                description="Standard 3DBenchy",
                file_path_3mf="storage/3mf/benchy.3mf", # Placeholder path
                required_filament_type="PLA",
                required_filament_color="#FF0000"
            )
            session.add(product)
            
        await session.commit()
        print("Seeding complete.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(init_db())
