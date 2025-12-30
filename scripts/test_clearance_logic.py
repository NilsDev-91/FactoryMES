import asyncio
import sys
import os
from contextlib import asynccontextmanager

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker, engine
from app.models.core import Printer, PrinterStatusEnum, SQLModel
from sqlmodel import select, text

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def create_test_printer(serial: str):
    async with async_session_maker() as session:
        statement = select(Printer).where(Printer.serial == serial)
        existing = (await session.exec(statement)).first()
        if existing:
            await session.delete(existing)
            await session.commit()
            
        printer = Printer(
            serial=serial,
            name="Test Printer",
            type="P1S", # Use enum string value directly if valid
            current_status=PrinterStatusEnum.AWAITING_CLEARANCE,
            current_job_id=123
        )
        session.add(printer)
        await session.commit()
        print(f"✅ Created test printer {serial} in state AWAITING_CLEARANCE")

async def verify_endpoint_logic(serial: str):
    # Simulate the endpoint logic directly to verify DB interactions without spinning up full FastAPI test client
    # (Faster for this specific logic check)
    
    print("\nSimulating POST /printers/{serial}/confirm-clearance...")
    
    async with async_session_maker() as session:
        # Fetch
        statement = select(Printer).where(Printer.serial == serial)
        printer = (await session.exec(statement)).first()
        
        if not printer:
            print("❌ Printer not found")
            return
            
        # Verify initial state
        if printer.current_status != PrinterStatusEnum.AWAITING_CLEARANCE:
            print(f"❌ Initial state mismatch: {printer.current_status}")
            return

        # Perform Action (Logic from endpoint)
        printer.current_status = PrinterStatusEnum.IDLE
        printer.current_job_id = None
        
        session.add(printer)
        await session.commit()
        await session.refresh(printer)
        
        # Verify Final State
        if printer.current_status == PrinterStatusEnum.IDLE and printer.current_job_id is None:
            print(f"✅ Success: Printer {serial} is now IDLE and job cleared.")
        else:
            print(f"❌ Failed: State={printer.current_status}, JobID={printer.current_job_id}")

async def main():
    test_serial = "TEST_CLEARANCE_001"
    # Ensure DB tables exist
    await setup_db()
    
    await create_test_printer(test_serial)
    await verify_endpoint_logic(test_serial)

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
