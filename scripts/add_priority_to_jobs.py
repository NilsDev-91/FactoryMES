import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker

async def main():
    print("Migrating 'jobs' table: Adding 'priority' column...")
    async with async_session_maker() as session:
        try:
            await session.execute(text("ALTER TABLE jobs ADD COLUMN priority INTEGER DEFAULT 0"))
            await session.commit()
            print("✅ Successfully added 'priority' column.")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(main())
