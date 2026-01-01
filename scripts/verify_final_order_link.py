import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.orm import selectinload

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Job
from app.models.order import Order

async def verify_order_link():
    async with async_session_maker() as session:
        stmt = select(Job).where(Job.id == 48).options(selectinload(Job.order))
        job = (await session.exec(stmt)).first()
        
        with open("final_verification.txt", "w", encoding="utf-8") as f:
            if job and job.order:
                f.write(f"Job 48 linked to Order: {job.order.ebay_order_id}\n")
                f.write(f"Job Status: {job.status}\n")
                f.write(f"Printer: {job.assigned_printer_serial}\n")
            else:
                f.write("Job 48 or its Order not found.\n")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_order_link())
