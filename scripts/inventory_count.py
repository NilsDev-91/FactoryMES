import asyncio
import sys
import os
from sqlalchemy import func
from sqlmodel import select

# Add the project root to sys.path to allow absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# Local engine to avoid SQL logging in the report
engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

from app.models.core import Product
from app.models.product_sku import ProductSKU

async def count_inventory():
    async with async_session_maker() as session:
        # 1. Total Products (Abstract)
        product_count_stmt = select(func.count()).select_from(Product)
        total_products = (await session.exec(product_count_stmt)).one()

        # 2. Total SKUs (Concrete)
        sku_count_stmt = select(func.count()).select_from(ProductSKU)
        total_skus = (await session.exec(sku_count_stmt)).one()

        # 3. Master SKUs (parent_id is None)
        master_sku_stmt = select(func.count()).select_from(ProductSKU).where(ProductSKU.parent_id == None)
        master_skus = (await session.exec(master_sku_stmt)).one()

        # 4. Variant SKUs (parent_id is NOT None)
        variant_sku_stmt = select(func.count()).select_from(ProductSKU).where(ProductSKU.parent_id != None)
        variant_skus = (await session.exec(variant_sku_stmt)).one()

        # Output the report
        print("\n--- FactoryMES Inventory Report ---")
        print(f"📦 Total Products (Abstract): {total_products}")
        print(f"🏷️ Total SKUs (Concrete):     {total_skus}")
        print(f"   ├─ Master SKUs:            {master_skus}")
        print(f"   └─ Variant SKUs (Child):   {variant_skus}")
        print("-----------------------------------\n")

if __name__ == "__main__":
    asyncio.run(count_inventory())
