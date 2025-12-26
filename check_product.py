
import asyncio
import sys
import os
from database import async_session_maker
from models import Product
from sqlmodel import select

async def check_product():
    async with async_session_maker() as session:
        sku = "white_eye"
        print(f"Searching for product SKU: {sku}")
        
        result = await session.execute(select(Product).where(Product.sku == sku))
        product = result.scalars().first()
        
        if product:
            print(f"FOUND: ID {product.id}")
            print(f"Name: {product.name}")
            print(f"Path: {product.file_path_3mf}")
            
            # Verify file
            abs_path = os.path.abspath(product.file_path_3mf)
            if os.path.exists(product.file_path_3mf):
                print(f"FILE STATUS: Exists at {abs_path}")
            else:
                 print(f"FILE STATUS: MISSING at {abs_path}")
        else:
            print("NOT FOUND in Database.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check_product())
