import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT id, status FROM jobs"))
        for row in res:
            print(f"Job {row[0]}: {row[1]}")

if __name__ == "__main__":
    asyncio.run(check())
