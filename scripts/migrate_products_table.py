import asyncio
from sqlalchemy import text
from app.core.database import async_session_maker

async def migrate_db():
    print("🛠️  Migrating Database Schema...")
    
    async with async_session_maker() as session:
        try:
            # Check if column exists first? 
            # Or just try to add it and catch error (Postgres specific: IF NOT EXISTS is cleaner)
            
            # Using raw SQL to alter table
            sql = "ALTER TABLE products ADD COLUMN IF NOT EXISTS filament_requirements JSON;"
            await session.exec(text(sql))
            await session.commit()
            print("✅ Successfully added 'filament_requirements' column to 'products'.")
            
        except Exception as e:
            print(f"❌ Migration Failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate_db())
