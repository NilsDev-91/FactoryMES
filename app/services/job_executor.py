
import asyncio
import logging
import random
from app.core.database import async_session_maker
from app.services.job_dispatcher import job_dispatcher

logger = logging.getLogger("JobExecutor")

class JobExecutor:
    """
    Phase 10: Production Job Executor
    Integrates the JobDispatcher into a resilient infinite loop.
    """
    def __init__(self):
        self.is_running = False

    async def start(self):
        """Starts the autonomous production loop."""
        self.is_running = True
        logger.info("🚀 Autonomous Production Loop Started.")
        
        while self.is_running:
            try:
                await self.process_queue()
            except Exception as e:
                logger.error(f"Error in production loop: {e}", exc_info=True)
            
            # Frequency: Sleep for 5-10 seconds between cycles to avoid hammering DB/MQTT
            sleep_time = random.uniform(5, 10)
            await asyncio.sleep(sleep_time)

    async def stop(self):
        """Stops the loop."""
        self.is_running = False
        logger.info("🛑 Autonomous Production Loop Stopping...")

    async def process_queue(self):
        """
        Main execution logic.
        Strictly relies on the JobDispatcher to find the best match based on AMS telemetry.
        """
        async with async_session_maker() as session:
            # Inject the JobDispatcher matching logic
            await job_dispatcher.dispatch_next_job(session)

# Singleton
executor = JobExecutor()
