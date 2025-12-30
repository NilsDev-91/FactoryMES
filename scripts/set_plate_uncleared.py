import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

from app.models.core import Printer
from app.core.config import settings
# from app.core.database import DATABASE_URL

async def set_plate_uncleared():
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        statement = select(Printer)
        result = await session.exec(statement)
        printers = result.all()
        
        if not printers:
            print("No printers found.")
            return

        for printer in printers:
            print(f"Updating printer {printer.name} ({printer.serial}) -> is_plate_cleared = False")
            printer.is_plate_cleared = False
            session.add(printer)
        
        await session.commit()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(set_plate_uncleared())
