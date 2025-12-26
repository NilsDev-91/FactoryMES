
import asyncio
import sys
import uuid
from datetime import datetime
from sqlmodel import select
from database import async_session_maker
from models import Order, OrderStatusEnum, PlatformEnum

async def create_order(sku: str, quantity: int = 1):
    async with async_session_maker() as session:
        new_order = Order(
            platform=PlatformEnum.ETSY,
            platform_order_id=str(uuid.uuid4())[:12],
            sku=sku,
            quantity=quantity,
            status=OrderStatusEnum.OPEN,
            purchase_date=datetime.now()
        )
        session.add(new_order)
        await session.commit()
        await session.refresh(new_order)
        print(f"[{datetime.now().time()}] Created Order {new_order.id} for {sku}")
        return new_order.id

async def wait_for_printing(order_id: int):
    print(f"Waiting for Order {order_id} to start printing...")
    while True:
        async with async_session_maker() as session:
            order = await session.get(Order, order_id)
            if order and order.status == OrderStatusEnum.PRINTING:
                print(f"[{datetime.now().time()}] Order {order_id} is now PRINTING!")
                return
            
            # Also check if it went to DONE (skipped?)
            if order and order.status == OrderStatusEnum.DONE:
                 print(f"[{datetime.now().time()}] Order {order_id} went straight to DONE.")
                 return

        await asyncio.sleep(2)

async def run_scenario():
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    print("--- STARTING PRODUCTION SIMULATION ---")
    
    # 1. Push white_eye
    order_id = await create_order("white_eye")
    
    # 2. Wait for it to start printing
    await wait_for_printing(order_id)
    
    # 3. Wait 1 min
    print("Waiting 60 seconds before next order...")
    await asyncio.sleep(60)
    
    # 4. Push red_tooth
    await create_order("red_tooth")
    
    print("--- SIMULATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_scenario())
