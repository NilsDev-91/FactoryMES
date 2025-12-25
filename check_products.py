import asyncio
from database import get_session
from models import Product
from sqlmodel import select

async def main():
    async for session in get_session():
        result = await session.execute(select(Product))
        products = result.scalars().all()
        print(f"Products found: {len(products)}")
        for p in products:
            print(f"- ID: {p.id}, Name: {p.name}, SKU: {p.sku}")
        break # get_session is a generator, we just need one session

if __name__ == "__main__":
    asyncio.run(main())
