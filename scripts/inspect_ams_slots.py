import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import selectinload
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# Ensure app modules are found
sys.path.append(os.getcwd())

from app.core.config import settings
from app.models.core import Printer
from app.models.filament import AmsSlot

async def inspect_ams():
    print("🔌 Connecting to Database...")
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        stmt = select(Printer).where(Printer.name == "A1 REAL").options(selectinload(Printer.ams_slots))
        printer = (await session.exec(stmt)).first()
        
        if not printer:
            # Fallback
            stmt = select(Printer).limit(1).options(selectinload(Printer.ams_slots))
            printer = (await session.exec(stmt)).first()
            
        print(f"Printer: {printer.name} ({printer.serial})")
        print("--- AMS SLOTS ---")
        
        # Sort by index
        slots = sorted(printer.ams_slots, key=lambda x: x.ams_index * 4 + x.slot_index)
        
        for slot in slots:
            pid = slot.ams_index * 4 + slot.slot_index
            print(f"Slot {pid + 1} (Index {pid}): Color={slot.tray_color} Type={slot.tray_type}")

if __name__ == "__main__":
    asyncio.run(inspect_ams())
