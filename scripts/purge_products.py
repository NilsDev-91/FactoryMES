import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select, delete
from app.models.core import Product
from app.models.product_sku import ProductSKU
from app.models.core import ProductRequirement

async def purge_products():
    async with async_session_maker() as session:
        print("🧹 Purging all products, SKUs, and requirements...")
        
        # Cascading delete usually handles children, but let's be explicit for a deep clean
        await session.execute(delete(ProductRequirement))
        await session.execute(delete(ProductSKU))
        await session.execute(delete(Product))
        
        await session.commit()
    print("✨ Database cleared of all products.")

if __name__ == "__main__":
    asyncio.run(purge_products())
