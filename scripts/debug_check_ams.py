import asyncio
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from app.core.database import engine
from app.models.filament import AmsSlot

async def check_ams():
    async with AsyncSession(engine) as session:
        serial = "03919C461802608"
        print(f"[*] Checking AMS slots for {serial}...")
        statement = select(AmsSlot).where(AmsSlot.printer_id == serial)
        result = await session.execute(statement)
        slots = result.scalars().all()
        
        if not slots:
            print("[-] No AMS slots found in DB.")
        else:
            for s in slots:
                print(f"Slot {s.slot_index}: Material={s.material}, Color={s.color_hex}")

if __name__ == "__main__":
    asyncio.run(check_ams())
