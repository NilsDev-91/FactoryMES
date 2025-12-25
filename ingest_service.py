
import random
import uuid
from datetime import datetime
from sqlalchemy import select, func
from database import async_session_maker as AsyncSessionLocal
from models import Order, PlatformEnum, OrderStatusEnum

async def fetch_orders_mock():
    """
    Simulates fetching new orders from platforms like Etsy or eBay.
    Creates a new random order if there are fewer than 5 OPEN orders.
    """
    async with AsyncSessionLocal() as session:
        # Check count of open orders
        result = await session.execute(select(func.count(Order.id)).where(Order.status == OrderStatusEnum.OPEN))
        open_count = result.scalar()

        if open_count < 5:
            # Create a mock order
            platform = random.choice(list(PlatformEnum))
            sku = random.choice(["BENCHY_RED", "BOX_BLUE", "DRAGON_GREEN", "VASE_WHITE"])
            quantity = random.randint(1, 3)
            
            new_order = Order(
                platform=platform,
                platform_order_id=str(uuid.uuid4())[:8],
                sku=sku,
                quantity=quantity,
                purchase_date=datetime.now(),
                status=OrderStatusEnum.OPEN
            )
            
            session.add(new_order)
            await session.commit()
            print(f"[IngestService] Created new mock order: {new_order.sku} from {new_order.platform.value}")
