
import asyncio
import logging
from app.core.database import engine
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MigratePhase5")

async def migrate():
    async with engine.begin() as conn:
        logger.info("Migrating Phase 5 Schema Changes...")
        
        # 0. Add missing enum values for PrinterStatusEnum
        enum_values = ["COOLDOWN", "CLEARING_BED"]
        for value in enum_values:
            try:
                await conn.execute(text(f"ALTER TYPE printerstatusenum ADD VALUE IF NOT EXISTS '{value}'"))
                logger.info(f"Added {value} to printerstatusenum")
            except Exception as e:
                logger.warning(f"Skipping enum {value}: {e}")
        
        # 1. Printer Columns
        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN IF NOT EXISTS jobs_since_calibration INTEGER DEFAULT 0"))
            logger.info("Added jobs_since_calibration to printers")
        except Exception as e:
            logger.warning(f"Skipping jobs_since_calibration: {e}")

        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN IF NOT EXISTS calibration_interval INTEGER DEFAULT 5"))
            logger.info("Added calibration_interval to printers")
        except Exception as e:
            logger.warning(f"Skipping calibration_interval: {e}")

        # 2. Job Columns
        try:
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ"))
            logger.info("Added updated_at to jobs")
        except Exception as e:
            logger.warning(f"Skipping updated_at: {e}")

        try:
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_metadata JSONB DEFAULT '{}'"))
            logger.info("Added job_metadata to jobs")
        except Exception as e:
            logger.warning(f"Skipping job_metadata: {e}")

        # 3. Phase 6: Product Columns for Continuous Printing
        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS part_height_mm FLOAT"))
            logger.info("Added part_height_mm to products")
        except Exception as e:
            logger.warning(f"Skipping part_height_mm: {e}")

        try:
            await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS is_continuous_printing BOOLEAN DEFAULT FALSE"))
            logger.info("Added is_continuous_printing to products")
        except Exception as e:
            logger.warning(f"Skipping is_continuous_printing: {e}")

        # 4. Phase 7: HMS Watchdog - Error Status Enums
        phase7_enums = ["ERROR", "PAUSED"]
        for value in phase7_enums:
            try:
                await conn.execute(text(f"ALTER TYPE printerstatusenum ADD VALUE IF NOT EXISTS '{value}'"))
                logger.info(f"Added {value} to printerstatusenum")
            except Exception as e:
                logger.warning(f"Skipping enum {value}: {e}")

        # 5. Phase 7: Printer Error Tracking Columns
        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN IF NOT EXISTS last_error_code VARCHAR"))
            logger.info("Added last_error_code to printers")
        except Exception as e:
            logger.warning(f"Skipping last_error_code: {e}")

        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN IF NOT EXISTS last_error_time TIMESTAMPTZ"))
            logger.info("Added last_error_time to printers")
        except Exception as e:
            logger.warning(f"Skipping last_error_time: {e}")

        try:
            await conn.execute(text("ALTER TABLE printers ADD COLUMN IF NOT EXISTS last_error_description VARCHAR"))
            logger.info("Added last_error_description to printers")
        except Exception as e:
            logger.warning(f"Skipping last_error_description: {e}")

    logger.info("Migration Complete.")

if __name__ == "__main__":
    asyncio.run(migrate())
