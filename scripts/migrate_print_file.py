import asyncio
from sqlalchemy import text
from app.core.database import engine
from app.models.core import SQLModel
from app.models.print_file import PrintFile # Ensure it's imported for metadata

async def migrate():
    print("🚀 Starting Database Migration...")
    async with engine.begin() as conn:
        # 1. Create all tables (this will create 'print_files' if missing)
        # We need to ensure metadata is populated. 
        # Since PrintFile is imported, it should be in SQLModel.metadata.
        await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ Tables initialized.")

        # 2. Add print_file_id column to product_skus if missing
        # PostgreSQL syntax: ALTER TABLE product_skus ADD COLUMN IF NOT EXISTS print_file_id INTEGER REFERENCES print_files(id);
        try:
            await conn.execute(text("""
                ALTER TABLE product_skus 
                ADD COLUMN IF NOT EXISTS print_file_id INTEGER 
                REFERENCES print_files(id);
            """))
            print("✅ Column 'print_file_id' added to 'product_skus'.")
        except Exception as e:
            print(f"ℹ️ Could not add column (it might already exist): {e}")

    print("🏁 Migration Complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
