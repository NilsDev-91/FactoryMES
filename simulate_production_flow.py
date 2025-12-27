
import asyncio
import sys
import time
from datetime import datetime
from sqlmodel import text, select
from database import async_session_maker
from models import Order, OrderStatusEnum, PlatformEnum, Job

async def run_simulation():
    print("--- STARTING PRODUCTION SIMULATION (CLEAN START) ---")
    
    async with async_session_maker() as session:
        # 1. PURGE (Clean Slate)
        print("1. PURGING existing Orders and Jobs...")
        # Note: Delete jobs first due to FK constraint
        await session.execute(text("DELETE FROM jobs"))
        await session.execute(text("DELETE FROM orders"))
        await session.commit()
        print("   -> Database Cleared.")
        
        # 2. Create White Eye Order
        print(f"\n[{datetime.now().time()}] 2. Creating Order 1: 'white_eye'")
        order1 = Order(
            platform=PlatformEnum.EBAY,
            platform_order_id=f"SIM-{int(time.time())}-1",
            sku="white_eye",
            quantity=1,
            purchase_date=datetime.now(),
            status=OrderStatusEnum.OPEN
        )
        session.add(order1)
        await session.commit()
        await session.refresh(order1)
        print(f"   -> 'white_eye' Order Created (ID: {order1.id})")

        # 3. Wait 5 Seconds
        print("\n3. Waiting 5 seconds...")
        await asyncio.sleep(5)
        
        # 4. Create Red Tooth Order
        print(f"\n[{datetime.now().time()}] 4. Creating Order 2: 'red_tooth'")
        order2 = Order(
            platform=PlatformEnum.EBAY,
            platform_order_id=f"SIM-{int(time.time())}-2",
            sku="red_tooth",
            quantity=1,
            purchase_date=datetime.now(),
            status=OrderStatusEnum.OPEN
        )
        session.add(order2)
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
