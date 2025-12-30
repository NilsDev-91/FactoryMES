import asyncio
from sqlmodel import text
from app.core.database import engine

async def check_db():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table';"))
        tables = result.scalars().all()
        print("Database tables:")
        for table in tables:
            print(f" - {table}")

if __name__ == "__main__":
    asyncio.run(check_db())
