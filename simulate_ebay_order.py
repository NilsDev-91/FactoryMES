
import asyncio
import sys
import uuid
from datetime import datetime
from database import async_session_maker
from models import Order, OrderStatusEnum, PlatformEnum

async def simulate_order():
    async with async_session_maker() as session:
        print("Simulating new eBay Order for 'white_eye'...")
        
        # specific SKU requested by user
        target_sku = "white_eye"
        
        order = Order(
            platform=PlatformEnum.EBAY,
            platform_order_id=str(uuid.uuid4())[:12],
            sku=target_sku,
            quantity=1,
            purchase_date=datetime.now(),
            status=OrderStatusEnum.OPEN
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        
        print(f"SUCCESS: Created Order {order.id}")
        print(f"  Platform: {order.platform}")
        print(f"  SKU: {order.sku}")
        print(f"  Status: {order.status}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(simulate_order())
