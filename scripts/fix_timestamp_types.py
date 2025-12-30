import asyncio
from sqlalchemy import text
from app.core.database import engine

async def fix_schema_types():
    print("🚀 Altering Column Types to TIMESTAMP WITH TIME ZONE...")
    async with engine.begin() as conn:
        tables_cols = [
            ("products", "created_at"),
            ("jobs", "created_at"),
            ("orders", "created_at"),
            ("print_files", "upload_timestamp")
        ]
        
        for table, col in tables_cols:
            print(f"🛠 Processing {table}.{col}...")
            try:
                # 1. Alter type to WITH TIME ZONE
                # 2. Add AT TIME ZONE 'UTC' if they were naive
                # In PostgreSQL: ALTER TABLE ... ALTER COLUMN ... TYPE ... USING ...
                stmt = text(f"""
                    ALTER TABLE {table} 
                    ALTER COLUMN {col} TYPE TIMESTAMP WITH TIME ZONE 
                    USING {col} AT TIME ZONE 'UTC';
                """)
                await conn.execute(stmt)
                print(f"✅ Altered and fixed {table}.{col}")
            except Exception as e:
                print(f"❌ Error processing {table}.{col}: {e}")

if __name__ == "__main__":
    asyncio.run(fix_schema_types())
