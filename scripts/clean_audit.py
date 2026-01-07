import asyncio
import sys
import os
import logging

# Disable all logging including SQLAlchemy
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Printer, Product, Job
from app.models.product_sku import ProductSKU
from sqlalchemy.orm import selectinload

async def clean_audit():
    print("=== CLEAN SYSTEM AUDIT ===")
    async with async_session_maker() as session:
        # Printers
        printers = (await session.exec(select(Printer).options(selectinload(Printer.ams_slots)))).all()
        print("\n--- PRINTERS ---")
        for p in printers:
            print(f"[{p.serial}] Name: {p.name} | Status: {p.current_status} | Cleared: {p.is_plate_cleared}")
            for s in p.ams_slots:
                print(f"  Slot {s.slot_id}: {s.material} {s.color_hex}")

        # Products & SKUs
        print("\n--- PRODUCTS & SKUS ---")
        stmt_sku = select(ProductSKU).options(selectinload(ProductSKU.product))
        skus = (await session.exec(stmt_sku)).all()
        for s in skus:
            print(f"SKU: {s.sku} | Product: {s.product.sku if s.product else 'N/A'} | Color: {s.hex_color} | File: {s.product.file_path_3mf if s.product else 'N/A'}")

        prods = (await session.exec(select(Product))).all()
        for pr in prods:
            print(f"PROD: {pr.sku} | ID: {pr.id} | Name: {pr.name} | 3MF: {pr.file_path_3mf}")

        # Jobs
        print("\n--- RECENT JOBS ---")
        jobs = (await session.exec(select(Job).order_by(Job.id.desc()).limit(5))).all()
        for j in jobs:
            print(f"Job {j.id} | Status: {j.status} | Printer: {j.assigned_printer_serial} | Req: {j.filament_requirements}")

if __name__ == "__main__":
    asyncio.run(clean_audit())
