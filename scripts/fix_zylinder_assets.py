import asyncio
import os
import sys
from sqlmodel import select, col

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.product_sku import ProductSKU
from app.models.print_file import PrintFile

async def fix_zylinder_assets():
    async with async_session_maker() as session:
        # We know ID 10 is the good master file
        master_file_id = 10
        
        # Check if ID 10 exists and is valid
        master_file = await session.get(PrintFile, master_file_id)
        if not master_file:
             print(f"ERROR: Parent PrintFile {master_file_id} not found!")
             return
        
        print(f"Master File: {master_file.file_path}")

        # Find all Zylinder SKUs
        stmt = select(ProductSKU).where(col(ProductSKU.sku).startswith("ZYL-"))
        skus = (await session.exec(stmt)).all()
        
        for sku in skus:
            print(f"Checking SKU: {sku.sku} (Current File ID: {sku.print_file_id})")
            
            # If it's the placeholder (ID 12) or None, update to ID 10
            if sku.print_file_id == 12 or sku.print_file_id is None:
                print(f"   ⚠️  Fixing {sku.sku}: Mapping to ID {master_file_id}")
                sku.print_file_id = master_file_id
                session.add(sku)
            else:
                print(f"   ✅ {sku.sku} looks okay.")

        await session.commit()
        print("\n✨ Zylinder SKU assets synchronized to Master File.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(fix_zylinder_assets())
