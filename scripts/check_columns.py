
import asyncio
from app.core.database import engine
from sqlalchemy import text

async def check():
    async with engine.connect() as conn:
        try:
            # Check Printers
            print("Checking printers...")
            result = await conn.execute(text("SELECT jobs_since_calibration, calibration_interval FROM printers LIMIT 1"))
            print("Printers columns exist.")
        except Exception as e:
            print(f"Printers Error: {e}")

        try:
            # Check Jobs
            print("Checking jobs...")
            result = await conn.execute(text("SELECT job_metadata, updated_at FROM jobs LIMIT 1"))
            print("Jobs columns exist.")
        except Exception as e:
            print(f"Jobs Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
