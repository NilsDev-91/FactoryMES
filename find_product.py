
import asyncio
import sys
from database import async_session_maker
from models import Product
from sqlmodel import select

async def find_red_tooth():
    async with async_session_maker() as session:
        # Search for anything looking like red_tooth
        print("Searching for product...")
        result = await session.execute(select(Product))
        products = result.scalars().all()
        
        found = False
        for p in products:
            if "red" in p.sku.lower() or "tooth" in p.sku.lower():
                print(f"FOUND MATCH: SKU='{p.sku}' Name='{p.name}'")
                found = True
        
        if not found:
            print("No matching product found for 'red_tooth'.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(find_red_tooth())
