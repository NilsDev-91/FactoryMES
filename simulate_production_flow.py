from app.core.database import async_session_maker
from app.models.core import Job, OrderStatusEnum
from app.models.order import Order, OrderItem
from sqlalchemy import text
from datetime import datetime
import asyncio
import time

async def run_simulation():
    print("--- STARTING PRODUCTION SIMULATION (CLEAN START) ---")
    
    async with async_session_maker() as session:
        # 1. PURGE (Clean Slate)
        print("1. PURGING existing Orders and Jobs...")
        # Note: Delete jobs first due to FK constraint
        await session.execute(text("DELETE FROM order_items"))
        await session.execute(text("DELETE FROM jobs"))
        await session.execute(text("DELETE FROM orders"))
        await session.commit()
        print("   -> Database Cleared.")
        
        # 2. Create White Eye Order
        print(f"\n[{datetime.now().time()}] 2. Creating Order 1: 'white_eye'")
        order1 = Order(
            ebay_order_id=f"SIM-{int(time.time())}-1",
            buyer_username="sim_buyer_1",
            total_price=9.99,
            currency="EUR",
            status="OPEN"
        )
        session.add(order1)
        await session.flush()
        
        item1 = OrderItem(order_id=order1.id, sku="white_eye", title="White Eye", quantity=1)
        session.add(item1)
        
        await session.commit()
        await session.refresh(order1)
        print(f"   -> 'white_eye' Order Created (ID: {order1.id})")

        # 3. Wait 5 Seconds
        print("\n3. Waiting 5 seconds...")
        await asyncio.sleep(5)
        
        # 4. Create Red Tooth Order
        print(f"\n[{datetime.now().time()}] 4. Creating Order 2: 'red_tooth'")
        order2 = Order(
            ebay_order_id=f"SIM-{int(time.time())}-2",
            buyer_username="sim_buyer_2",
            total_price=14.99,
            currency="EUR",
            status="OPEN"
        )
        session.add(order2)
        await session.flush()
        
        item2 = OrderItem(order_id=order2.id, sku="red_tooth", title="Red Tooth", quantity=1)
        session.add(item2)
        
        await session.commit()
        await session.refresh(order2)
        print(f"   -> 'red_tooth' Order Created (ID: {order2.id})")
        
        print("\n--- SIMULATION ORDERS PLACED ---")
        print("Now Check if:")
        print("1. White Eye -> FAILED (if upload fails as expected)")
        print("2. Red Tooth -> PRINTING (after delay)")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_simulation())
