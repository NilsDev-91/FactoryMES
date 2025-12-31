import asyncio
import os
import sys
# Ensure app modules are found
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import select, delete
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker, selectinload
import uuid

from app.core.config import settings
from app.models.core import Printer, Job, JobStatusEnum, Product, PrinterStatusEnum
from app.models.product_sku import ProductSKU
from app.models.order import Order, OrderItem

async def setup_live_test():
    print("🔌 Connecting to Database...")
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # =================================================================================================
        # 1. Printer Setup (A1 REAL)
        # =================================================================================================
        print("\n🔧 STEP 1: PRINTER SETUP")
        stmt_printer = select(Printer).where(Printer.name == "A1 REAL")
        printer = (await session.exec(stmt_printer)).first()

        if not printer:
            print("❌ CRITICAL: Printer 'A1 REAL' not found!")
            stmt_any = select(Printer)
            printer = (await session.exec(stmt_any)).first()
            if printer:
                print(f"⚠️  Fallback: Using '{printer.name}' ({printer.serial})")
            else:
                print("❌ FATAL: No printers found. Aborting.")
                return

        print(f"✅ Target Printer: {printer.name} ({printer.serial})")
        
        # Reset Printer State
        printer.is_plate_cleared = True
        printer.current_status = PrinterStatusEnum.IDLE 
        session.add(printer)
        print("✨ Printer state reset: Plate Cleared = TRUE, Status = IDLE")
        
        # NO AMS SEEDING! We rely on Live Data or manual FMS setup.
        print("⚠️  Mode: NO AMS SEEDING. Relying on FMS and Live Printer Data.")

        # =================================================================================================
        # 2. Clean Slate
        # =================================================================================================
        print("\n🧹 STEP 2: CLEANUP")
        await session.exec(delete(Job))
        await session.exec(delete(OrderItem))
        await session.exec(delete(Order))
        print("✅ Production Queue & Orders Cleared.")
        
        print("⏳ Waiting 5 seconds before seeding new orders...")
        await asyncio.sleep(5)

        # =================================================================================================
        # 3. Strict Catalog Validation
        # =================================================================================================
        print("\n📜 STEP 3: CATALOG VALIDATION")
        
        # A. Find Parent Product "Eye"
        stmt_parent = select(Product).where(Product.name == "Eye")
        parent_product = (await session.exec(stmt_parent)).first()
        
        if not parent_product:
            print("❌ CRITICAL: Parent Product 'Eye' not found!")
            return
            
        print(f"✅ Found Parent Product: 'Eye' (ID: {parent_product.id})")
        
        # B. Find Variants (Robust Lookup: "WHITE - EYE" or "Eye - PLA (#FFFFFF)")
        async def get_sku_robust(names):
            for n in names:
                s = select(ProductSKU).where(ProductSKU.name == n).options(
                     selectinload(ProductSKU.product),
                     selectinload(ProductSKU.print_file)
                )
                res = (await session.exec(s)).first()
                if res: return res
            return None

        sku_white = await get_sku_robust(["WHITE - EYE", "Eye - PLA (#FFFFFF)"])
        sku_red = await get_sku_robust(["RED - EYE", "Eye - PLA (#FF0000)"])
        
        if not sku_white:
            print("❌ CRITICAL: SKU 'WHITE - EYE' (or alias) not found.")
            return
        if not sku_red:
            print("❌ CRITICAL: SKU 'RED - EYE' (or alias) not found.")
            return
            
        print(f"✅ Found SKU: {sku_white.name}")
        print(f"✅ Found SKU: {sku_red.name}")
        
        # C. Resolve File Path (Log Logic)
        def resolve_and_log(sku):
            if sku.print_file:
                 return sku.print_file.file_path, "Variant Specific"
            
            if sku.product and sku.product.file_path_3mf:
                 return sku.product.file_path_3mf, "Inherited from Parent"
                 
            return None, "Missing"

        path_white, source_white = resolve_and_log(sku_white)
        print(f"🔍 File Resolution (White): {path_white} ({source_white})")
        if source_white == "Missing":
             print("❌ CRITICAL: No file path found for White SKU!")
             return

        path_red, source_red = resolve_and_log(sku_red)

        # =================================================================================================
        # 4. Create Production Orders
        # =================================================================================================
        print("\n📦 STEP 4: CREATE ORDERS")
        
        # Order A: White (Priority 20)
        u1 = uuid.uuid4().hex[:6].upper()
        order1 = Order(ebay_order_id=f"ORD-WHT-{u1}", buyer_username="Tester_White", total_price=50.0, currency="USD", status="PAID")
        session.add(order1)
        await session.commit()
        
        item1 = OrderItem(order_id=order1.id, sku=sku_white.sku, title=sku_white.name, quantity=1, variation_details="Color: White")
        session.add(item1)
        
        # Job A (NO virtual-id, FMS Logic Only)
        # Note: We use the resolved path_white
        reqs_white = [{"hex_color": sku_white.hex_color or "#FFFFFF", "material": "PLA"}]
        
        job1 = Job(
            order_id=order1.id,
            product=parent_product,
            assigned_printer_serial=printer.serial, # Pre-assigning to force target printer checking
            gcode_path=path_white,
            status=JobStatusEnum.PENDING,
            priority=20,
            filament_requirements=reqs_white
        )
        session.add(job1)
        
        # Order B: Red (Priority 10)
        u2 = uuid.uuid4().hex[:6].upper()
        order2 = Order(ebay_order_id=f"ORD-RED-{u2}", buyer_username="Tester_Red", total_price=50.0, currency="USD", status="PAID")
        session.add(order2)
        await session.commit()
        
        item2 = OrderItem(order_id=order2.id, sku=sku_red.sku, title=sku_red.name, quantity=1, variation_details="Color: Red")
        session.add(item2)
        
        reqs_red = [{"hex_color": sku_red.hex_color or "#FF0000", "material": "PLA"}]
        
        job2 = Job(
            order_id=order2.id,
            product=parent_product,
            assigned_printer_serial=printer.serial,
            gcode_path=path_red,
            status=JobStatusEnum.PENDING,
            priority=10,
            filament_requirements=reqs_red # Pure FMS
        )
        session.add(job2)
        
        await session.commit()
        
        print(f"🚀 Orders Created:")
        print(f"   1. Order {order1.ebay_order_id}: {sku_white.name} -> Job PENDING (Prio 20)")
        print(f"   2. Order {order2.ebay_order_id}: {sku_red.name}   -> Job PENDING (Prio 10)")
        
        print("\n✅ SETUP COMPLETE. FMS should now match Filament Requirements to Live AMS Data.")
        print("\n⚠️  IMPORTANT: Please RESTART the backend (uvicorn) to apply the latest 'commander.py' fixes!")

if __name__ == "__main__":
    asyncio.run(setup_live_test())
