import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Printer, Product
from app.models.product_sku import ProductSKU
from sqlalchemy.orm import selectinload

async def target_audit():
    print("=== TARGETED AUDIT ===")
    async with async_session_maker() as session:
        # Check for A1 REAL
        stmt = select(Printer)
        printers = (await session.exec(stmt)).all()
        for p in printers:
            print(f"P: {p.serial} | {p.name}")

        # Check for ProductSKUs (The real ones)
        stmt_sku = select(ProductSKU).options(selectinload(ProductSKU.product))
        skus = (await session.exec(stmt_sku)).all()
        for s in skus:
            print(f"SKU: {s.sku} | Hex: {s.hex_color} | Product: {s.product.sku if s.product else 'N/A'}")

        # Check for Products
        stmt_prod = select(Product)
        prods = (await session.exec(stmt_prod)).all()
        for pr in prods:
            print(f"PROD: {pr.sku} | ID: {pr.id} | 3MF: {pr.file_path_3mf}")

if __name__ == "__main__":
    asyncio.run(target_audit())
