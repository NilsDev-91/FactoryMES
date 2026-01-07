import asyncio
import sys
import os
import logging

# Kill all logging
logging.basicConfig(level=logging.CRITICAL)
for name in logging.root.manager.loggerDict:
    logging.getLogger(name).setLevel(logging.CRITICAL)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Printer, Product, Job
from app.models.product_sku import ProductSKU
from app.models.filament import AmsSlot
from sqlalchemy.orm import selectinload

async def final_audit():
    print("--- DEFINITIVE SYSTEM AUDIT ---")
    async with async_session_maker() as session:
        # Printers
        printers = (await session.exec(select(Printer).options(selectinload(Printer.ams_slots)))).all()
        print("\n[PRINTERS]")
        for p in printers:
            print(f"SERIAL: {p.serial} | NAME: {p.name} | STATUS: {p.current_status}")
            for s in p.ams_slots:
                print(f"  SLOT {s.slot_id}: {s.material} {s.color_hex}")

        # Products
        print("\n[PRODUCTS]")
        products = (await session.exec(select(Product))).all()
        for pr in products:
            print(f"ID: {pr.id} | SKU: {pr.sku} | NAME: {pr.name} | 3MF: {pr.file_path_3mf}")

        # SKUs
        print("\n[SKUS]")
        skus = (await session.exec(select(ProductSKU).options(selectinload(ProductSKU.product)))).all()
        for s in skus:
            print(f"SKU: {s.sku} | Parent: {s.product.sku if s.product else 'N/A'} | Color: {s.hex_color}")

        # Jobs
        print("\n[LATEST JOBS]")
        jobs = (await session.exec(select(Job).order_by(Job.id.desc()).limit(10))).all()
        for j in jobs:
            print(f"JOB {j.id} | ORDER: {j.order_id} | STATUS: {j.status} | PRINTER: {j.assigned_printer_serial} | REQ: {j.filament_requirements}")

if __name__ == "__main__":
    asyncio.run(final_audit())
