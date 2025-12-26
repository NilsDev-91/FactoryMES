
import asyncio
import sys
import logging
import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Try importing pandas
try:
    import pandas as pd
except ImportError:
    print("Pandas not installed. Please run: pip install pandas")
    sys.exit(1)

from sqlmodel import select
from database import async_session_maker
from models import Order, PlatformEnum, OrderStatusEnum

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("eBayIngest")

# --- Configuration Loader ---
def load_env():
    """Simple .env loader to avoid dependencies"""
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"): continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    os.environ[key] = value

load_env()

EBAY_APP_ID = os.getenv("EBAY_APP_ID")
EBAY_CERT_ID = os.getenv("EBAY_CERT_ID")
EBAY_USER_TOKEN = os.getenv("EBAY_USER_TOKEN")
EBAY_ENV = os.getenv("EBAY_ENV", "SANDBOX")

BASE_URL = "https://api.sandbox.ebay.com" if EBAY_ENV == "SANDBOX" else "https://api.ebay.com"

def fetch_ebay_orders() -> List[Dict[str, Any]]:
    """
    Fetches real orders from eBay Fulfillment API.
    """
    if not EBAY_USER_TOKEN:
        logger.error("No eBay User Token found. Please check .env")
        return []

    logger.info(f"Fetching orders from eBay ({EBAY_ENV})...")
    
    # Endpoint: getOrders (Fulfillment API v1)
    # Docs: https://developer.ebay.com/api-docs/sell/fulfillment/resources/order/methods/getOrders
    url = f"{BASE_URL}/sell/fulfillment/v1/order"
    
    headers = {
        "Authorization": f"Bearer {EBAY_USER_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # Filter for unfulfilled orders if possible, or just last 30 days
    # params = {"filter": "orderfulfillmentstatus:{NOT_STARTED|IN_PROGRESS}"} 
    # For Sandbox, let's just grab everything to ensure we see data
    params = {"limit": 50}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        
        orders = data.get("orders", [])
        logger.info(f"Retrieved {len(orders)} orders from eBay.")
        
        parsed_orders = []
        for o in orders:
            order_id = o.get("orderId")
            creation_date = o.get("creationDate")
            
            line_items = o.get("lineItems", [])
            for item in line_items:
                parsed_orders.append({
                    "OrderID": order_id,
                    "SKU": item.get("sku", "UNKNOWN_SKU"),
                    "Quantity": int(item.get("quantity", 1)),
                    "CreatedDate": creation_date,
                    "Platform": "EBAY",
                    "Status": o.get("orderFulfillmentStatus")
                })
                
        return parsed_orders

    except requests.exceptions.HTTPError as e:
        logger.error(f"eBay API Error: {e}")
        if e.response is not None:
             logger.error(f"Response: {e.response.text}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return []

async def process_orders(df: pd.DataFrame):
    """
    Upserts orders from DataFrame to Database.
    """
    if df.empty:
        logger.info("DataFrame is empty. Nothing to process.")
        return

    logger.info(f"Processing {len(df)} line items...")
    
    async with async_session_maker() as session:
        for index, row in df.iterrows():
            platform_id = str(row['OrderID'])
            
            # Check if exists
            result = await session.execute(select(Order).where(Order.platform_order_id == platform_id))
            existing_order = result.scalars().first()
            
            if existing_order:
                # Optional: Update status?
                logger.info(f"Order {platform_id} already exists. Skipping.")
                continue
            
            # Create new Order
            # Parse Date
            try:
                # ISO 8601 from eBay: 2024-12-25T10:00:00.000Z
                purchase_date = pd.to_datetime(row['CreatedDate']).to_pydatetime()
            except:
                purchase_date = datetime.now()

            new_order = Order(
                platform=PlatformEnum.EBAY,
                platform_order_id=platform_id,
                sku=row['SKU'],
                quantity=int(row['Quantity']),
                purchase_date=purchase_date,
                status=OrderStatusEnum.OPEN
            )
            
            session.add(new_order)
            logger.info(f"Added Order: {platform_id} ({row['SKU']})")
        
        await session.commit()
        logger.info("Database sync complete.")

async def main():
    # 1. Fetch Data
    raw_data = fetch_ebay_orders()
    
    if not raw_data:
        logger.warning("No data retrieved.")
        return

    # 2. Create DataFrame
    df = pd.DataFrame(raw_data)
    
    print("\n--- DataFrame Head ---")
    print(df.head())
    print("----------------------\n")

    # 3. Ingest to DB
    await process_orders(df)

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())
