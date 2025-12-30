import asyncio
from sqlalchemy import text
from app.core.database import engine

async def inspect_datetimes():
    async with engine.connect() as conn:
        tables = ["print_files", "products", "jobs", "orders"]
        for table in tables:
            print(f"--- Table: {table} ---")
            try:
                # Check column types and sample values
                result = await conn.execute(text(f"SELECT * FROM {table} LIMIT 1;"))
                row = result.fetchone()
                if not row:
                    print("No data.")
                    continue
                
                # Look for datetime columns
                for col in result.keys():
                    val = getattr(row, col)
                    if hasattr(val, "strftime"):
                        print(f"Column: {col}, Value: {val}, TZ: {val.tzinfo}")
            except Exception as e:
                print(f"Error inspecting {table}: {e}")

async def fix_datetimes():
    print("🚀 Attempting to fix naive datetimes in DB...")
    async with engine.begin() as conn:
        tables_cols = {
            "products": ["created_at"],
            "jobs": ["created_at"],
            "orders": ["created_at"]
        }
        
        for table, cols in tables_cols.items():
            for col in cols:
                try:
                    # PostgreSQL: cast to aware
                    stmt = text(f"UPDATE {table} SET {col} = {col} AT TIME ZONE 'UTC' WHERE {col} IS NOT NULL;")
                    await conn.execute(stmt)
                    print(f"✅ Fixed {table}.{col}")
                except Exception as e:
                    print(f"ℹ️ Could not fix {table}.{col}: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_datetimes())
    asyncio.run(fix_datetimes()) # Uncomment if needed
