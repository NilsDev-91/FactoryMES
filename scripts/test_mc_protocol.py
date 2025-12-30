import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import async_session_maker, engine
from app.models.core import Printer, PrinterStatusEnum, Job, JobStatusEnum, SQLModel
from app.services.printer.mqtt_worker import PrinterMqttWorker
from app.services.production.dispatcher import ProductionDispatcher
from sqlmodel import select, text

async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

async def test_manual_clearance_protocol():
    print("Testing Manual Clearance Protocol...")
    
    # 1. Setup Data: Printer in IDLE (initially), Job PENDING
    test_serial = "MC_TEST_001"
    async with async_session_maker() as session:
        # cleanup
        await session.exec(text(f"DELETE FROM printers WHERE serial = '{test_serial}'"))
        await session.commit()
        
        printer = Printer(serial=test_serial, name="MC Test", type="P1S", current_status=PrinterStatusEnum.PRINTING) # Start as printing
        session.add(printer)
        await session.commit()

    # 2. Simulate MQTT "FINISH" -> AWAITING_CLEARANCE
    print("Simulating MQTT FINISH message...")
    worker = PrinterMqttWorker()
    message = {"print": {"gcode_state": "FINISH"}} # Simulating Bambu payload
    await worker._handle_message(test_serial, message)
    
    # Verify DB State
    async with async_session_maker() as session:
        printer = await session.get(Printer, test_serial)
        if printer.current_status != PrinterStatusEnum.AWAITING_CLEARANCE:
            print(f"❌ MQTT Worker Failed: Status is {printer.current_status}, expected AWAITING_CLEARANCE")
            return
        else:
            print("✅ MQTT Worker Success: Printer set to AWAITING_CLEARANCE")

    # 3. Simulate Dispatcher Block
    print("Simulating Dispatcher Cycle...")
    dispatcher = ProductionDispatcher()
    
    # We will wrap run_cycle to timeout because it should sleep(5)
    # Actually, we can check logs or just ensure it returns without crashing and didn't pick up jobs?
    # Better: Ensure it returns and we can time it?
    # Or just run it and trust the log output if we were watching logs. 
    # For script, checking it doesn't crash is basic.
    # To check logic: We can verify it returns (it has a return).
    
    start_time = asyncio.get_event_loop().time()
    task = asyncio.create_task(dispatcher.run_cycle())
    
    # It should sleep 5s. If we cancel it after 6s, it should be done?
    # Wait for it.
    await task
    end_time = asyncio.get_event_loop().time()
    
    duration = end_time - start_time
    print(f"Dispatcher cycle duration: {duration:.2f}s")
    
    if duration >= 5.0:
        print("✅ Dispatcher waited for manual clearance (duration >= 5s)")
    else:
        # Note: If it didn't find jobs, it returns immediately. 
        # But we want it to hit the "block" logic because we have 0 IDLE and 1 AWAITING.
        # So correct behavior is duration >= 5s.
        print("❌ Dispatcher did NOT wait (duration < 5s). Check logic.")

async def main():
    await setup_db()
    await test_manual_clearance_protocol()

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
