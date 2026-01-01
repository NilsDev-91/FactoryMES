import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.orm import selectinload

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.product_sku import ProductSKU
from app.models.print_file import PrintFile

async def dump_details():
    async with async_session_maker() as session:
        stmt = select(ProductSKU).where(ProductSKU.sku == "ZYL-WHITE").options(selectinload(ProductSKU.print_file))
        sku = (await session.exec(stmt)).first()
        if sku:
            print(f"SKU: {sku.sku}")
            print(f"Color: {sku.hex_color}")
            if sku.print_file:
                print(f"PrintFile ID: {sku.print_file.id}")
                print(f"Original Filename: {sku.print_file.original_filename}")
                print(f"File Path: {sku.print_file.file_path}")
            else:
                print("PrintFile: NONE")
        else:
            print("SKU ZYL-WHITE not found.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(dump_details())
