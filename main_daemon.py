
import asyncio
import logging
import sys
from init_db import init_db
import worker_service
import order_service

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MainDaemon")

async def main():
    logger.info("FactoryOS Daemon starting...")
    
    # 1. DB Init (Run init_db logic if needed, or ensure tables exist)
    # The original main_daemon called init_db(). Since init_db is async compatible:
    # We might need to import the async function from init_db.py
    # checking init_db.py: it has `async def init_db()`
    from init_db import init_db as run_init_db
    logger.info("Checking database...")
    await run_init_db()

    # 2. Start Services
    # We run both service loops concurrently
    logger.info("Starting Services...")
    
    await asyncio.gather(
        worker_service.main(),       # The Smart Dispatcher & Printer Manager
        order_service.run_service_loop() # The Order Generator
    )

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutdown...")
