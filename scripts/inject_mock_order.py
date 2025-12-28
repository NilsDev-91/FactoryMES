import asyncio
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Product, Job, JobStatusEnum, OrderStatusEnum
from app.models.order import Order

async def inject_mock_order():
    print("🚀 Injecting Mock Order...")
    
    async with async_session_maker() as session:
        # 1. Load Product
        statement = select(Product).where(Product.sku == "WHITE_EYE")
        result = await session.exec(statement)
        product = result.first()
        
        if not product:
            print("❌ Error: Product WHITE_EYE not found. Run seed_white_eye.py first.")
            return

        # 2. Create Order
        # Check if exists to avoid dupes in this test script
        stmt_order = select(Order).where(Order.ebay_order_id == "TEST-ORDER-001")
        res_order = await session.exec(stmt_order)
        existing_order = res_order.first()
        
        if existing_order:
             print("ℹ️  Order TEST-ORDER-001 already exists. Using existing order.")
             order = existing_order
        else:
            order = Order(
                ebay_order_id="TEST-ORDER-001",
                buyer_username="Tester",
                total_price=0.0,
                currency="USD",
                status=OrderStatusEnum.OPEN
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)
        
        # 3. Create Job
        # Filament requirements: White PLA on slot 0 (virtual)
        filament_reqs = [{"material": "PLA", "hex_color": "#FFFFFF", "virtual_id": 0}]
        
        job = Job(
            order_id=order.id,
            gcode_path=product.file_path_3mf,
            status=JobStatusEnum.PENDING,
            filament_requirements=filament_reqs
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        print(f"✅ Job Created! ID: {job.id}")
        print(f"   - Status: {job.status}")
        print(f"   - File: {job.gcode_path}")
        print(f"   - Requirements: {job.filament_requirements}")
        print("🚀 Order Injected! Watch the Dispatcher logs.")

if __name__ == "__main__":
    asyncio.run(inject_mock_order())
