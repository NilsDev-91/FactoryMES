import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker

async def main():
    print("Migrating 'printers' table: Adding 'is_plate_cleared' column...")
    async with async_session_maker() as session:
        try:
            # Add column logic: BOOLEAN DEFAULT TRUE
            await session.execute(text("ALTER TABLE printers ADD COLUMN is_plate_cleared BOOLEAN DEFAULT TRUE"))
            await session.commit()
            print("✅ Successfully added 'is_plate_cleared' column.")
        except Exception as e:
            # Check if it might be because it already exists
            if "duplicate column" in str(e):
                print("ℹ️ Column 'is_plate_cleared' already exists.")
            else:
                print(f"❌ Migration failed: {e}")
                await session.rollback()

if __name__ == "__main__":
    asyncio.run(main())
