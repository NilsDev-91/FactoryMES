
import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import engine
from app.models.core import Printer

async def check_printer():
    async with AsyncSession(engine) as session:
        statement = select(Printer).where(Printer.serial == "sim_printer_01")
        result = await session.execute(statement)
        printer = result.scalar_one_or_none()
        if printer:
            print(f"Printer: {printer.serial}, Status: {printer.current_status}, Last Error: {printer.last_error_code}")
        else:
            print("Printer not found")

if __name__ == "__main__":
    asyncio.run(check_printer())
