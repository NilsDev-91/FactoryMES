
import asyncio
from sqlalchemy import text
from app.core.database import engine
from app.models.filament import AmsSlot
from sqlmodel import SQLModel

async def reset_ams_slots():
    print("[*] Hard Resetting ams_slots table...")
    async with engine.begin() as conn:
        # 1. Drop table
        await conn.execute(text("DROP TABLE IF EXISTS ams_slots CASCADE"))
        print("[*] Table dropped.")
        
    # 2. Recreate via SQLModel
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all, tables=[AmsSlot.__table__])
        print("[*] Table recreated.")

if __name__ == "__main__":
    asyncio.run(reset_ams_slots())
