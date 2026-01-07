import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.product_sku import ProductSKU

async def check_skus():
    async with async_session_maker() as session:
        stmt = select(ProductSKU)
        result = await session.exec(stmt)
        skus = result.all()
        
        if not skus:
            print("📭 No SKUs found in the database.")
        else:
            print(f"📋 Found {len(skus)} SKUs:")
            for s in skus:
                print(f"   - {s.sku} ({s.name}) | ID: {s.id} | Parent: {s.parent_id}")

if __name__ == "__main__":
    asyncio.run(check_skus())
