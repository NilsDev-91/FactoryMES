import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.orm import selectinload

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Product
from app.models.product_sku import ProductSKU
from app.models.print_file import PrintFile

async def audit_red_sku():
    output = []
    async with async_session_maker() as session:
        # Find Zylinder Product
        stmt = select(Product).where(Product.name == "Zylinder").options(selectinload(Product.variants))
        product = (await session.exec(stmt)).first()
        
        if not product:
            output.append("Product 'Zylinder' not found.")
        else:
            output.append(f"Product: {product.name} (ID: {product.id})")
            output.append(f"Parent PrintFile ID: {product.print_file_id}")
            if product.print_file_id:
                pf = await session.get(PrintFile, product.print_file_id)
                output.append(f"Parent File Path: {pf.file_path if pf else 'MISSING'}")

            for v in product.variants:
                if v.sku == "ZYL-RED":
                    output.append(f"\nFound Variant: {v.name} (SKU: {v.sku})")
                    output.append(f"Variant PrintFile ID: {v.print_file_id}")
                    if v.print_file_id:
                        pf = await session.get(PrintFile, v.print_file_id)
                        output.append(f"Variant File Path: {pf.file_path if pf else 'MISSING'}")
                    else:
                        output.append("Variant has NO print_file_id (falls back to parent)")

    with open("red_audit_result.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(output))

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(audit_red_sku())
