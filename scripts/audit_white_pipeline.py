import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.orm import selectinload

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Printer, Product, Job
from app.models.product_sku import ProductSKU
from app.models.filament import AmsSlot

REAL_PRINTER_SERIAL = "03919C461802608"

async def audit_white_pipeline():
    with open("audit_result.txt", "w", encoding="utf-8") as f:
        f.write("--- PIPELINE AUDIT: ZYLINDER WHITE ---\n")
        async with async_session_maker() as session:
            # 1. Product Audit
            f.write("\n[1] Checking Product 'Zylinder'...\n")
            stmt = select(Product).where(Product.name == "Zylinder").options(selectinload(Product.variants))
            zylinder = (await session.exec(stmt)).first()
            if not zylinder:
                f.write("❌ Product 'Zylinder' not found!\n")
            else:
                f.write(f"✅ Product 'Zylinder' found (ID: {zylinder.id})\n")
                found_white = False
                for v in zylinder.variants:
                    f.write(f"   - Variant: {v.name} (SKU: {v.sku}, Color: {v.hex_color})\n")
                    if "white" in v.name.lower() or "weiss" in v.name.lower():
                        found_white = True
                if not found_white:
                    f.write("❌ 'Zylinder White' variant missing in variants!\n")
            
            # 2. SKU Audit
            f.write("\n[2] Checking SKU 'ZYL-WHITE'...\n")
            sku_stmt = select(ProductSKU).where(ProductSKU.sku.like("%WHITE%")).options(selectinload(ProductSKU.print_file))
            skus = (await session.exec(sku_stmt)).all()
            if not skus:
                f.write("❌ No SKU matching '%WHITE%' found!\n")
            for s in skus:
                f.write(f"✅ SKU found: {s.sku} (Color: {s.hex_color}, File: {s.print_file.file_path if s.print_file else 'MISSING'})\n")

            # 3. Printer Audit
            f.write(f"\n[3] Checking Printer {REAL_PRINTER_SERIAL}...\n")
            printer = await session.get(Printer, REAL_PRINTER_SERIAL)
            if not printer:
                f.write(f"❌ Printer {REAL_PRINTER_SERIAL} not found in DB!\n")
            else:
                f.write(f"✅ Printer: {printer.name} (Status: {printer.current_status})\n")
                slot_stmt = select(AmsSlot).where(AmsSlot.printer_id == REAL_PRINTER_SERIAL)
                slots = (await session.exec(slot_stmt)).all()
                if not slots:
                    f.write("❌ No AMS slots found for this printer!\n")
                for slot in slots:
                    f.write(f"   - Slot {slot.slot_id} (AMS {slot.ams_index}, Index {slot.slot_index}): {slot.material} ({slot.color_hex})\n")

    print("Audit finished. Results in audit_result.txt")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(audit_white_pipeline())
