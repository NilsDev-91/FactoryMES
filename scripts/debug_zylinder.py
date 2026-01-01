import asyncio
from app.core.database import async_session_maker
from app.models.core import Product
from sqlalchemy import select

async def check():
    async with async_session_maker() as s:
        r = await s.execute(select(Product).where(Product.name == 'Zylinder'))
        p = r.scalars().first()
        if p:
            print(f"Product: {p.name}, Continuous: {p.is_continuous_printing}, Height: {p.part_height_mm}")
        else:
            print("Product 'Zylinder' not found.")

if __name__ == "__main__":
    asyncio.run(check())
