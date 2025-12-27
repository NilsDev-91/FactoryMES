
import asyncio
import sys
from database import async_session_maker
from models import Product
from sqlmodel import select

async def check():
    async with async_session_maker() as session:
        for sku in ["red_tooth", "white_eye"]:
            res = await session.execute(select(Product).where(Product.sku == sku))
            p = res.scalars().first()
            if p:
                print(f"FOUND {sku} (ID: {p.id})")
            else:
                print(f"MISSING {sku}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(check())
