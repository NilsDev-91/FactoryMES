import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def migrate_hierarchy():
    print("Starting ProductSKU Hierarchy Migration...")
    
    database_url = settings.ASYNC_DATABASE_URL
    print(f"Connecting to: {database_url}")
    
    engine = create_async_engine(database_url, echo=True)

    async with engine.begin() as conn:
        print("Checking for missing columns in 'product_skus'...")
        
        # 1. Add 'name' column (making it nullable first if existing data exists, or just adding it)
        try:
            await conn.execute(text("ALTER TABLE product_skus ADD COLUMN IF NOT EXISTS name VARCHAR DEFAULT 'Unnamed SKU'"))
            # Optionally remove default or set NOT NULL after populating, 
            # but for a migration script 'ADD COLUMN IF NOT EXISTS' is safer.
            print("✅ 'name' column verified/added.")
        except Exception as e:
            print(f"❌ Error adding 'name': {e}")

        # 2. Add 'is_catalog_visible' column
        try:
            await conn.execute(text("ALTER TABLE product_skus ADD COLUMN IF NOT EXISTS is_catalog_visible BOOLEAN DEFAULT TRUE"))
            print("✅ 'is_catalog_visible' column verified/added.")
        except Exception as e:
            print(f"❌ Error adding 'is_catalog_visible': {e}")

        # 3. Add 'parent_id' column
        try:
            await conn.execute(text("ALTER TABLE product_skus ADD COLUMN IF NOT EXISTS parent_id INTEGER REFERENCES product_skus(id)"))
            print("✅ 'parent_id' column verified/added.")
        except Exception as e:
            print(f"❌ Error adding 'parent_id': {e}")
            
        # 4. Ensure hex_color, color_name, and product_id are NULLABLE
        try:
            await conn.execute(text("ALTER TABLE product_skus ALTER COLUMN hex_color DROP NOT NULL"))
            await conn.execute(text("ALTER TABLE product_skus ALTER COLUMN color_name DROP NOT NULL"))
            await conn.execute(text("ALTER TABLE product_skus ALTER COLUMN product_id DROP NOT NULL"))
            print("✅ 'hex_color', 'color_name', and 'product_id' set to NULLABLE.")
        except Exception as e:
            print(f"❌ Error altering columns: {e}")

    await engine.dispose()
    print("Migration Complete.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(migrate_hierarchy())
