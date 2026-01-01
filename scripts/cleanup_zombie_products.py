import asyncio
import sys
import os

# Add project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from app.services.product_service import ProductService

async def cleanup():
    # Targeted deletion of discovered zombie Product IDs
    zombie_product_ids = [41, 52]
    
    async with async_session_maker() as session:
        for p_id in zombie_product_ids:
            print(f"🗑️ Deleting zombie Product ID {p_id}...")
            success = await ProductService.delete_product(p_id, session)
            if success:
                print(f"   ✅ Successfully deleted Product {p_id}")
            else:
                print(f"   ⚠️ Product {p_id} not found or already deleted.")

if __name__ == "__main__":
    asyncio.run(cleanup())
