import asyncio
import os
import sys
import uuid

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.product_sku import ProductSKU
from app.models.core import Product
from app.services.catalog_service import get_public_catalog

async def verify_catalog_refactor():
    print("Verifying Catalog Service Refactor...")
    
    async with async_session_maker() as session:
        # 1. Create Mock Data
        master_sku_name = f"Master {uuid.uuid4().hex[:4]}"
        file_path = f"storage/3mf/{uuid.uuid4()}-test_model_v1.3mf"
        
        # Create Product
        product = Product(
            name=master_sku_name,
            sku=f"P_{uuid.uuid4().hex[:4]}",
            file_path_3mf=file_path,
            required_filament_type="PLA"
        )
        session.add(product)
        await session.flush()
        
        # Create Master SKU
        master_sku = ProductSKU(
            sku=f"MSKU_{uuid.uuid4().hex[:4]}",
            name=master_sku_name,
            is_catalog_visible=True,
            product_id=product.id
        )
        session.add(master_sku)
        await session.flush()
        
        # Create Variant 1 (Red PLA)
        v1 = ProductSKU(
            sku=f"VRED_{uuid.uuid4().hex[:4]}",
            name=f"{master_sku_name} (Red)",
            parent_id=master_sku.id,
            hex_color="#FF0000",
            product_id=product.id
        )
        session.add(v1)
        
        # Create Variant 2 (Blue PETG)
        # Note: Linking to a different product to test material aggregation
        prod_petg = Product(
            name=f"{master_sku_name} (PETG)",
            sku=f"P_PETG_{uuid.uuid4().hex[:4]}",
            file_path_3mf=file_path,
            required_filament_type="PETG"
        )
        session.add(prod_petg)
        await session.flush()
        
        v2 = ProductSKU(
            sku=f"VBLUE_{uuid.uuid4().hex[:4]}",
            name=f"{master_sku_name} (Blue)",
            parent_id=master_sku.id,
            hex_color="#0000FF",
            product_id=prod_petg.id
        )
        session.add(v2)
        
        await session.commit()
        
        # 2. Test get_public_catalog
        print("\nExecuting get_public_catalog...")
        catalog = await get_public_catalog(session)
        
        # Find our test master
        target_dto = next((item for item in catalog if item.id == master_sku.id), None)
        
        if not target_dto:
            print(f"❌ Master SKU {master_sku.id} not found in catalog!")
            return
            
        print(f"✅ Master SKU found: {target_dto.name}")
        print(f"✅ Display Name: {target_dto.printfile_display_name}")
        
        expected_display_name = "test_model_v1.3mf"
        if target_dto.printfile_display_name == expected_display_name:
            print(f"✅ UUID Stripping Success: {target_dto.printfile_display_name}")
        else:
            print(f"❌ UUID Stripping Failed: Expected {expected_display_name}, got {target_dto.printfile_display_name}")
            
        print(f"✅ Colors: {target_dto.variant_colors}")
        if "#FF0000" in target_dto.variant_colors and "#0000FF" in target_dto.variant_colors:
            print("✅ Color Aggregation Success")
        else:
            print("❌ Color Aggregation Failed")
            
        print(f"✅ Materials: {target_dto.material_tags}")
        if "PLA" in target_dto.material_tags and "PETG" in target_dto.material_tags:
            print("✅ Material Aggregation Success")
        else:
            print("❌ Material Aggregation Failed")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(verify_catalog_refactor())
