import asyncio
import argparse
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import delete
from app.core.database import async_session_maker
from app.models.core import ProductRequirement, Product
from app.models.product_sku import ProductSKU

async def reset_catalog(force: bool):
    """
    Wipes the Product Catalog data: ProductRequirement, ProductSKU, and Product.
    Leaves PrintFile and FilamentProfile intact.
    """
    print("WARNING: This will wipe ALL Product Catalog data (Requirements, SKUs, Products).")
    print("PrintFiles and FilamentProfiles will be preserved.")
    
    if not force:
        confirm = input("Type 'DELETE' to confirm: ")
        if confirm != "DELETE":
            print("Aborted.")
            return

    async with async_session_maker() as session:
        print("Deleting ProductRequirements...")
        # Delete Requirements first to satisfy FK constraints
        req_result = await session.execute(delete(ProductRequirement))
        req_count = req_result.rowcount

        print("Deleting ProductSKUs...")
        # Delete SKUs next
        sku_result = await session.execute(delete(ProductSKU))
        sku_count = sku_result.rowcount
        
        print("Deleting Products...")
        # Delete Products last
        prod_result = await session.execute(delete(Product))
        prod_count = prod_result.rowcount

        await session.commit()
        
        print("-" * 30)
        print("Catalog Wiped Successfully.")
        print(f"Deleted {req_count} Requirements")
        print(f"Deleted {sku_count} SKUs")
        print(f"Deleted {prod_count} Products")
        print("-" * 30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Wipe Product Catalog Data")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    asyncio.run(reset_catalog(args.force))
