import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import engine
from app.models.core import Printer

async def check_temps():
    async with AsyncSession(engine) as session:
        serial = "03919C461802608"
        print(f"[*] Checking Temps for {serial}...")
        statement = select(Printer).where(Printer.serial == serial)
        result = await session.execute(statement)
        p = result.scalars().first()
        
        if not p:
            print("[-] Printer not found in DB.")
        else:
            print(f"Nozzle: {p.current_temp_nozzle}, Bed: {p.current_temp_bed}")
            print(f"Status: {p.current_status}")

if __name__ == "__main__":
    asyncio.run(check_temps())
