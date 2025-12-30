import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
from app.core.config import settings
from app.models.product_sku import ProductSKU

async def inspect():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(ProductSKU).where(ProductSKU.name.contains("White"))
        skus = (await session.exec(stmt)).all()
        
        print("--- WHITE SKUs ---")
        for sku in skus:
            print(f"SKU: {sku.name} | Hex: {sku.hex_color} | Requirements: {sku.filament_requirements}")

        stmt = select(ProductSKU).where(ProductSKU.name.contains("Eye"))
        skus = (await session.exec(stmt)).all()
        
        print("--- ALL EYE SKUs ---")
        for sku in skus:
            print(f"SKU: {sku.name} | Hex: {sku.hex_color}")

if __name__ == "__main__":
    asyncio.run(inspect())
