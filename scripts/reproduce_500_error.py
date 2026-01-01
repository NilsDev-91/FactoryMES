import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.orm import selectinload
from pydantic import ValidationError

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.order import Order, OrderRead

async def test_get_orders():
    async with async_session_maker() as session:
        result = await session.execute(
            select(Order)
            .options(selectinload(Order.items), selectinload(Order.jobs))
            .order_by(Order.created_at.desc())
        )
        orders = result.scalars().all()
        print(f"Fetched {len(orders)} orders.")
        
        for order in orders:
            try:
                # Attempt to validate with OrderRead
                OrderRead.model_validate(order)
                print(f"Order {order.id}: VALID")
            except Exception as e:
                print(f"Order {order.id}: INVALID")
                print(f"   Error Type: {type(e).__name__}")
                print(f"   Error: {e}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_get_orders())
