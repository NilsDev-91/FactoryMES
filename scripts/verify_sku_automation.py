import asyncio
import sys
import os
import uuid

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select, delete
from app.models.core import Product
from app.models.product_sku import ProductSKU
from app.models.filament import FilamentProfile
from app.services.product_service import ProductService, ProductCreateDTO
from app.services.catalog_service import get_public_catalog

async def verify_sku_automation():
    async with async_session_maker() as session:
        # 1. Get profiles
        print("--- Fetching profiles ---")
        black_prof = (await session.exec(select(FilamentProfile).where(FilamentProfile.color_name == "Black"))).first()
        red_prof = (await session.exec(select(FilamentProfile).where(FilamentProfile.color_name == "Red"))).first()
        
        if not black_prof or not red_prof:
            print("❌ Could not find Black or Red profiles. Run setup_smart_data.py first.")
            return

        # 2. Setup Test Product
        test_sku = f"AUTO-TEST-{uuid.uuid4().hex[:4].upper()}"
        print(f"--- Creating Product with SKU: {test_sku} ---")
        
        dto = ProductCreateDTO(
            name="Auto Test Product",
            sku=test_sku,
            description="Testing automated SKU generation",
            print_file_id=1, # Mock file ID
            part_height_mm=25.5,
            generate_variants_for_profile_ids=[black_prof.id, red_prof.id]
        )
        
        # 3. Create Product
        product = await ProductService.create_product(dto, session)
        print(f"OK: Product created: ID {product.id}")
        
        # 4. Verify Variants
        print("--- Verifying child SKUs ---")
        expected_skus = {f"{test_sku}-BLACK", f"{test_sku}-RED"}
        
        # Refresh variants
        stmt = select(ProductSKU).where(ProductSKU.product_id == product.id)
        variants = (await session.exec(stmt)).all()
        
        found_skus = {v.sku for v in variants}
        print(f"Found SKUs: {found_skus}")
        
        for expected in expected_skus:
            if expected not in found_skus:
                print(f"❌ Missing expected SKU: {expected}")
            else:
                print(f"   - Found {expected}")

        # Check visibility
        for v in variants:
            if v.parent_id is not None: # It's a child
                if v.is_catalog_visible:
                    print(f"❌ Child SKU {v.sku} should NOT be catalog visible.")
                else:
                    print(f"   - {v.sku} visibility is correctly False")
                
                if v.print_file_id != dto.print_file_id:
                    print(f"❌ Child SKU {v.sku} did not inherit print_file_id.")
                else:
                    print(f"   - {v.sku} inherited print_file_id {v.print_file_id}")

        # 5. Verify Catalog
        print("--- Checking Public Catalog ---")
        catalog = await get_public_catalog(session)
        target_display = next((p for p in catalog if p.sku == test_sku), None)
        
        if not target_display:
            print(f"FAIL: Master SKU {test_sku} not found in catalog.")
        else:
            print(f"OK: Master SKU found in catalog.")
            print(f"   - Name: {target_display.name}")
            print(f"   - Colors: {target_display.variant_colors}")
            if "#000000" in target_display.variant_colors and "#FF0000" in target_display.variant_colors:
                print(f"   - Correct color HEX codes found in DTO.")
            else:
                print(f"❌ Missing expected colors in catalog DTO.")

        # Cleanup
        print("--- Cleaning up test data ---")
        await ProductService.delete_product(product.id, session)
        await session.commit()
        print("DONE: Verification complete!")

if __name__ == "__main__":
    asyncio.run(verify_sku_automation())
