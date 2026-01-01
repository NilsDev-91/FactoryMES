import asyncio
import sys
import os
from sqlmodel import select
from sqlalchemy.orm import selectinload

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.core import Product
from app.models.product_sku import ProductSKU

# Create Local Engine (Clean Output)
engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def debug_skus():
    async with async_session_maker() as session:
        # 1. Find Products
        stmt = select(Product).where(
            (Product.name.ilike("%Zylinder%"))
        )
        products = (await session.exec(stmt)).all()

        if not products:
            print("❌ No Products found matching 'Zylinder'.")
            return

        for prod in products:
            print(f"\n📦 Product: {prod.name} (ID: {prod.id}, Master SKU: {prod.sku})")
            
            # 2. Find Variants (SKUs)
            sku_stmt = select(ProductSKU).where(ProductSKU.product_id == prod.id)
            variants = (await session.exec(sku_stmt)).all()

            if not variants:
                print("   ⚠️ No Variants (SKUs) found for this product.")
                continue

            for var in variants:
                print(f"   - Variant: {var.name}")
                print(f"     SKU:  {var.sku}")
                print(f"     HEX:  {var.hex_color}")
                print(f"     PID:  {var.parent_id}")

        print("\n" + "="*50 + "\n")

if __name__ == "__main__":
    # Remove SQLModel rich formatting for raw string extraction if needed or use rich
    try:
        from rich import print
    except ImportError:
        pass
        
    asyncio.run(debug_skus())
