
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check_schema():
    async with engine.connect() as conn:
        print("\n--- Columns in ams_slots ---")
        # Ensure we are checking the right table in the right schema
        res = await conn.execute(text(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'ams_slots' ORDER BY column_name"
        ))
        rows = res.fetchall()
        if not rows:
            print("!!! TABLE ams_slots NOT FOUND IN information_schema !!!")
        for row in rows:
            print(f"| {row[0]:<20} | {row[1]:<20} |")

if __name__ == "__main__":
    asyncio.run(check_schema())
