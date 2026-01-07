import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from app.core.database import async_session_maker
from app.models.product_sku import ProductSKU
from app.models.core import Product

async def list_all_skus():
    async with async_session_maker() as session:
        # List ProductSKU
        stmt_sku = select(ProductSKU)
        skus = (await session.exec(stmt_sku)).all()
        print(f"All ProductSKUs in DB: {[s.sku for s in skus]}")
        
        # List Products
        stmt_prod = select(Product)
        prods = (await session.exec(stmt_prod)).all()
        print(f"All Products in DB: {[p.sku for p in prods]}")

if __name__ == "__main__":
    asyncio.run(list_all_skus())
