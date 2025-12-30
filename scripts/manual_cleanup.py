import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import delete
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# Ensure app modules are found
sys.path.append(os.getcwd())

from app.core.config import settings
from app.models.core import Job
from app.models.order import Order, OrderItem

async def manual_cleanup():
    print("🔌 Connecting to Database...")
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("\n🧹 CLEARING DATA...")
        await session.exec(delete(Job))
        print("   - Deleted Jobs")
        await session.exec(delete(OrderItem))
        print("   - Deleted Order Items")
        await session.exec(delete(Order))
        print("   - Deleted Orders")
        
        await session.commit()
        print("✅ CLEANUP COMPLETE. Database is fresh.")

if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    except:
        pass
    asyncio.run(manual_cleanup())
