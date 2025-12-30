import asyncio
import logging
import sys
import uuid
from pathlib import Path

# Add project root to Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlmodel import select
from app.core.database import async_session_maker
from app.models.core import Job, JobStatusEnum
from app.models.order import Order
from app.models.product_sku import ProductSKU

# Setup Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SimulateEbay")

async def main():
    logger.info("Starting eBay Order Simulation...")
    
    async with async_session_maker() as session:
        # 1. Lookup SKUs
        sku_white = (await session.exec(select(ProductSKU).where(ProductSKU.sku == "EYE_WHITE"))).first()
        sku_red = (await session.exec(select(ProductSKU).where(ProductSKU.sku == "EYE_RED"))).first()
        
        # Validation/Fallback
        if not sku_white:
             logger.warning("SKU EYE_WHITE not found. Using fallback hex #FFFFFF.")
             white_req = [{"color_hex": "#FFFFFF"}]
        else:
             white_req = [{"color_hex": sku_white.hex_color}]

        if not sku_red:
             logger.warning("SKU EYE_RED not found. Using fallback hex #FF0000.")
             red_req = [{"color_hex": "#FF0000"}]
        else:
             red_req = [{"color_hex": sku_red.hex_color}]

        # 2. Create Order
        order_id = str(uuid.uuid4())[:8]
        order = Order(
            ebay_order_id=f"EBAY_SIM_{order_id}",
            buyer_username="SimulateEbayUser",
            total_price=99.99,
            currency="USD",
            status="PAID"
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        logger.info(f"Created Order {order.ebay_order_id}")

        # 3. Create Job 1 (White) - Priority 10
        # Assuming gcode_path "Eye_Master.3mf" is standard for these SKUs based on previous script
        job_white = Job(
            order_id=order.id,
            gcode_path="Eye_Master.3mf",
            status=JobStatusEnum.PENDING,
            filament_requirements=white_req,
            priority=10
        )
        session.add(job_white)
        
        # 4. Create Job 2 (Red) - Priority 5
        job_red = Job(
            order_id=order.id,
            gcode_path="Eye_Master.3mf",
            status=JobStatusEnum.PENDING,
            filament_requirements=red_req,
            priority=5
        )
        session.add(job_red)
        
        await session.commit()
        await session.refresh(job_white)
        await session.refresh(job_red)
        
        print(f"Injecting Order #1: White (Pending) - ID: {job_white.id}")
        print(f"Injecting Order #2: Red (Pending) - ID: {job_red.id}")
        logger.info("Simulation complete.")

if __name__ == "__main__":
    asyncio.run(main())
