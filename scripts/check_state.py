import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Job
from app.models.order import Order

async def check():
    async with async_session_maker() as session:
        orders = (await session.exec(select(Order))).all()
        jobs = (await session.exec(select(Job))).all()
        print(f"ORDERS found: {len(orders)} - {[o.ebay_order_id for o in orders]}")
        for j in jobs:
            print(f"JOB {j.id}: Status={j.status}, Printer={j.assigned_printer_serial}, Reqs={j.filament_requirements}")

if __name__ == "__main__":
    asyncio.run(check())
