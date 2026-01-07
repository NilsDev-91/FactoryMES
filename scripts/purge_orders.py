import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select, delete
from app.models.core import Job
from app.models.order import Order, OrderItem

async def purge_orders():
    async with async_session_maker() as session:
        print("🧹 Purging all Jobs and Orders...")
        
        # 1. Delete Jobs first (FK constraint)
        await session.execute(delete(Job))
        print("  - Deleted all Jobs")

        # 2. Delete OrderItems
        await session.execute(delete(OrderItem))
        print("  - Deleted all OrderItems")
        
        # 3. Delete Orders
        await session.execute(delete(Order))
        print("  - Deleted all Orders")
        
        await session.commit()
    print("✅ All incoming order data purged.")

if __name__ == "__main__":
    asyncio.run(purge_orders())
