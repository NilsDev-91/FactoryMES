import asyncio
import logging
import random
import uuid
from datetime import datetime
from sqlmodel import select, func
from app.core.database import async_session_maker
from app.models.core import Product, OrderStatusEnum, PlatformEnum
from app.models.order import Order

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("OrderService")

async def create_dummy_order():
    """Creates a random order for testing purposes"""
    async with async_session_maker() as session:
        # Get all products
        result = await session.exec(select(Product))
        products = result.all()
        
        if not products:
            logger.warning("No products in DB. Cannot create dummy order.")
            return

        product = random.choice(products)
        
        # Randomly choose a status for variety (mostly OPEN)
        status = OrderStatusEnum.OPEN
        
        new_order = Order(
            platform=PlatformEnum.ETSY,
            platform_order_id=str(uuid.uuid4())[:12],
            sku=product.sku,
            quantity=1,
            status=status,
            created_at=datetime.now()
        )
        
        session.add(new_order)
        await session.commit()
        await session.refresh(new_order)
        logger.info(f"New Order created: ID {new_order.id} for SKU {product.sku}")

async def run_service_loop():
    """Simulates incoming orders"""
    logger.info("Order Service (Async) started.")
    
    while True:
        try:
            async with async_session_maker() as session:
                # Spam protection: only create if less than 5 pending
                # Count queries in SQLModel/SQLAlchemy Async
                # method 1: execute(select(func.count())...).scalar()
                
                result = await session.exec(select(func.count()).select_from(Order).where(Order.status == OrderStatusEnum.OPEN))
                pending_count = result.one()
                
                if pending_count < 5:
                    # await create_dummy_order()
                    pass
                else:
                    logger.debug("Enough pending orders, pausing creation.")
                    
        except Exception as e:
            logger.error(f"Error in Order Loop: {e}")
        
        await asyncio.sleep(30) 

if __name__ == "__main__":
    # Windows Selector Loop Policy fix
    import sys
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(run_service_loop())
    except KeyboardInterrupt:
        pass
