import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def fix_schema():
    print("🔧 Starting Database Schema Repair...")
    
    database_url = settings.ASYNC_DATABASE_URL
    print(f"📡 Connecting to database...")
    
    # Use isolation_level="AUTOCOMMIT" to allow ALTER TYPE
    engine = create_async_engine(database_url, isolation_level="AUTOCOMMIT", echo=True)

    async with engine.connect() as conn:
        # 1. Add current_job_id column
        print("🔍 Checking 'current_job_id' column in 'printers' table...")
        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN IF NOT EXISTS current_job_id INTEGER;"))
            print("✅ 'current_job_id' column verified/added.")
        except Exception as e:
            print(f"❌ Error checking/adding column: {e}")

        # 2. Update PrinterStatusEnum
        print("🔍 Checking 'printerstatusenum' type for 'AWAITING_CLEARANCE'...")
        try:
            # We try to add the value. 
            # Note: IF NOT EXISTS for enum values is only available in Postgres 12+
            # If older, we might need a catch.
            await conn.execute(text("ALTER TYPE printerstatusenum ADD VALUE IF NOT EXISTS 'AWAITING_CLEARANCE';"))
            print("✅ 'printerstatusenum' updated with 'AWAITING_CLEARANCE'.")
        except Exception as e:
            # Fallback for older postgres or if it fails for another reason
            print(f"ℹ️ Attempting alternative enum update check because: {e}")
            try:
                # Check if exists first
                result = await conn.execute(text("SELECT 1 FROM pg_enum WHERE enumlabel = 'AWAITING_CLEARANCE' AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'printerstatusenum')"))
                if result.scalar():
                     print("✅ 'AWAITING_CLEARANCE' already exists in enum.")
                else:
                     await conn.execute(text("ALTER TYPE printerstatusenum ADD VALUE 'AWAITING_CLEARANCE';"))
                     print("✅ 'printerstatusenum' updated with 'AWAITING_CLEARANCE'.")
            except Exception as e2:
                print(f"❌ Critical Error updating enum: {e2}")

    await engine.dispose()
    print("✨ Schema Repair Complete.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_schema())
