
import asyncio
import sys
from sqlalchemy import select
from database import AsyncSessionLocal, Order

async def check_orders():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Order))
        orders = result.scalars().all()
        print(f"Total Orders: {len(orders)}")
        for o in orders:
            print(f"Order {o.id}: {o.sku} - {o.status}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_orders())
