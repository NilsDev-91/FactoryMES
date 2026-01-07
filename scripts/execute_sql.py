import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlalchemy import text

async def execute_sql(query):
    async with async_session_maker() as session:
        result = await session.execute(text(query))
        try:
            rows = result.fetchall()
            for row in rows:
                print(row)
        except Exception:
            print("Query executed (no rows returned).")
        await session.commit()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(execute_sql(sys.argv[1]))
    else:
        print("Usage: python execute_sql.py \"SQL QUERY\"")
