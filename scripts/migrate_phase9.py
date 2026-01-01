
import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    print("[*] Running Migration for Phase 9 (AMS Slot Refactor)...")
    async with engine.begin() as conn:
        # 1. Add new columns if they don't exist
        print("[*] Adding new columns...")
        await conn.execute(text("ALTER TABLE ams_slots ADD COLUMN IF NOT EXISTS slot_id INTEGER"))
        await conn.execute(text("ALTER TABLE ams_slots ADD COLUMN IF NOT EXISTS color_hex VARCHAR"))
        await conn.execute(text("ALTER TABLE ams_slots ADD COLUMN IF NOT EXISTS material VARCHAR"))
        await conn.execute(text("ALTER TABLE ams_slots ADD COLUMN IF NOT EXISTS remaining_percent INTEGER"))
        
        # 2. Sync data from old columns if they exist
        print("[*] Syncing data from legacy columns...")
        try:
            # Check if tray_color exists
            res = await conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='ams_slots' AND column_name='tray_color'"))
            if res.fetchone():
                await conn.execute(text("UPDATE ams_slots SET color_hex = tray_color, material = tray_type"))
                print("[*] Data migrated from legacy columns.")
            
            # Populate slot_id if null
            await conn.execute(text("UPDATE ams_slots SET slot_id = (ams_index * 4) + slot_index WHERE slot_id IS NULL"))
        except Exception as e:
            print(f"[*] Note: Sync might have failed or already done: {e}")

        # 3. Drop old columns if they exist
        print("[*] Dropping legacy columns...")
        await conn.execute(text("ALTER TABLE ams_slots DROP COLUMN IF EXISTS tray_color"))
        await conn.execute(text("ALTER TABLE ams_slots DROP COLUMN IF EXISTS tray_type"))
        
    print("[SUCCESS] Migration for Phase 9 complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
