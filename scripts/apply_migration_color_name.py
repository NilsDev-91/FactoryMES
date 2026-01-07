import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlalchemy import text

async def apply_migration():
    async with async_session_maker() as session:
        print("🛠️ Applying migration: add_color_name_to_filament_and_ams...")
        try:
            await session.execute(text("ALTER TABLE filament_profiles ADD COLUMN IF NOT EXISTS color_name VARCHAR;"))
            await session.execute(text("ALTER TABLE ams_slots ADD COLUMN IF NOT EXISTS color_name VARCHAR;"))
            await session.commit()
            print("✅ Migration applied successfully.")
        except Exception as e:
            await session.rollback()
            print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(apply_migration())
