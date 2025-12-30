import asyncio
from sqlalchemy import text
from app.core.database import engine

async def check_schema():
    print("📋 Checking PostgreSQL Schema Column Types...")
    async with engine.connect() as conn:
        tables = ["print_files", "products", "jobs", "orders"]
        for table in tables:
            print(f"--- Table: {table} ---")
            try:
                # Query information_schema for column types
                stmt = text(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = '{table}';
                """)
                result = await conn.execute(stmt)
                for row in result:
                    print(f"Column: {row.column_name}, Type: {row.data_type}")
            except Exception as e:
                print(f"Error checking {table}: {e}")

if __name__ == "__main__":
    asyncio.run(check_schema())
