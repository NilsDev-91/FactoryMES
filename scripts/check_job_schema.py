import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker

async def main():
    async with async_session_maker() as session:
        result = await session.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name = 'jobs'"))
        columns = [row[0] for row in result.fetchall()]
        print(f"Columns in 'jobs' table: {columns}")
        if 'priority' in columns:
            print("✅ 'priority' column exists.")
        else:
            print("❌ 'priority' column MISSING.")

if __name__ == "__main__":
    asyncio.run(main())
