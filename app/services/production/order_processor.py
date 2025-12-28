import logging
import asyncio
from typing import List, Optional
from sqlmodel import Session, select
from app.core.database import get_session
from app.core.config import settings
from app.models.core import Job, Product, JobStatusEnum
from app.models.order import Order, OrderItem
from app.services.ebay.orders import ebay_orders
from app.models.ebay import EbayOrder

logger = logging.getLogger(__name__)

class OrderProcessor:
    """
    Service to fetch orders from eBay and convert them into internal Jobs.
    """
    
    def __init__(self):
        self.running = False

    async def start_loop(self):
        """Background task loop."""
        self.running = True
        logger.info("OrderProcessor loop started.")
        while self.running:
            try:
                await self.sync_orders()
            except Exception as e:
                logger.error(f"Error in OrderProcessor loop: {e}", exc_info=True)
            
            await asyncio.sleep(60) # Run every 60 seconds

    async def sync_orders(self):
        """Fetches new orders and processes them."""
        logger.info("Syncing eBay orders...")
        
        # 1. Fetch from eBay
        try:
            new_orders = await ebay_orders.fetch_orders()
        except Exception as e:
            logger.error(f"Failed to fetch eBay orders: {e}")
            return

        if not new_orders:
            logger.info("No new orders found.")
            return

        async for session in get_session():
            for ebay_order in new_orders:
                # 2. Check deduplication
                stmt = select(Order).where(Order.ebay_order_id == ebay_order.order_id)
                result = await session.exec(stmt)
                existing_order = result.first()
                
                if existing_order:
                    logger.debug(f"Order {ebay_order.order_id} already exists. Skipping.")
                    continue
                
                # 3. Process new order
                try:
                    await self.process_order(session, ebay_order)
                except Exception as e:
                    logger.error(f"Failed to process order {ebay_order.order_id}: {e}", exc_info=True)

    async def process_order(self, session: Session, ebay_order: EbayOrder):
        """Converts a single eBay order into an internal Order and Jobs."""
        logger.info(f"Processing new order: {ebay_order.order_id}")
        
        # Create Order
        db_order = Order(
            ebay_order_id=ebay_order.order_id,
            buyer_username=ebay_order.buyer.username,
            total_price=float(ebay_order.pricing_summary.total.value),
            currency=ebay_order.pricing_summary.total.currency,
            status=ebay_order.order_fulfillment_status,
            created_at=ebay_order.creation_date
        )
        session.add(db_order)
        await session.flush() # Get ID
        
        # Process Line Items
        for item in ebay_order.line_items:
            # Create OrderItem
            db_item = OrderItem(
                order_id=db_order.id,
                sku=item.sku or "UNKNOWN",
                title=item.title,
                quantity=item.quantity,
                variation_details=str(item.variation_aspects) if item.variation_aspects else None
            )
            session.add(db_item)
            
            # Match Product & Create Job
            if item.sku:
                stmt = select(Product).where(Product.sku == item.sku)
                result = await session.exec(stmt)
                product = result.first()
                
                if product:
                    logger.info(f"Found matching product for SKU {item.sku}. Creating {item.quantity} Job(s).")
                    
                    # Create one job per quantity
                    for _ in range(item.quantity):
                        # Determine requirements
                        # Logic: Use Product default, override if variation suggests valid color
                        reqs = {
                            "material": product.required_filament_type,
                            "color": product.required_filament_color
                        }
                        
                        # Basic variation parsing (can be expanded)
                        if item.variation_aspects:
                            for aspect in item.variation_aspects:
                                if aspect.name.lower() in ["color", "colour"]:
                                    reqs["color"] = aspect.value
                                    break
                        
                        job = Job(
                            order_id=db_order.id,
                            gcode_path=product.file_path_3mf, # Using 3mf path as source
                            status=JobStatusEnum.PENDING,
                            filament_requirements=reqs
                        )
                        session.add(job)
                else:
                    logger.warning(f"No Product found for SKU {item.sku}. No Job created.")
            
        await session.commit()
        logger.info(f"Order {ebay_order.order_id} processed successfully.")

# Singleton
order_processor = OrderProcessor()
