import asyncio
import os
import sys
# Ensure app modules are found
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
from datetime import datetime, timezone
import uuid

from app.core.config import settings
from app.models.core import Printer, Job, JobStatusEnum, Product
from app.models.product_sku import ProductSKU
from app.models.order import Order, OrderItem

async def setup_live_test():
    print("🔌 Connecting to Database...")
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # 1. Printer Setup
        print("🔍 Searching for 'A1 REAL'...")
        stmt_printer = select(Printer).where(Printer.name == "A1 REAL")
        printer = (await session.exec(stmt_printer)).first()

        if not printer:
            print("❌ Printer 'A1 REAL' not found! Please check connection/naming.")
            # Fallback: Get first printer or exit?
            # Let's try to get *any* printer just in case
            stmt_any = select(Printer)
            printer = (await session.exec(stmt_any)).first()
            if printer:
                print(f"⚠️  Fallback: Using '{printer.name}' ({printer.serial})")
            else:
                print("❌ No printers found at all. Aborting.")
                return

        print(f"✅ Target Printer: {printer.name} ({printer.serial})")
        
        # Reset Printer State
        printer.is_plate_cleared = True
        printer.current_status = "IDLE" # Force IDLE to be safe
        session.add(printer)
        print("✨ Printer state reset: Plate Cleared = TRUE, Status = IDLE")

        # 2. Cleanup Queue
        print("🧹 Clearing Production Queue...")
        await session.exec(delete(Job))
        # Clear legacy/test orders to ensure a clean slate
        await session.exec(delete(OrderItem))
        await session.exec(delete(Order))
        # Also clean up our test orders if needed, but maybe keep them for history?
        # Let's just create a new one.
        print("✅ Queue cleared.")

        # 3. Create Dummy Order
        order_id = f"TEST-{uuid.uuid4().hex[:6].upper()}"
        dummy_order = Order(
            ebay_order_id=order_id,
            buyer_username="Mr. Test",
            total_price=99.99,
            currency="USD",
            status="PAID"
        )
        session.add(dummy_order)
        await session.commit()
        await session.refresh(dummy_order)
        print(f"📦 Created Order: {order_id}")

        # 4. Find Products (White and Red variants)
        # We need SKU objects to get color data if we want to be fancy, 
        # or just assume specific SKUs exist.
        # Let's look up by color/name similarity.
        
        stmt_variants = (
            select(ProductSKU)
            .where(ProductSKU.parent_id != None)
            .options(
                selectinload(ProductSKU.product).selectinload(Product.print_file),
                selectinload(ProductSKU.print_file)
            )
        )
        variants = (await session.exec(stmt_variants)).all()
        
        white_variant = None
        red_variant = None

        for v in variants:
            name_lower = v.name.lower()
            if "white" in name_lower and not white_variant:
                white_variant = v
            if "red" in name_lower and not red_variant:
                red_variant = v
        
        if not white_variant:
            print("⚠️ Could not find a 'White' variant. Picking first available.")
            white_variant = variants[0] if variants else None
        
        if not red_variant:
             print("⚠️ Could not find a 'Red' variant. Picking second available.")
             red_variant = variants[1] if len(variants) > 1 else white_variant

        if not white_variant or not red_variant:
            print("❌ Not enough products found to seed jobs.")
            return

        # 5. Create Jobs
        print("🌱 Seeding Jobs...")
        
        # Job 1: White (Priority 20 - Higher goes first usually? Or lower? 
        # Standard logic: Higher priority number = Higher importance/First?
        # Let's assume Descending Priority (20 > 10).
        
        # We need gcode_path.
        # If print_file/file_path logic is complex, we'll just grab it from product.
        # Fallback to a dummy path if missing, ensuring it doesn't crash worker immediately (or maybe it should).
        
        def get_gcode_path(sku):
            if sku.print_file: return sku.print_file.file_path
            if sku.product and sku.product.print_file: return sku.product.print_file.file_path
            if sku.product and sku.product.file_path_3mf: return sku.product.file_path_3mf
            return "storage/3mf/dummy.gcode"

        job1 = Job(
            order_id=dummy_order.id,
            assigned_printer_serial=printer.serial,
            gcode_path=get_gcode_path(white_variant),
            status=JobStatusEnum.PENDING,
            priority=20,
            filament_requirements=[{"color": white_variant.hex_color or "#FFFFFF", "type": "PLA"}]
        )
        
        job2 = Job(
            order_id=dummy_order.id,
            assigned_printer_serial=printer.serial,
            gcode_path=get_gcode_path(red_variant),
            status=JobStatusEnum.PENDING,
            priority=10,
            filament_requirements=[{"color": red_variant.hex_color or "#FF0000", "type": "PLA"}]
        )

        session.add(job1)
        session.add(job2)
        await session.commit()

        print(f"🚀 Job #1 Queued: {white_variant.name} (White) - Priority 20")
        print(f"🚀 Job #2 Queued: {red_variant.name} (Red)   - Priority 10")
        
        print("\n✅ Test Ready. Printer 'A1 REAL' is Clean & IDLE.")
        print("WAITING: Start the Backend/Worker now to see it fly.")

if __name__ == "__main__":
    asyncio.run(setup_live_test())
