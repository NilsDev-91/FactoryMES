
import asyncio
import sys
from database import async_session_maker
from models import Job, Order, OrderStatusEnum
from sqlmodel import select, delete

async def purge_orders():
    async with async_session_maker() as session:
        print("--- PURGING ACTIVE ORDERS ---")
        
        # 1. Delete all Jobs first (Foreign Key constraints usually cascade or need manual deletion)
        print("Deleting all Jobs...")
        await session.execute(delete(Job))
        
        # 2. Delete Orders that are NOT DONE
        # This covers OPEN, IN_PROGRESS, QUEUED, PRINTING
        print("Deleting active Orders (OPEN, QUEUED, PRINTING, IN_PROGRESS)...")
        
        # Using delete() with where clause
        stmt = delete(Order).where(Order.status != OrderStatusEnum.DONE)
        result = await session.execute(stmt)
        
        print(f"DONE. Purged active orders/jobs.")
        await session.commit()

        # Check remaining
        result = await session.execute(select(Order))
        remaining = result.scalars().all()
        print(f"Remaining (History/DONE) Orders: {len(remaining)}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(purge_orders())
