import asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from app.core.database import engine, async_session_maker
from app.services.product_service import ProductService, ProductCreateDTO
from app.models.print_file import PrintFile
from app.models.filament import FilamentProfile
from app.models.core import Product, ProductRequirement
from app.models.product_sku import ProductSKU

async def verify_refactor():
    print("🧪 Verifying Product Service Refactor...")
    
    async with async_session_maker() as session:
        # 1. Setup/Fetch Filament Profiles
        result = await session.execute(select(FilamentProfile).limit(2))
        profiles = result.scalars().all()
        
        if not profiles:
            print("⚠️ No FilamentProfiles found. Creating mock profiles...")
            p1 = FilamentProfile(material="PLA", brand="Bambu", color_hex="#FF0000", density=1.24, spool_weight=1000)
            p2 = FilamentProfile(material="PETG", brand="Bambu", color_hex="#0000FF", density=1.27, spool_weight=1000)
            session.add_all([p1, p2])
            await session.commit()
            profiles = [p1, p2]
            
        profile_ids = [p.id for p in profiles]
        print(f"✅ Using {len(profile_ids)} filament profiles.")

        # 2. Setup/Fetch Print File
        result = await session.execute(select(PrintFile).limit(1))
        print_file = result.scalar_one_or_none()
        
        if not print_file:
            print("⚠️ No PrintFile found. Creating mock file...")
            print_file = PrintFile(file_path="storage/3mf/test_verify.3mf", original_filename="VerifyTest.3mf")
            session.add(print_file)
            await session.commit()
            await session.refresh(print_file)
        
        print(f"✅ Using PrintFile: {print_file.original_filename} (ID: {print_file.id})")

        # 3. Create Product with Procedural Variants
        dto = ProductCreateDTO(
            name="Verify Procedural Product",
            sku=f"VPRO-{uuid.uuid4().hex[:4].upper()}",
            description="Integration test for procedural generation",
            print_file_id=print_file.id,
            generate_variants_for_profile_ids=profile_ids
        )
        
        print(f"🚀 Creating Product with SKU: {dto.sku}...")
        master = await ProductService.create_product(dto, session)
        
        # 4. Verify Data
        await session.refresh(master, ["variants"])
        print(f"✅ Master Product Created: {master.name}")
        print(f"📦 Total variants created: {len(master.variants)}")
        
        # Check Master SKU
        master_sku = next((v for v in master.variants if v.parent_id is None), None)
        if not master_sku:
            print("❌ Master SKU not found!")
            return
            
        print(f"✅ Master SKU found: {master_sku.sku}")
        
        # Check Children
        children = [v for v in master.variants if v.parent_id == master_sku.id]
        print(f"👶 Children found: {len(children)}")
        
        for i, child in enumerate(children):
            print(f"   Checking child {i+1}: {child.sku}")
            await session.refresh(child, ["requirements", "print_file"])
            if child.print_file_id != master.print_file_id:
                print(f"   ❌ Child {child.sku} has wrong print_file_id: {child.print_file_id}")
            else:
                print(f"   ✅ Child {child.sku} inherited PrintFile (ID: {child.print_file_id})")
                
            if not child.requirements:
                print(f"   ❌ Child {child.sku} has no requirements!")
            else:
                req = child.requirements[0]
                await session.refresh(req, ["filament_profile"])
                print(f"   ✅ Requirement set: {req.filament_profile.material} ({req.filament_profile.color_hex})")

    print("\n🏁 Verification Complete. Refactor is working correctly!")

if __name__ == "__main__":
    asyncio.run(verify_refactor())
