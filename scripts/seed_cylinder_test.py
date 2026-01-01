
import asyncio
import logging
from sqlalchemy import delete, select
from app.core.database import async_session_maker
from app.models.core import Job, Product, JobStatusEnum

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("SeedCylinderTest")

async def seed():
    async with async_session_maker() as session:
        # Step 1: Purge (Ghost Busting)
        logger.info("🧹 Purging ghost jobs from the queue...")
        result = await session.execute(delete(Job))
        await session.commit()
        logger.info(f"🧹 Cleared {result.rowcount} ghost jobs from the queue.")

        # Step 2: Product Verification
        logger.info("🔍 Verifying product 'Zylinder'...")
        stmt = select(Product).where(Product.name == "Zylinder")
        product = (await session.execute(stmt)).scalars().first()

        if not product:
            logger.error("❌ Product 'Zylinder' not found! Please create it in the UI first.")
            return

        # Safety Check
        is_continuous = getattr(product, "is_continuous_printing", False)
        part_height = getattr(product, "part_height_mm", 0) or 0

        if not is_continuous or part_height < 50:
            logger.error(
                f"❌ Safety Validation Failed for '{product.name}':\n"
                f"   - Continuous Printing: {is_continuous} (Expected: True)\n"
                f"   - Part Height: {part_height}mm (Expected: >= 50mm)\n"
                f"👉 Please fix the product definition in the UI before proceeding."
            )
            return
        
        logger.info(f"✅ Product '{product.name}' verified for autonomous production.")

        # Step 3: Seed Orders
        logger.info("🌱 Seeding cylinder test jobs...")
        
        # We need an order ID. Usually jobs are linked to orders.
        # For simplicity in this seed, we'll look for an existing order or assume 0 (not ideal).
        # Better: Create a dummy order for the test batch.
        from app.models.order import Order
        from datetime import datetime, timezone

        test_order = Order(
            ebay_order_id=f"TEST-CYLINDER-{int(datetime.now().timestamp())}",
            buyer_username="System_SRE_Phase10",
            total_price=0.0,
            currency="USD",
            status="OPEN",
            created_at=datetime.now(timezone.utc)
        )
        session.add(test_order)
        await session.flush() # Get ID

        jobs_to_create = [
            ("Blue", "#0000FF"),
            ("White", "#FFFFFF"),
            ("Red", "#FF0000")
        ]

        # Get G-code path from product or dummy
        gcode_path = product.file_path_3mf or "storage/models/zylinder_v1.3mf"

        new_jobs = []
        for color_name, hex_color in jobs_to_create:
            job = Job(
                order_id=test_order.id,
                gcode_path=gcode_path,
                status=JobStatusEnum.PENDING,
                priority=100,
                filament_requirements=[{
                    "hex_color": hex_color,
                    "material": "PLA",
                    "color_name": color_name
                }],
                job_metadata={
                    "is_continuous": True,
                    "model_height_mm": part_height
                }
            )
            session.add(job)
            new_jobs.append(job)

        await session.commit()
        
        # Output Summary
        logger.info("\n" + "="*40)
        logger.info(" PRODUCTION QUEUE SEEDED ")
        logger.info("="*40)
        for job in new_jobs:
            req = job.filament_requirements[0]
            logger.info(f" [+] Job ID {job.id}: {req['color_name']} ({req['hex_color']}) - PENDING")
        logger.info("="*40)
        logger.info(f"Ready for Autonomous Loop Integration.")

if __name__ == "__main__":
    asyncio.run(seed())
