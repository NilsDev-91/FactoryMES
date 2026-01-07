import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Product

async def check_product_details():
    async with async_session_maker() as session:
        stmt = select(Product)
        prods = (await session.exec(stmt)).all()
        for p in prods:
            print(f"SKU: {p.sku} | Name: {p.name} | GCode: {p.file_path_3mf}")

if __name__ == "__main__":
    asyncio.run(check_product_details())
