
import asyncio
import logging
import sys
import os
from unittest.mock import MagicMock

# Ensure we can import app
sys.path.append(os.getcwd())

from sqlmodel import select, delete
from app.core.database import async_session_maker, engine
from app.models.core import Printer, Job, Product, PrinterStatusEnum, JobStatusEnum, SQLModel
from app.models.filament import AmsSlot
from app.models.order import Order
from app.services.production.dispatcher import ProductionDispatcher
from app.services.logic.filament_manager import FilamentManager
from app.services.printer.commander import PrinterCommander

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SystemIntegrityCheck")

# Mock Commander to avoid Network IO
class MockPrinterCommander(PrinterCommander):
    async def upload_file(self, ip, access_code, local_path, target_filename):
        logger.info(f"MOCK UPLOAD: {local_path} -> {ip}:{target_filename}")
        return

    async def start_print_job(self, ip, serial, access_code, filename, ams_mapping):
        logger.info(f"MOCK START PRINT: {serial} mapping={ams_mapping}")
        return

async def run_check():
    logger.info("🛠️  Starting System Integrity Check...")

    # 1. Database Setup
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    async with async_session_maker() as session:
        # 2. Clean Previous Test Data
        logger.info("🧹 Cleaning old test data...")
        await session.exec(delete(Job).where(Job.gcode_path == "TEST-GCODE-PATH.gcode"))
        await session.exec(delete(Product).where(Product.sku == "TEST-SKU-001"))
        await session.exec(delete(AmsSlot).where(AmsSlot.printer_id == "TEST-PRINTER-01"))
        await session.exec(delete(Printer).where(Printer.serial == "TEST-PRINTER-01"))
        await session.exec(delete(Order).where(Order.ebay_order_id == "TEST-ORDER-001"))
        await session.commit()

        # 3. Seed Data
        logger.info("🌱 Seeding Test Environment...")
        
        # Create Printer
        printer = Printer(
            serial="TEST-PRINTER-01",
            name="Test Printer",
            type="P1S",
            current_status=PrinterStatusEnum.IDLE,
            ip_address="127.0.0.1",
            access_code="12345678"
        )
        session.add(printer)
        
        # Create Order
        order = Order(
            ebay_order_id="TEST-ORDER-001",
            buyer_username="test_user",
            total_price=99.99,
            currency="USD",
            status="OPEN"
        )
        session.add(order)
        await session.commit() 
        await session.refresh(order)

        # Create AMS Slots (Slot 0: Red PLA)
        slot = AmsSlot(
            printer_id=printer.serial,
            ams_index=0,
            slot_index=0,
            tray_color="FF0000",
            tray_type="PLA",
            remaining_percent=100
        )
        session.add(slot)

        # Create Product (Needs Red PLA)
        product = Product(
            name="Test Vase",
            sku="TEST-SKU-001",
            file_path_3mf="TEST-GCODE-PATH.gcode",
            required_filament_type="PLA",
            required_filament_color="FF0000"
        )
        session.add(product)
        await session.commit()
        await session.refresh(product) 

        # Create Job
        job = Job(
            order_id=order.id, 
            gcode_path="TEST-GCODE-PATH.gcode",
            status=JobStatusEnum.PENDING,
        )
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        # Attach product manually for logic service (since it's not a relationship)
        # Dispatcher does this manually too.
        # job.product = product <-- REMOVED
        
        logger.info("✅ Data Seeded.")

        # 4. Verify Filament Manager Logic
        logger.info("🧠 Testing FilamentManager Logic...")
        fm = FilamentManager()
        # Re-attach product because session refresh might detach ephemeral attrs if not loaded
        # But in our dispatcher we load it. Here let's ensure.
        # Actually `find_best_printer` expects `job` to have `product` attached or logic finds it.
        # Our implementation of `_get_job_requirements` tries to access `job.product`.
        # Since we just added it, it might still be attached. If not, re-assign.
        # job.product = product <-- REMOVED
        
        match = await fm.find_best_printer(session, job, product=product)
        
        if match and match[0].serial == "TEST-PRINTER-01" and match[1] == [0]:
            logger.info("✅ FilamentManager: Correctly matched Test Printer.")
        else:
            logger.error(f"❌ FilamentManager Failed! Match: {match}")
            raise Exception("Filament Logic Failed")

        # 5. Verify Dispatcher Flow
        logger.info("🚀 Testing Dispatcher Flow...")
        dispatcher = ProductionDispatcher()
        dispatcher.commander = MockPrinterCommander() # HACK: Inject Mock
        
        # Run one cycle
        # We need to make sure the job we created is picked up.
        # Dispatcher queries DB for PENDING jobs.
        await dispatcher.run_cycle()
        
        # 6. Verify Results
        await session.refresh(job)
        await session.refresh(printer)
        
        logger.info(f"Final Job Status: {job.status}")
        logger.info(f"Final Printer Status: {printer.current_status}")

        if job.status in [JobStatusEnum.PRINTING, JobStatusEnum.UPLOADING]:
            logger.info("✅ Job Transitioned to PRINTING/UPLOADING.")
        else:
            logger.error("❌ Job did not transition!")
            raise Exception("Dispatcher Flow Failed")
            
        if printer.current_status == PrinterStatusEnum.PRINTING:
             logger.info("✅ Printer Transitioned to PRINTING.")
        else:
             logger.error("❌ Printer did not lock!")
             raise Exception("Printer Lock Failed")

    logger.info("🎉 System Integrity Check PASSED!")

if __name__ == "__main__":
    try:
        if sys.platform == 'win32':
             asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(run_check())
    except Exception as e:
        logger.error(f"FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
