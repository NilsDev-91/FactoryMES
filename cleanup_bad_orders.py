
import asyncio
import sys
from database import async_session_maker
from models import Order, Product
from sqlmodel import select, delete

async def cleanup_orders():
    async with async_session_maker() as session:
        print("--- CLEANING INVALID ORDERS ---")
        
        # 1. Get all valid SKUs
        result = await session.execute(select(Product.sku))
        valid_skus = result.scalars().all()
        print(f"Valid SKUs: {valid_skus}")
        
        if not valid_skus:
            print("WARNING: No products found? Skipping cleanup to be safe.")
            return

        # 2. Find Orders with invalid SKUs
        # Note: SQLModel doesn't support NOT IN efficiently with async usually, let's just fetch all orders
        # or do a fetch and delete logic in python for simplicity if dataset is small (<1000)
        
        result = await session.execute(select(Order))
        orders = result.scalars().all()
        
        deleted_count = 0
        for order in orders:
            if order.sku not in valid_skus:
                 # print(f"Deleting Invalid Order {order.id} (SKU: {order.sku})")
                 await session.delete(order)
                 deleted_count += 1
        
        await session.commit()
        print(f"DONE. Deleted {deleted_count} orders with invalid SKUs.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(cleanup_orders())
