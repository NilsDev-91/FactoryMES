
import asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings

engine = create_async_engine(settings.ASYNC_DATABASE_URL)

async def inspect():
    async with engine.connect() as conn:
        print("\n--- Raw Printers Data ---")
        result = await conn.execute(text("SELECT serial, name, current_status FROM printers"))
        rows = result.fetchall()
        for row in rows:
            print(row)

if __name__ == "__main__":
    try:
        asyncio.run(inspect())
    except Exception as e:
        print(f"Error: {e}")
