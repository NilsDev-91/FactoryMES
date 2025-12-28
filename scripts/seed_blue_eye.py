import asyncio
import os
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Product

async def seed_blue_eye():
    print("🔵 Seeding 'Blue Eye' product...")
    
    # Confirm Master File exists
    file_path = "storage/3mf/Eye_Master.3mf"
    if not os.path.exists(file_path):
        print(f"❌ Error: Master File {file_path} NOT FOUND. Please run seed_white_eye.py first.")
        return
    
    print(f"✅ Master File found: {file_path}")

    async with async_session_maker() as session:
        # Check if product exists
        statement = select(Product).where(Product.sku == "BLUE_EYE")
        result = await session.exec(statement)
        existing_product = result.first()
        
        # Requirements: PLA, Blue (#0000FF), Virtual ID 0
        fil_reqs = [{"material": "PLA", "hex_color": "#0000FF", "virtual_slot_id": 0}]

        if existing_product:
            print(f"ℹ️  Product BLUE_EYE already exists. Updating...")
            existing_product.name = "Eye Model (Blue Variant)"
            existing_product.file_path_3mf = file_path
            existing_product.filament_requirements = fil_reqs
            session.add(existing_product)
        else:
            print(f"✨ Creating new Product BLUE_EYE...")
            new_product = Product(
                name="Eye Model (Blue Variant)",
                sku="BLUE_EYE",
                file_path_3mf=file_path,
                # Using new JSON field for requirements
                filament_requirements=fil_reqs 
            )
            session.add(new_product)
        
        await session.commit()
        print("✅ Created BLUE_EYE pointing to generic Master File.")

if __name__ == "__main__":
    asyncio.run(seed_blue_eye())
