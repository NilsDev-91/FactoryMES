import asyncio
from sqlmodel import text
from app.core.database import engine

async def add_product_column():
    print("🛠️  Starting Migration: Adding 'filament_requirements' to 'products'...")
    
    try:
        async with engine.begin() as conn:
            # Using JSONB for better performance/indexing capability in Postgres
            await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS filament_requirements JSONB;"))
            
        print("✅ Successfully added 'filament_requirements' column to 'products' table.")
        
    except Exception as e:
        print(f"❌ Migration Failed: {e}")

if __name__ == "__main__":
    asyncio.run(add_product_column())
