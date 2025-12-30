import asyncio
from sqlalchemy import text
from app.core.database import engine

async def fix_table(table, col):
    print(f"🛠 Fixing {table}.{col}...")
    async with engine.begin() as conn:
        try:
            stmt = text(f"UPDATE {table} SET {col} = {col} AT TIME ZONE 'UTC' WHERE {col} IS NOT NULL;")
            await conn.execute(stmt)
            print(f"✅ Fixed {table}.{col}")
        except Exception as e:
            print(f"❌ Error fixing {table}.{col}: {e}")

async def main():
    tables_cols = [
        ("products", "created_at"),
        ("jobs", "created_at"),
        ("orders", "created_at")
    ]
    for table, col in tables_cols:
        await fix_table(table, col)

if __name__ == "__main__":
    asyncio.run(main())
