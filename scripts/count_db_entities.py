import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings

async def count_entities():
    database_url = settings.ASYNC_DATABASE_URL
    engine = create_async_engine(database_url)
    
    async with engine.connect() as conn:
        res_prod = await conn.execute(text("SELECT count(*) FROM products"))
        prod_count = res_prod.scalar()
        
        res_sku = await conn.execute(text("SELECT count(*) FROM product_skus"))
        sku_count = res_sku.scalar()
        
        print(f"Products: {prod_count}")
        print(f"Product SKUs: {sku_count}")
        
    await engine.dispose()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(count_entities())
