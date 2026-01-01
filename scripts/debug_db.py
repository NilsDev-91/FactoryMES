
import asyncio
import os
import sys

sys.path.append(os.getcwd())

from app.core.database import async_session_maker
from app.models.core import Printer, Job, Product
from app.models.product_sku import ProductSKU
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check():
    print("Checking DB State...")
    async with async_session_maker() as session:
        # Check Printer
        print("\n--- PRINTERS ---")
        result = await session.execute(select(Printer).options(selectinload(Printer.ams_slots)))
        printers = result.scalars().all()
        for printer in printers:
            print(f"Printer {printer.serial} ({printer.name})")
            print(f"   Status: {printer.current_status}")
            print(f"   AMS Slots: {len(printer.ams_slots)}")
            for slot in printer.ams_slots:
                print(f"     - Slot {slot.ams_index}-{slot.slot_index}: {slot.color_hex} ({slot.material})")

        # Check Jobs
        print("\n--- JOBS ---")
        result = await session.execute(select(Job))
        jobs = result.scalars().all()
        for j in jobs:
            print(f"Job {j.id}: Status={j.status}")
            print(f"   Assigned: {j.assigned_printer_serial}")
            print(f"   Error: {j.error_message}")
            print(f"   Reqs: {j.filament_requirements}")

        # Check Products & SKUs
        print("\n--- PRODUCTS & SKUs ---")
        result = await session.execute(select(Product).options(selectinload(Product.variants)))
        products = result.scalars().all()
        for p in products:
            print(f"Product {p.id}: {p.name} (SKU={p.sku})")
            print(f"   Variants: {len(p.variants)}")
            for v in p.variants:
                print(f"     - Variant {v.id}: {v.name} ({v.sku}) | Color: {v.hex_color}")

if __name__ == "__main__":
    asyncio.run(check())
