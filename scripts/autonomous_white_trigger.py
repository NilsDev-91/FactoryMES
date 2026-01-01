import asyncio
import os
import sys
import logging
from datetime import datetime, timezone
from sqlmodel import select
from sqlalchemy.orm import selectinload

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.core import Job, JobStatusEnum, Printer
from app.models.order import Order
from app.models.ebay import EbayOrder, EbayLineItem, EbayPricingSummary, EbayPrice, EbayBuyer
from app.services.production.order_processor import order_processor
from app.services.job_dispatcher import job_dispatcher

# Setup logging to see what's happening
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AutonomousTrigger")

async def trigger_and_monitor():
    order_id = f"AUTO-WHITE-{int(datetime.now(timezone.utc).timestamp())}"
    
    # 1. Construct eBay Payload
    mock_order = EbayOrder(
        order_id=order_id,
        creation_date=datetime.now(timezone.utc),
        last_modified_date=datetime.now(timezone.utc),
        order_payment_status="PAID",
        order_fulfillment_status="NOT_STARTED",
        buyer=EbayBuyer(username="AutonomousTester"),
        pricing_summary=EbayPricingSummary(total=EbayPrice(value="25.00", currency="EUR")),
        line_items=[
            EbayLineItem(
                sku="ZYL-WHITE",
                title="Zylinder - White",
                quantity=1,
                line_item_id="LI-WHITE-1",
                legacy_item_id="LEGACY-W-1"
            )
        ]
    )

    async with async_session_maker() as session:
        print(f"\n[1] Injecting Order: {order_id}")
        await order_processor.process_order(session, mock_order)
        await session.commit()

        # 2. Wait for Job creation & Dispatch
        print("\n[2] Monitoring Pipeline...")
        for i in range(12): # 60 seconds
            # Refresh session for each check to avoid stale data
            async with async_session_maker() as poll_session:
                # Check Order
                res = await poll_session.exec(select(Order).where(Order.ebay_order_id == order_id).options(selectinload(Order.jobs)))
                db_order = res.first()
                
                if not db_order:
                    print(f"   [{i*5}s] Order still not in DB...")
                elif not db_order.jobs:
                    print(f"   [{i*5}s] Order found, waiting for Job creation...")
                else:
                    job = db_order.jobs[0]
                    print(f"   [{i*5}s] Job {job.id} Status: {job.status}")
                    
                    if job.status == JobStatusEnum.PRINTING:
                        print(f"\n🚀 SUCCESS! Job is now PRINTING on {job.assigned_printer_serial}")
                        return
                        
                    if job.status == JobStatusEnum.PENDING:
                        print("   (Triggering manual Dispatch cycle...)")
                        await job_dispatcher.dispatch_next_job(poll_session)
                        # We don't commit here because dispatch_next_job handles its own commits 
                        # but let's check the result in next iteration
                
            await asyncio.sleep(5)

    print("\n⚠️ Pipeline monitoring timed out. Job did not reach PRINTING state.")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(trigger_and_monitor())
