import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def migrate_postgres():
    print("Starting PostgreSQL Migration...")
    
    database_url = settings.ASYNC_DATABASE_URL
    print(f"Connecting to: {database_url}")
    
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        print("Checking for 'current_job_id' column...")
        # Check column existence in PostgreSQL
        # We can just try to add it and ignore "duplicate column" error, or check information_schema
        # Simple "ADD COLUMN IF NOT EXISTS" is valid in newer Postgres (v9.6+)
        
        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN IF NOT EXISTS current_job_id INTEGER"))
            print("✅ 'current_job_id' column verified/added.")
        except Exception as e:
            print(f"❌ Error adding column: {e}")

        print("Checking for 'product_skus' table...")
        try:
             await conn.execute(text("""
                CREATE TABLE IF NOT EXISTS product_skus (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
                    sku VARCHAR NOT NULL UNIQUE,
                    hex_color VARCHAR NOT NULL,
                    color_name VARCHAR NOT NULL
                )
            """))
             # Create index manually if needed? UNIQUE checks implied index.
             print("✅ 'product_skus' table verified/created.")
        except Exception as e:
             print(f"❌ Error creating table: {e}")

    await engine.dispose()
    print("Migration Complete.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate_postgres())
