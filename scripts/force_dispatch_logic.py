import asyncio
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set logging to DEBUG to see matching details
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("JobDispatcher")
matcher_logger = logging.getLogger("ColorMatcher")

from app.core.database import async_session_maker
from app.services.job_dispatcher import JobDispatcher

async def force_dispatch():
    dispatcher = JobDispatcher()
    print("🚀 Forcing local dispatch cycle...")
    async with async_session_maker() as session:
        await dispatcher.dispatch_next_job(session)
    print("🏁 Cycle complete.")

if __name__ == "__main__":
    asyncio.run(force_dispatch())
