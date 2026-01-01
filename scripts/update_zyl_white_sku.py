import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.product_sku import ProductSKU

async def update_sku():
    async with async_session_maker() as session:
        stmt = select(ProductSKU).where(ProductSKU.sku == "ZYL-WHITE")
        sku = (await session.exec(stmt)).first()
        if sku:
            sku.print_file_id = 10
            session.add(sku)
            await session.commit()
            print("SKU ZYL-WHITE updated to PrintFile ID 10")
        else:
            print("SKU ZYL-WHITE not found.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(update_sku())
