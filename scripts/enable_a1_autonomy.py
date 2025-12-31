import asyncio
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Printer

async def enable_a1_autonomy():
    target_serial = '03919C461802608'
    
    print(f"Targeting printer with serial: {target_serial}")
    
    async with async_session_maker() as session:
        statement = select(Printer).where(Printer.serial == target_serial)
        result = await session.exec(statement)
        printer = result.one_or_none()
        
        if not printer:
            print(f"Error: Printer with serial {target_serial} not found in database.")
            return

        print(f"Found printer: {printer.name}")
        print(f"Current Config: model={printer.hardware_model}, auto_eject={printer.can_auto_eject}")
        
        # Apply updates
        printer.hardware_model = "A1"
        printer.can_auto_eject = True
        
        session.add(printer)
        await session.commit()
        
        # Verify
        await session.refresh(printer)
        print("---")
        print("Success! Configuration updated.")
        print(f"New Config: model={printer.hardware_model}, auto_eject={printer.can_auto_eject}")

if __name__ == "__main__":
    asyncio.run(enable_a1_autonomy())
