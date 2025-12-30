import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    print("🚀 Starting Database Migration (PrintFile Timestamp)...")
    async with engine.begin() as conn:
        try:
            # PostgreSQL syntax: ALTER TABLE print_files ADD COLUMN IF NOT EXISTS upload_timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
            await conn.execute(text("""
                ALTER TABLE print_files 
                ADD COLUMN IF NOT EXISTS upload_timestamp TIMESTAMP WITH TIME ZONE 
                DEFAULT CURRENT_TIMESTAMP;
            """))
            print("✅ Column 'upload_timestamp' added to 'print_files'.")
        except Exception as e:
            print(f"ℹ️ Could not add column: {e}")

    print("🏁 Migration Complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
