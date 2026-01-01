import asyncio
import sys
import os
from sqlalchemy import text
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)

async def dump_all_skus():
    async with engine.connect() as conn:
        print("\n--- MASTER PRODUCTS ---")
        res_p = await conn.execute(text("SELECT id, name, sku FROM products WHERE name ILIKE '%Zylinder%'"))
        for row in res_p:
            print(f"ID: {row[0]} | Name: {row[1]} | Master SKU: {row[2]}")
            
        print("\n--- CONCRETE SKUS (VARIANTS) ---")
        res_s = await conn.execute(text("""
            SELECT ps.id, ps.sku, ps.name, ps.hex_color, ps.product_id 
            FROM product_skus ps
            JOIN products p ON ps.product_id = p.id
            WHERE p.name ILIKE '%Zylinder%'
        """))
        for row in res_s:
            print(f"ID: {row[0]} | SKU: {row[1]} | Name: {row[2]} | Color: {row[3]} | ProdID: {row[4]}")

if __name__ == "__main__":
    asyncio.run(dump_all_skus())
