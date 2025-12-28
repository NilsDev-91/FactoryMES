import asyncio
import os
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Product

async def seed_white_eye():
    print("🌱 Seeding 'White Eye' product...")
    
    # Ensure dummy file exists for the test case if not present
    file_path = "storage/3mf/Eye_Master.3mf"
    if not os.path.exists(file_path):
        print(f"⚠️  File {file_path} not found. Creating dummy file for test.")
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w") as f:
            f.write("DUMMY 3MF CONTENT")
    
    async with async_session_maker() as session:
        # Check if product exists
        statement = select(Product).where(Product.sku == "WHITE_EYE")
        result = await session.exec(statement)
        existing_product = result.first()
        
        if existing_product:
            print(f"ℹ️  Product WHITE_EYE already exists. Updating...")
            existing_product.name = "Eye Master Model"
            existing_product.file_path_3mf = file_path
            existing_product.required_filament_type = "PLA"
            existing_product.required_filament_color = "#FFFFFF"
            session.add(existing_product)
        else:
            print(f"✨ Creating new Product WHITE_EYE...")
            new_product = Product(
                name="Eye Master Model",
                sku="WHITE_EYE",
                file_path_3mf=file_path,
                required_filament_type="PLA",
                required_filament_color="#FFFFFF"
            )
            session.add(new_product)
        
        await session.commit()
        print("✅ Product WHITE_EYE seeded successfully.")

if __name__ == "__main__":
    asyncio.run(seed_white_eye())
