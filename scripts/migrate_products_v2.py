import asyncio
from sqlalchemy import text
from sqlmodel import SQLModel
from app.core.database import engine
from app.models import * # Ensure all models are imported for metadata discovery

async def migrate():
    print("🚀 Starting Database Migration (Phase 2)...")
    async with engine.begin() as conn:
        # 1. Create all tables (this will create 'product_requirements' if missing)
        await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ Tables initialized.")

        # 2. Add columns to 'products' if missing
        try:
            await conn.execute(text("""
                ALTER TABLE products 
                ADD COLUMN IF NOT EXISTS print_file_id INTEGER REFERENCES print_files(id),
                ADD COLUMN IF NOT EXISTS is_catalog_visible BOOLEAN DEFAULT TRUE;
            """))
            print("✅ Columns added to 'products'.")
        except Exception as e:
            print(f"ℹ️ Could not add columns to 'products': {e}")

    print("🏁 Migration Complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
