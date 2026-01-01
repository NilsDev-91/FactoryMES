import asyncio
import sys
import os
from sqlalchemy import text
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)

async def audit():
    async with engine.connect() as conn:
        print("\n--- PRODUCTS MATCHING 'Zylinder' ---")
        res = await conn.execute(text("SELECT id, name, sku FROM products WHERE name ILIKE '%Zylinder%'"))
        for row in res:
            print(f"Product ID: {row[0]} | Name: {row[1]} | Master SKU: {row[2]}")
            
        print("\n--- SKUS POINTING TO THESE PRODUCTS ---")
        res = await conn.execute(text("""
            SELECT ps.id, ps.name, ps.sku, ps.product_id, ps.parent_id, ps.is_catalog_visible 
            FROM product_skus ps
            JOIN products p ON ps.product_id = p.id
            WHERE p.name ILIKE '%Zylinder%'
            ORDER BY ps.product_id, ps.parent_id NULLS FIRST
        """))
        for row in res:
            vis = "VISIBLE" if row[5] else "HIDDEN"
            parent = row[4] if row[4] else "ROOT"
            print(f"SKU ID: {row[0]:<3} | ProductID: {row[3]:<3} | ParentID: {parent:<4} | {vis:<8} | SKU: {row[2]:<30} | Name: {row[1]}")

if __name__ == "__main__":
    asyncio.run(audit())
