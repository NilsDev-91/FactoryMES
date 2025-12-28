import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
from sqlmodel import Session, create_engine, SQLModel, select
from app.models.core import Job, Product, JobStatusEnum
from app.models.order import Order, OrderItem
from app.models.ebay import EbayOrder, EbayLineItem, EbayPricingSummary, EbayBuyer, EbayPrice, EbayVariationAspect
from app.services.production.order_processor import OrderProcessor

from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Setup Async In-Memory DB
# We utilize persistent mode for in-memory sqlite if possible, but shared cache is easier
# Or just use a specific instance.
engine = create_async_engine("sqlite+aiosqlite:///:memory:")

async def run_verification():
    print("--- Starting Order Ingestion Logic Verification ---")
    
    # 0. Create Tables
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    
    # 1. Seed Database with a Product
    async with AsyncSession(engine) as session:
        product = Product(
            sku="TEST-SKU-123",
            name="Test Product",
            file_path_3mf="/path/to/test.3mf",
            required_filament_type="PLA",
            required_filament_color="#FF0000"
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        print(f"Canary Product created: {product.sku}")

    # 2. Mock eBay Data
    mock_order = EbayOrder(
        orderId="TEST-ORDER-001",
        creationDate="2023-01-01T00:00:00.000Z",
        lastModifiedDate="2023-01-02T00:00:00.000Z",
        orderFulfillmentStatus="NOT_STARTED",
        orderPaymentStatus="PAID",
        buyer=EbayBuyer(username="test_buyer"),
        pricingSummary=EbayPricingSummary(
            total=EbayPrice(value="10.00", currency="USD")
        ),
        lineItems=[
            EbayLineItem(
                lineItemId="LI-001",
                legacyItemId="LEG-001",
                sku="TEST-SKU-123",
                title="Test Product - Red",
                quantity=2,
                variationAspects=[
                    EbayVariationAspect(name="Color", value="#00FF00")
                ]
            )
        ]
    )

    # 3. Instantiate OrderProcessor
    processor = OrderProcessor()
    
    # 4. Patch external dependencies
    # We patch `ebay_orders.fetch_orders` and `get_session`
    with patch("app.services.production.order_processor.ebay_orders") as mock_ebay, \
         patch("app.services.production.order_processor.get_session") as mock_get_session:
        
        # Mock Fetch
        mock_ebay.fetch_orders = AsyncMock(return_value=[mock_order])
        
        # Mock Session Generator
        async def session_yielder():
            async with AsyncSession(engine) as session:
                yield session
        mock_get_session.side_effect = session_yielder

        # 5. Run Sync
        print("Running sync_orders()...")
        await processor.sync_orders()

    # 6. Verify Results
    async with AsyncSession(engine) as session:
        # Check Order
        result = await session.exec(select(Order))
        order = result.first()
        if order:
            print(f"[PASS] Order created: {order.ebay_order_id}")
            print(f"       Status: {order.status}")
            print(f"       Total Price: {order.total_price} {order.currency}")
        else:
            print("[FAIL] Order NOT created.")

        # Check Jobs (Should be 2 because quantity=2)
        result = await session.exec(select(Job))
        jobs = result.all()
        if len(jobs) == 2:
            print(f"[PASS] Correct number of Jobs created: {len(jobs)}")
        else:
            print(f"[FAIL] Expected 2 Jobs, found {len(jobs)}")

        if jobs:
            job = jobs[0]
            print(f"       Job Status: {job.status}")
            print(f"       Job Requirements: {job.filament_requirements}")
            
            # Check Variation Override Logic
            # Product default was #FF0000, Variation was #00FF00
            if job.filament_requirements.get("color") == "#00FF00":
                print("[PASS] Variation color override logic worked.")
            else:
                print(f"[FAIL] Variation logic failed. Got {job.filament_requirements.get('color')}")

if __name__ == "__main__":
    asyncio.run(run_verification())
