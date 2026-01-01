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
        print("\n--- PRODUCTS ---")
        res_p = await conn.execute(text("SELECT id, name, sku FROM products WHERE name ILIKE '%Zylinder%'"))
        prods = res_p.all()
        for p in prods:
            print(f"ProdID: {p[0]} | Name: {p[1]} | Master SKU: {p[2]}")
            
        print("\n--- VISIBLE MASTER SKUS ---")
        res_m = await conn.execute(text("""
            SELECT id, sku, name, product_id 
            FROM product_skus 
            WHERE parent_id IS NULL AND is_catalog_visible = TRUE AND name ILIKE '%Zylinder%'
        """))
        for m in res_m:
            print(f"SKU ID: {m[0]} | SKU: {m[1]} | Name: {m[2]} | ProdID: {m[3]}")
            
            # Count children
            res_c = await conn.execute(text(f"SELECT COUNT(*) FROM product_skus WHERE parent_id = {m[0]}"))
            count = res_c.scalar()
            print(f"   -> Children (Variants): {count}")

if __name__ == "__main__":
    asyncio.run(audit())
