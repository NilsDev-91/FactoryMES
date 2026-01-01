import asyncio
import os
import sys
from sqlmodel import select
from sqlalchemy.orm import selectinload

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
        
        results = []
        all_valid = True
        for order in orders:
            try:
                OrderRead.model_validate(order)
                results.append(f"Order {order.id}: VALID")
            except Exception as e:
                all_valid = False
                results.append(f"Order {order.id}: INVALID - {e}")

        with open("serialization_test_result.txt", "w", encoding="utf-8") as f:
            f.write(f"Total Orders: {len(orders)}\n")
            f.write(f"All Valid: {all_valid}\n\n")
            f.write("\n".join(results))

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(test_get_orders())
