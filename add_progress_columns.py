
import asyncio
from sqlalchemy import text
from database import engine

async def add_columns():
    async with engine.begin() as conn:
        print("Checking for missing progress columns...")
        
        # Add current_progress
        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN current_progress INTEGER DEFAULT 0"))
            print("Successfully added 'current_progress'.")
        except Exception as e:
            print(f"Skipping 'current_progress' (likely exists): {e}")

        # Add remaining_time
        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN remaining_time INTEGER DEFAULT 0"))
            print("Successfully added 'remaining_time'.")
        except Exception as e:
            print(f"Skipping 'remaining_time' (likely exists): {e}")
            
        print("Done.")

if __name__ == "__main__":
    asyncio.run(add_columns())
