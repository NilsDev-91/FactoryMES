import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.product_sku import ProductSKU
from app.models.core import Product
from app.core.config import settings

# Use the computed async property
DATABASE_URL = settings.ASYNC_DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def verify_hierarchy():
    async with async_session_maker() as session:
        print("--- Testing ProductSKU Hierarchy ---")
        
        # 1. Create a Master SKU
        master_sku_val = "MASTER_TEST_001"
        master = ProductSKU(
            sku=master_sku_val,
            name="Master Product",
            is_catalog_visible=True
        )
        session.add(master)
        await session.commit()
        await session.refresh(master)
        print(f"Created Master SKU: {master.sku} (ID: {master.id})")
        
        # 2. Create Variant SKUs (Children)
        variant1 = ProductSKU(
            sku="VAR_RED_001",
            name="Red Variant",
            parent_id=master.id,
            is_catalog_visible=False
        )
        variant2 = ProductSKU(
            sku="VAR_BLUE_001",
            name="Blue Variant",
            parent_id=master.id,
            is_catalog_visible=False
        )
        session.add(variant1)
        session.add(variant2)
        await session.commit()
        
        # 3. Verify Relationship
        await session.refresh(master)
        # Re-fetch with selectin loading (though already set in model)
        result = await session.execute(
            select(ProductSKU).where(ProductSKU.id == master.id)
        )
        master_fetched = result.scalar_one()
        
        print(f"Master '{master_fetched.name}' has {len(master_fetched.children)} children:")
        for child in master_fetched.children:
            print(f" - Child SKU: {child.sku}, Name: {child.name}, Visible: {child.is_catalog_visible}")
            assert child.parent_id == master_fetched.id
            
        assert len(master_fetched.children) == 2
        print("Relationship verification SUCCESSFUL!")

        # 4. Clean up
        await session.delete(variant1)
        await session.delete(variant2)
        await session.delete(master)
        await session.commit()
        print("Cleanup successful.")

if __name__ == "__main__":
    try:
        asyncio.run(verify_hierarchy())
    except Exception as e:
        print(f"Verification FAILED: {e}")
        sys.exit(1)
