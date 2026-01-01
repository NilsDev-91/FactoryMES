import asyncio
import os
import sys
from sqlmodel import select
import uuid

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker
from app.models.core import Product
from app.models.product_sku import ProductSKU
from app.models.print_file import PrintFile

async def seed_skus():
    async with async_session_maker() as session:
        # 1. Get Product
        stmt = select(Product).where(Product.name == "Zylinder")
        product = (await session.execute(stmt)).scalars().first()
        
        if not product:
            print("❌ Product 'Zylinder' not found.")
            return

        # 2. Ensure we have a PrintFile
        # Check if one exists or create a placeholder
        stmt = select(PrintFile).where(PrintFile.original_filename == "zylinder_v1.3mf")
        pfile = (await session.execute(stmt)).scalars().first()
        
        if not pfile:
            # Create a mock physical file if it doesn't exist
            store_dir = Path("storage/3mf")
            store_dir.mkdir(parents=True, exist_ok=True)
            mock_path = store_dir / "zylinder_placeholder.3mf"
            if not mock_path.exists():
                with open(mock_path, "w") as f:
                    f.write("MOCK 3MF CONTENT")
            
            pfile = PrintFile(
                file_path=str(mock_path),
                original_filename="zylinder_v1.3mf"
            )
            session.add(pfile)
            await session.flush()
            print(f"✅ Created mock PrintFile: {pfile.file_path}")

        # 3. Create SKUs
        variants = [
            ("Zylinder Rot", "ZYL-RED", "#FF0000"),
            ("Zylinder Blau", "ZYL-BLUE", "#0000FF"),
            ("Zylinder Weiß", "ZYL-WHITE", "#FFFFFF")
        ]
        
        for name, sku_code, color in variants:
            # Check if SKU exists
            stmt = select(ProductSKU).where(ProductSKU.sku == sku_code)
            existing = (await session.execute(stmt)).scalars().first()
            
            if not existing:
                sku = ProductSKU(
                    sku=sku_code,
                    name=name,
                    product_id=product.id,
                    hex_color=color,
                    print_file_id=pfile.id
                )
                session.add(sku)
                print(f"✅ Created SKU: {name} ({sku_code})")
            else:
                print(f"🟡 SKU {sku_code} already exists.")

        await session.commit()
        print("\n✨ Seeding Complete.")

if __name__ == "__main__":
    from pathlib import Path
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(seed_skus())
