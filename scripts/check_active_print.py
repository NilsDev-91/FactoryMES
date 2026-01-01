import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Job, Printer

async def check_active_print():
    async with async_session_maker() as session:
        # Load Printer
        p = await session.get(Printer, "03919C461802608")
        # Load latest Job assigned to this printer
        stmt = select(Job).where(Job.assigned_printer_serial == "03919C461802608").order_by(Job.id.desc()).limit(1)
        job = (await session.exec(stmt)).first()
        
        with open("active_print_check.txt", "w", encoding="utf-8") as f:
            f.write(f"Printer Status: {p.current_status}\n")
            if job:
                f.write(f"Active Job ID: {job.id}\n")
                f.write(f"Active Job Status: {job.status}\n")
                f.write(f"Error: {job.error_message}\n")
            else:
                f.write("No jobs assigned to this printer.\n")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_active_print())
