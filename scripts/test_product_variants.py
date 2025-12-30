import asyncio
import sys
import os
import uuid

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker, engine
from app.models.core import Product, ProductVariant, SQLModel
from sqlmodel import select, text
from app.routers.products import ProductDefinitionRequest, VariantDefinition, create_product_with_variants

# Mock Storage Dir for test
import app.routers.products as prod_router
prod_router.STORAGE_DIR = "." # Use current dir just to pass file check

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def test_create_variants():
    print("Testing Product Variant Creation...")

    # Create dummy 3mf file
    test_file = "test_variant_creation.3mf"
    with open(test_file, "w") as f:
        f.write("dummy content")

    try:
        req = ProductDefinitionRequest(
            name="Variant Test Product",
            filename_3mf=test_file,
            allowed_variants=[
                VariantDefinition(hex_code="#FF0000", color_name="Red"),
                VariantDefinition(hex_code="#0000FF", color_name="Blue")
            ]
        )

        async with async_session_maker() as session:
            # Clean up previous runs
            existing = await session.exec(select(Product).where(Product.name == req.name))
            for p in existing.all():
                await session.delete(p)
            await session.commit()

            # Call logic
            # We mock Depends(get_session) by passing session directly
            product = await create_product_with_variants(req, session)
            
            print(f"✅ Product Created: ID={product.id}, Name={product.name}, SKU={product.sku}")
            
            # Verify Variants
            await session.refresh(product, ["variants"])
            print(f"Variants Count: {len(product.variants)}")
            
            for v in product.variants:
                print(f" - SKU: {v.sku} | Color: {v.color_name} ({v.hex_code})")
                
            if len(product.variants) != 2:
                print("❌ Expected 2 variants.")
            else:
                print("✅ Variant count correct.")
                
            # Verify SKUs
            skus = [v.sku for v in product.variants]
            if "VARIANT_TEST_PRODUCT_RED" in skus and "VARIANT_TEST_PRODUCT_BLUE" in skus:
                 print("✅ SKUs generated correctly.")
            else:
                 print(f"❌ Unexpected SKUs: {skus}")

    except Exception as e:
        print(f"❌ Test Failed: {e}")
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_create_variants())
