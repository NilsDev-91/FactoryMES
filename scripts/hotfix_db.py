import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.core.database import engine

async def fix_schema():
    print("Starting database schema hotfix...")
    try:
        async with engine.begin() as conn:
            print("Attempting to add filament_requirements column to jobs table...")
            # Using raw SQL to alter the table. Using IF NOT EXISTS to be safe if supported, 
            # but standard SQL for adding column usually errors if exists.
            # SQLite (if used) doesn't support IF NOT EXISTS in ADD COLUMN easily, but Postgres does.
            # Assuming Postgres based on previous logs (asyncpg).
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS filament_requirements JSON"))
            print("✅ Column 'filament_requirements' added (or already existed).")
    except Exception as e:
        print(f"❌ Error updating schema: {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_schema())
