
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check_tables():
    async with engine.connect() as conn:
        res = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'"))
        tables = [r[0] for r in res.fetchall()]
        print(f"Tables in DB: {tables}")
        
        if 'ams_slots' in tables:
            print("\nColumns in ams_slots:")
            cols = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='ams_slots'"))
            print([c[0] for c in cols.fetchall()])

if __name__ == "__main__":
    asyncio.run(check_tables())
