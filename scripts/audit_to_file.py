import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Printer, Product, Job
from app.models.product_sku import ProductSKU
from app.models.filament import AmsSlot
from sqlalchemy.orm import selectinload

async def audit_to_file():
    content = ["--- SYSTEM AUDIT ---"]
    async with async_session_maker() as session:
        # Printers
        printers = (await session.exec(select(Printer).options(selectinload(Printer.ams_slots)))).all()
        content.append("\n[PRINTERS]")
        for p in printers:
            content.append(f"SERIAL: {p.serial} | NAME: {p.name} | STATUS: {p.current_status}")
            for s in p.ams_slots:
                content.append(f"  SLOT {s.slot_id}: {s.material} {s.color_hex}")

        # Products
        content.append("\n[PRODUCTS]")
        products = (await session.exec(select(Product))).all()
        for pr in products:
            content.append(f"ID: {pr.id} | SKU: {pr.sku} | NAME: {pr.name} | 3MF: {pr.file_path_3mf}")

        # SKUs
        content.append("\n[SKUS]")
        skus = (await session.exec(select(ProductSKU).options(selectinload(ProductSKU.product)))).all()
        for s in skus:
            content.append(f"SKU: {s.sku} | Parent: {s.product.sku if s.product else 'N/A'} | Color: {s.hex_color}")

    with open("audit_final.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(content))
    print("Audit written to audit_final.txt")

if __name__ == "__main__":
    asyncio.run(audit_to_file())
