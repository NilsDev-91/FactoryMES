
import asyncio
import sys
from sqlmodel import select
from database import async_session_maker
from models import Order, Job, JobStatusEnum, OrderStatusEnum

async def create_job():
    async with async_session_maker() as session:
        # Find the test order
        result = await session.execute(select(Order).where(Order.sku == "BENCHY_TEST"))
        order = result.scalars().first()
        
        if not order:
            print("Test order not found. Run init_db.py first.")
            return

        # Check if job already exists
        result = await session.execute(select(Job).where(Job.order_id == order.id))
        job = result.scalars().first()
        
        if not job:
            print("Creating PENDING Job for Order...")
            job = Job(
                order_id=order.id,
                gcode_path="models/benchy.gcode",
                status=JobStatusEnum.PENDING,
                created_at=order.purchase_date
            )
            session.add(job)
            await session.commit()
            print(f"Job created with ID: {job.id}")
        else:
            print(f"Job already exists with status: {job.status}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(create_job())
