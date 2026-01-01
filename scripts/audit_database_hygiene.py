import asyncio
import sys
import os
from sqlalchemy import text
from app.core.config import settings
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

engine = create_async_engine(settings.ASYNC_DATABASE_URL, echo=False)

async def audit_products():
    async with engine.connect() as conn:
        print("\n=== [PRODUCTS TABLE] ===")
        res_p = await conn.execute(text("SELECT id, name, sku, created_at FROM products ORDER BY id"))
        for row in res_p:
            print(f"ID: {row[0]:<3} | Name: {row[1]:<20} | Master SKU: {row[2]:<20} | Created: {row[3]}")
            
        print("\n=== [PRODUCT_SKUS TABLE] ===")
        res_s = await conn.execute(text("""
            SELECT id, sku, name, parent_id, product_id, hex_color, is_catalog_visible 
            FROM product_skus 
            ORDER BY id
        """))
        for row in res_s:
            parent = row[3] if row[3] else "ROOT"
            visible = "VIS" if row[6] else "HID"
            print(f"ID: {row[0]:<3} | PID: {parent:<4} | ProdID: {row[4]:<3} | {visible} | SKU: {row[1]:<30} | Name: {row[2]}")

        print("\n=== [ORPHAN CHECK] ===")
        res_o = await conn.execute(text("""
            SELECT id, sku FROM product_skus 
            WHERE product_id IS NOT NULL AND product_id NOT IN (SELECT id FROM products)
        """))
        orphans = res_o.all()
        if orphans:
            for o in orphans:
                print(f"🚨 ORPHAN SKU: ID {o[0]} (SKU {o[1]}) points to non-existent Product!")
        else:
            print("✅ No orphaned SKUs found (pointing to missing products).")

        res_np = await conn.execute(text("""
            SELECT id, sku FROM products 
            WHERE id NOT IN (SELECT product_id FROM product_skus WHERE parent_id IS NULL)
        """))
        zombie_prods = res_np.all()
        if zombie_prods:
            for z in zombie_prods:
                print(f"🧟 ZOMBIE PRODUCT: ID {z[0]} (SKU {z[1]}) has no Master SKU!")
        else:
            print("✅ No zombie products found (all products have master SKUs).")

if __name__ == "__main__":
    asyncio.run(audit_products())
