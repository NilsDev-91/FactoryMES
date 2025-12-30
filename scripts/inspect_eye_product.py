import asyncio
import os
import sys
# Ensure app modules are found
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload

from app.core.config import settings
from app.models.core import Product
from app.models.product_sku import ProductSKU

async def inspect_eye_product():
    print("🔌 Connecting to Database...")
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("\n🔍 INSPECTING PARENT PRODUCT: 'Eye'")
        # Fetch Parent
        stmt = select(Product).where(Product.name == "Eye")
        parent = (await session.exec(stmt)).first()
        
        if not parent:
            print("❌ Parent Product 'Eye' NOT FOUND.")
            return

        print(f"✅ FOUND Parent ID: {parent.id}")
        print(f"   Name: {parent.name}")
        print(f"   Legacy File Path (file_path_3mf): {parent.file_path_3mf}")
        
        print("\n🔍 INSPECTING CHILD VARIANTS (ProductSKUs)")
        # Fetch Children (ProductSKUs linked to this Product)
        # Note: We check if they are linked via product_id (Legacy/Transition) or parent_id (SKU hierarchy)?
        # The user mentioned "Variants" in their request, which usually implies ProductSKU.
        
        stmt_skus = select(ProductSKU).where(ProductSKU.product_id == parent.id).options(
            selectinload(ProductSKU.print_file)
        )
        skus = (await session.exec(stmt_skus)).all()
        
        if not skus:
            print("⚠️  No ProductSKUs found linked to this Parent Product ID.")
            # Try matching by name just in case
            print("   (Checking by name similarity 'Eye'...)")
            stmt_fuzzy = select(ProductSKU).where(ProductSKU.name.contains("Eye")).options(
                selectinload(ProductSKU.print_file)
            )
            skus = (await session.exec(stmt_fuzzy)).all()
        
        print(f"   Found {len(skus)} SKUs:")
        
        for sku in skus:
            print(f"\n   👉 SKU ID: {sku.id} | Name: '{sku.name}'")
            print(f"      SKU Code: {sku.sku}")
            print(f"      Hex Color: {sku.hex_color}")
            
            # File Path Check
            file_source = "NONE"
            path = "N/A"
            
            if sku.print_file:
                path = sku.print_file.file_path
                file_source = f"ProductSKU.print_file (ID: {sku.print_file_id})"
            elif parent.file_path_3mf:
                path = parent.file_path_3mf
                file_source = "INHERITED (Parent Product)"
            
            print(f"      📂 RESOLVED FILE: {path}")
            print(f"         Source: {file_source}")
            
            if "bdc" in str(path):
                print("         🚨 MATCH: This URL contains the mysterious 'bdc' UUID!")

if __name__ == "__main__":
    asyncio.run(inspect_eye_product())
