
import asyncio
import sys
from database import async_session_maker
from models import Job, Order, JobStatusEnum, OrderStatusEnum
from sqlmodel import select

async def check_jobs():
    async with async_session_maker() as session:
        print("--- Checking JOBS ---")
        result = await session.execute(select(Job))
        jobs = result.scalars().all()
        if not jobs:
            print("NO JOBS FOUND IN DB.")
        else:
            for j in jobs:
                print(f"Job {j.id}: Order={j.order_id} Status={j.status} Printer={j.assigned_printer_serial}")

        print("\n--- Checking OPEN ORDERS ---")
        result = await session.execute(select(Order).where(Order.status == OrderStatusEnum.OPEN))
        orders = result.scalars().all()
        if not orders:
            print("NO OPEN ORDERS FOUND.")
        else:
            for o in orders:
                print(f"Order {o.id}: SKU={o.sku} Status={o.status}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_jobs())
