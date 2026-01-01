
import asyncio
from app.core.database import async_session_maker
from app.models.core import Product
from sqlalchemy import select

async def fix():
    async with async_session_maker() as session:
        stmt = select(Product).where(Product.name == "Zylinder")
        product = (await session.execute(stmt)).scalars().first()
        if product:
            product.is_continuous_printing = True
            product.part_height_mm = 120.0 # Standard Zylinder height
            session.add(product)
            await session.commit()
            print("✅ Product 'Zylinder' updated with safe defaults.")
        else:
            print("❌ Product 'Zylinder' not found.")

if __name__ == "__main__":
    asyncio.run(fix())
