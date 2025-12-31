
import asyncio
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models.core import Printer, Product
from app.models.product_sku import ProductSKU
from app.core.config import settings

# Use the same async URL as the app
engine = create_async_engine(settings.ASYNC_DATABASE_URL)

async def inspect():
    async with AsyncSession(engine) as session:
        print("\n--- Printers in PostgreSQL ---")
        from sqlalchemy.orm import selectinload
        result = await session.execute(select(Printer).options(selectinload(Printer.ams_slots)))
        printers = result.scalars().all()
        for p in printers:
            print(f"Serial: {p.serial}, Name: {p.name}, IP: {p.ip_address}, Status: {p.current_status}")
            print(f"   AMS Slots ({len(p.ams_slots)}):")
            for slot in p.ams_slots:
                 print(f"      AMS {slot.ams_index} Slot {slot.slot_index}: Color={slot.tray_color} Type={slot.tray_type}")
            # Explicitly load AMS slots if not loaded, or use select options
            # But here we just access if available? Or need to change query?
            # It's an async session, lazy loading might fail if not careful.
            # Best to update the query to selectinload


        print("\n--- Products in PostgreSQL ---")
        result = await session.execute(select(Product))
        products = result.scalars().all()
        for p in products:
            print(f"ID: {p.id}, Name: {p.name}, SKU: {p.sku}, Path: {p.file_path_3mf}")

        print("\n--- Product SKUs in PostgreSQL ---")
        result = await session.execute(select(ProductSKU))
        skus = result.scalars().all()
        for s in skus:
            print(f"ID: {s.id}, SKU: {s.sku}, Name: {s.name}, ParentID: {s.parent_id}")

        print("\n--- Jobs in PostgreSQL ---")
        from app.models.core import Job
        result = await session.execute(select(Job))
        jobs = result.scalars().all()
        for j in jobs:
            print(f"ID: {j.id}, Printer: {j.assigned_printer_serial}, Status: {j.status}, Created: {j.created_at}")

if __name__ == "__main__":
    try:
        asyncio.run(inspect())
    except Exception as e:
        print(f"Error: {e}")
