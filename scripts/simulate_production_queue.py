import asyncio
import logging
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import (
    Product, 
    ProductRequirement, 
    Job, 
    JobStatusEnum, 
    PlatformEnum
)
from app.models.order import Order, OrderItem
from app.models.product_sku import ProductSKU
from app.models.filament import FilamentProfile
from app.models.print_file import PrintFile

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimulateQueue")

async def main():
    logger.info("Starting Production Queue Simulation...")
    
    async with async_session_maker() as session:
        # 1. Filament Profiles (White & Red)
        logger.info("Ensuring Filament Profiles...")
        
        # White
        fp_white = (await session.exec(select(FilamentProfile).where(FilamentProfile.color_hex == "#FFFFFF"))).first()
        if not fp_white:
            fp_white = FilamentProfile(
                brand="Generic",
                material="PLA",
                color_hex="#FFFFFF",
                density=1.24,
                spool_weight=1000
            )
            session.add(fp_white)
            logger.info("Created White Profile.")
        
        # Red
        fp_red = (await session.exec(select(FilamentProfile).where(FilamentProfile.color_hex == "#FF0000"))).first()
        if not fp_red:
            fp_red = FilamentProfile(
                brand="Generic",
                material="PLA",
                color_hex="#FF0000",
                density=1.24,
                spool_weight=1000
            )
            session.add(fp_red)
            logger.info("Created Red Profile.")
            
        await session.commit()
        await session.refresh(fp_white)
        await session.refresh(fp_red)

        # 2. Print File
        logger.info("Ensuring Print File...")
        pf = (await session.exec(select(PrintFile).where(PrintFile.file_path == "Eye_Master.3mf"))).first()
        if not pf:
            pf = PrintFile(
                file_path="Eye_Master.3mf",
                file_size_bytes=1024,
                uploaded_at=datetime.now(timezone.utc)
            )
            session.add(pf)
            await session.commit()
            await session.refresh(pf)
            logger.info("Created PrintFile 'Eye_Master.3mf'.")

        # 3. Product (Eye_Master)
        logger.info("Ensuring Master Product...")
        master = (await session.exec(select(Product).where(Product.name == "Eye_Master"))).first()
        if not master:
            master = Product(
                name="Eye_Master",
                sku="EYE_MASTER",
                description="Master Eye Product",
                print_file_id=pf.id
            )
            session.add(master)
            await session.commit()
            await session.refresh(master)
            logger.info("Created Master Product.")
        else:
             # Ensure print file link
             if not master.print_file_id:
                 master.print_file_id = pf.id
                 session.add(master)
                 await session.commit()

        # 4. SKUs (White & Red)
        logger.info("Ensuring SKUs...")
        
        # SKU White
        sku_white = (await session.exec(select(ProductSKU).where(ProductSKU.sku == "EYE_WHITE"))).first()
        if not sku_white:
            sku_white = ProductSKU(
                sku="EYE_WHITE",
                name="Eye (White)",
                product_id=master.id,
                hex_color="#FFFFFF",
                print_file_id=pf.id
            )
            session.add(sku_white)
            await session.commit()
            await session.refresh(sku_white)
            logger.info("Created SKU Eye_White.")
            
            # Link Requirement
            req = ProductRequirement(
                product_sku_id=sku_white.id,
                filament_profile_id=fp_white.id
            )
            session.add(req)
            await session.commit()

        # SKU Red
        sku_red = (await session.exec(select(ProductSKU).where(ProductSKU.sku == "EYE_RED"))).first()
        if not sku_red:
            sku_red = ProductSKU(
                sku="EYE_RED",
                name="Eye (Red)",
                product_id=master.id,
                hex_color="#FF0000",
                print_file_id=pf.id
            )
            session.add(sku_red)
            await session.commit()
            await session.refresh(sku_red)
            logger.info("Created SKU Eye_Red.")
            
            # Link Requirement
            req = ProductRequirement(
                product_sku_id=sku_red.id,
                filament_profile_id=fp_red.id
            )
            session.add(req)
            await session.commit()

        # 5. Orders & Jobs
        logger.info("Creating Simulation Orders...")
        
        # Create Dummy Order
        order_id = str(uuid.uuid4())[:8]
        order = Order(
            ebay_order_id=f"SIM_{order_id}",
            buyer_username="SimUser",
            total_price=50.0,
            currency="USD",
            status="PAID"
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        
        # Create Order Items
        item1 = OrderItem(order_id=order.id, sku="EYE_WHITE", title="Eye White", quantity=1)
        item2 = OrderItem(order_id=order.id, sku="EYE_RED", title="Eye Red", quantity=1)
        session.add_all([item1, item2])
        await session.commit()
        
        # Create Job 1 (White)
        job1 = Job(
            order_id=order.id,
            gcode_path="Eye_Master.3mf",
            status=JobStatusEnum.PENDING,
            filament_requirements=[{"color_hex": "#FFFFFF"}] # Snapshot of requirement
        )
        session.add(job1)
        
        # Create Job 2 (Red)
        job2 = Job(
            order_id=order.id,
            gcode_path="Eye_Master.3mf",
            status=JobStatusEnum.PENDING,
            filament_requirements=[{"color_hex": "#FF0000"}]
        )
        session.add(job2)
        
        await session.commit()
        await session.refresh(job1)
        await session.refresh(job2)
        
        print(f"Created Job {job1.id} (White) - Priority 10")
        print(f"Created Job {job2.id} (Red) - Priority 5")
        
        logger.info("Simulation ready. 2 Jobs queued. Waiting for Printer to go IDLE.")

if __name__ == "__main__":
    asyncio.run(main())
