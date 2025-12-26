
import asyncio
import sys
from database import async_session_maker
from models import Job, Order, OrderStatusEnum
from sqlmodel import select, delete

async def reset_jobs():
    async with async_session_maker() as session:
        print("--- RESETTING JOB QUEUE ---")
        
        # 1. Delete all Jobs
        print("Deleting all Jobs...")
        await session.execute(delete(Job))
        
        # 2. Reset IN_PROGRESS Orders to OPEN
        print("Resetting IN_PROGRESS orders to OPEN...")
        result = await session.execute(select(Order).where(Order.status == OrderStatusEnum.IN_PROGRESS))
        orders = result.scalars().all()
        
        count = 0
        for order in orders:
            order.status = OrderStatusEnum.OPEN
            session.add(order)
            count += 1
            
        await session.commit()
        print(f"DONE. Deleted Jobs. Reset {count} Orders to OPEN.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(reset_jobs())
