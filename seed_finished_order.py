
import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from database import async_session_maker
from models import Order, OrderStatusEnum, PlatformEnum
from sqlmodel import select

async def seed_finished_order():
    async with async_session_maker() as session:
        print("Seeding FINISHED order...")
        
        # Create a "Finished" order
        # Assuming the user printed "red_tooth.gcode" or similar based on history, but generic is fine.
        order_guid = str(uuid.uuid4())[:8]
        order = Order(
            platform=PlatformEnum.ETSY,
            platform_order_id=order_guid,
            sku="RED_TOOTH_MODEL",
            quantity=1,
            purchase_date=datetime.now() - timedelta(hours=2),
            status=OrderStatusEnum.DONE
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        
        print(f"Created DONE Order: ID {order.id} / PlatformID {order.platform_order_id}")

        # Check total orders
        result = await session.execute(select(Order))
        all_orders = result.scalars().all()
        print(f"Total Orders in DB: {len(all_orders)}")
        for o in all_orders:
            print(f"- {o.id}: {o.status} ({o.sku})")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_finished_order())
