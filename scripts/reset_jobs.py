import asyncio
from sqlalchemy import text
from app.core.database import engine

async def reset():
    async with engine.connect() as conn:
        print("Resetting FAILED jobs to PENDING...")
        await conn.execute(text("UPDATE jobs SET status = 'PENDING', error_message = NULL WHERE status = 'FAILED'"))
        await conn.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(reset())
