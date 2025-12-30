
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
        result = await session.execute(select(Printer))
        printers = result.scalars().all()
        for p in printers:
            print(f"Serial: {p.serial}, Name: {p.name}, IP: {p.ip_address}, Status: {p.current_status}")

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
