import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.core import Printer, Product
from app.models.filament import AmsSlot
from sqlalchemy.orm import selectinload

async def audit_system():
    print("=== SYSTEM AUDIT ===")
    async with async_session_maker() as session:
        # Printers
        printers = (await session.exec(select(Printer).options(selectinload(Printer.ams_slots)))).all()
        for p in printers:
            print(f"PRINTER: {p.serial} | Name: {p.name} | Status: {p.current_status} | Cleared: {p.is_plate_cleared}")
            for slot in p.ams_slots:
                print(f"  - Slot {slot.slot_id}: {slot.material} | {slot.color_hex}")

        # Products
        products = (await session.exec(select(Product))).all()
        for pr in products:
            print(f"PRODUCT: SKU: {pr.sku} | Name: {pr.name} | 3MF: {pr.file_path_3mf} | Filament: {pr.required_filament_type}/{pr.required_filament_color}")

if __name__ == "__main__":
    asyncio.run(audit_system())
