
import asyncio
import uuid
import logging
from sqlmodel import select, delete
from sqlalchemy.orm import selectinload

from app.core.database import async_session_maker, engine
from app.models.core import Printer, Job, PrinterStatusEnum, JobStatusEnum, PrinterTypeEnum, OrderStatusEnum
from app.models.order import Order, OrderItem
from app.models.filament import AmsSlot
from app.services.job_dispatcher import job_dispatcher

# Disable excessive logging
logging.getLogger("JobDispatcher").setLevel(logging.INFO)

async def setup_test_data(session):
    print("[*] Setting up mock FMS data...")
    
    # 1. Cleanup
    await session.execute(delete(Job))
    await session.execute(delete(AmsSlot))
    await session.execute(delete(Printer))
    await session.execute(delete(OrderItem))
    await session.execute(delete(Order))
    
    # 1.5 Create Mock Orders
    order1 = Order(id=1, ebay_order_id="EBAY-1", buyer_username="test1", total_price=10.0, currency="USD", status="PENDING")
    order2 = Order(id=2, ebay_order_id="EBAY-2", buyer_username="test2", total_price=20.0, currency="USD", status="PENDING")
    session.add(order1)
    session.add(order2)
    # Flush to ensure IDs are available
    await session.flush()
    
    # 2. Create Printer (A1)
    printer = Printer(
        serial="MOCK-A1-001",
        name="Mock A1",
        type=PrinterTypeEnum.A1,
        current_status=PrinterStatusEnum.IDLE,
        is_plate_cleared=True,
        ip_address="127.0.0.1", # Trigger simulation mode in Commander
        access_code="12345678"
    )
    session.add(printer)
    
    # 3. Add AMS Slots to Printer
    # Slot 0: PLA White
    slot0 = AmsSlot(
        printer_id=printer.serial,
        ams_index=0,
        slot_index=0,
        slot_id=0,
        material="PLA",
        color_hex="#FFFFFF",
        remaining_percent=100
    )
    # Slot 1: PLA Black
    slot1 = AmsSlot(
        printer_id=printer.serial,
        ams_index=0,
        slot_index=1,
        slot_id=1,
        material="PLA",
        color_hex="#000000",
        remaining_percent=50
    )
    session.add(slot0)
    session.add(slot1)
    
    # 4. Create Jobs
    import os
    print(f"[*] Current Working Directory: {os.getcwd()}")
    white_path = os.path.abspath("test_white.3mf")
    red_path = os.path.abspath("test_red.3mf")
    print(f"[*] White Job File Path: {white_path}")
    print(f"[*] Red Job File Path: {red_path}")

    # Job 1: Red PLA (No match)
    job_red = Job(
        order_id=1,
        gcode_path=red_path,
        status=JobStatusEnum.PENDING,
        priority=10,
        filament_requirements=[{"material": "PLA", "hex_color": "#FF0000", "virtual_id": 0}]
    )
    # Job 2: White PLA (Match)
    job_white = Job(
        order_id=2,
        gcode_path=white_path,
        status=JobStatusEnum.PENDING,
        priority=5,
        filament_requirements=[{"material": "PLA", "hex_color": "#FFFFFF", "virtual_id": 0}]
    )
    
    session.add(job_red)
    session.add(job_white)
    
    await session.commit()
    return printer.serial, job_red.id, job_white.id

async def verify_dispatch():
    try:
        async with async_session_maker() as session:
            serial, red_id, white_id = await setup_test_data(session)
            
            print("\n[*] Running Dispatch Cycle...")
            await job_dispatcher.dispatch_next_job(session)
            
            # Verify Results
            session.expire_all()
            
            # Red job should still be PENDING
            job_red = await session.get(Job, red_id)
            print(f"[*] Job Red Status: {job_red.status}")
            assert job_red.status == JobStatusEnum.PENDING
            
            # White job should be PRINTING (since we start it)
            job_white = await session.get(Job, white_id)
            print(f"[*] Job White Status: {job_white.status}")
            print(f"[*] Job White Assigned Printer: {job_white.assigned_printer_serial}")
            
            # Printer should be PRINTING
            printer = await session.get(Printer, serial)
            print(f"[*] Printer Status: {printer.current_status}")
            
            if job_white.status != JobStatusEnum.PRINTING:
                print(f"DEBUG: Job White is NOT PRINTING. Reality: {job_white.status}")
                if hasattr(job_white, 'error_message'):
                    print(f"DEBUG: Job Error Message: {job_white.error_message}")

            assert job_red.status == JobStatusEnum.PENDING
            assert job_white.status == JobStatusEnum.PRINTING
            assert job_white.assigned_printer_serial == serial
            assert printer.current_status == PrinterStatusEnum.PRINTING

            print("\n[SUCCESS] FMS Dispatcher correctly matched White PLA and ignored Red PLA.")
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise e

if __name__ == "__main__":
    asyncio.run(verify_dispatch())
