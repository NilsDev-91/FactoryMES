import asyncio
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Product, Job, JobStatusEnum, OrderStatusEnum
from app.models.order import Order

async def simulate_blue_order():
    print("🔵 Simulating Blue Eye Order...")
    
    async with async_session_maker() as session:
        # 1. Load Product
        statement = select(Product).where(Product.sku == "BLUE_EYE")
        result = await session.exec(statement)
        product = result.first()
        
        if not product:
            print("❌ Product BLUE_EYE not found.")
            return

        # 2. Create Order
        ebay_id = "TEST-ORDER-BLUE-001"
        stmt_order = select(Order).where(Order.ebay_order_id == ebay_id)
        res_order = await session.exec(stmt_order)
        existing_order = res_order.first()
        
        if existing_order:
             order = existing_order
             print(f"ℹ️  Using existing Order {ebay_id}")
        else:
            order = Order(
                ebay_order_id=ebay_id,
                buyer_username="BlueTester",
                total_price=10.0,
                currency="USD",
                status=OrderStatusEnum.OPEN
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)
        
        # 3. Create Job (Simulating Logic Service)
        # The Job should inherit the Product's requirements
        # In a real flow, OrderProcessor does this. Here we manually link them.
        
        # 3. Create Job (Simulating Logic Service)
        # The Job should inherit the Product's requirements
        
        job_reqs = []
        if product.filament_requirements:
             job_reqs = [
                {
                    "material": r.get("material"),
                    "hex_color": r.get("hex_color"),
                    "virtual_id": r.get("virtual_slot_id", 0)
                }
                for r in product.filament_requirements
             ]
        else:
             # Fallback to legacy fields
             job_reqs = [{
                 "material": product.required_filament_type,
                 "hex_color": product.required_filament_color,
                 "virtual_id": 0
             }]
        
        job = Job(
            order_id=order.id,
            gcode_path=product.file_path_3mf,
            status=JobStatusEnum.PENDING,
            filament_requirements=job_reqs
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        # 4. Verification
        print(f"✅ Job Created! ID: {job.id}")
        print(f"   file: {job.gcode_path}")
        print(f"   reqs: {job.filament_requirements}")
        
        # Check for Blue
        has_blue = any(r['hex_color'] == "#0000FF" for r in job.filament_requirements)
        if has_blue:
            print("✅ Job Created. The Printer will use BLUE filament for this WHITE sliced file.")
        else:
            print("❌ FAILED: Job does not contain Blue requirement!")

if __name__ == "__main__":
    asyncio.run(simulate_blue_order())
