import logging
import asyncio
from typing import List, Optional
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.config import settings
from app.models.core import Job, Product, JobStatusEnum
from app.models.order import Order, OrderItem
from app.models.product_sku import ProductSKU
from app.models.print_file import PrintFile
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

    async def process_order(self, session: AsyncSession, ebay_order: EbayOrder):
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
            
            # Match Product/SKU & Create Job
            if item.sku:
                # 1. Try matching with ProductSKU (Master-Variant Architecture)
                sku_stmt = (
                    select(ProductSKU)
                    .where(ProductSKU.sku == item.sku)
                    .options(
                        selectinload(ProductSKU.print_file), 
                        selectinload(ProductSKU.product).selectinload(Product.print_file)
                    )
                )
                sku_result = await session.exec(sku_stmt)
                sku_record = sku_result.first()
                
                if sku_record:
                    logger.info(f"Found matching ProductSKU for SKU {item.sku}.")
                    
                    # Resolve File Path
                    file_path = None
                    if sku_record.print_file:
                        file_path = sku_record.print_file.file_path
                    elif sku_record.product and sku_record.product.print_file_id:
                        # Fallback to parent product's print file
                        # We need to load it if not available, but for now let's hope it's loaded 
                        # Or just use product.file_path_3mf as ultimate fallback
                        file_path = sku_record.product.file_path_3mf
                    
                    # Resolve Requirements
                    reqs = [{
                        "material": sku_record.product.required_filament_type if sku_record.product else "PLA",
                        "color": sku_record.hex_color or (sku_record.product.required_filament_color if sku_record.product else None)
                    }]
                    
                    for _ in range(item.quantity):
                        job = Job(
                            order_id=db_order.id,
                            gcode_path=file_path or "MISSING_FILE",
                            status=JobStatusEnum.PENDING,
                            filament_requirements=reqs
                        )
                        session.add(job)
                else:
                    # 2. Fallback to legacy Product lookup
                    stmt = select(Product).where(Product.sku == item.sku)
                    result = await session.exec(stmt)
                    product = result.first()
                    
                    if product:
                        logger.info(f"Found matching legacy Product for SKU {item.sku}. Creating {item.quantity} Job(s).")
                        
                        # Create one job per quantity
                        for _ in range(item.quantity):
                            # Determine requirements
                            reqs = [{
                                "material": product.required_filament_type,
                                "color": product.required_filament_color
                            }]
                            
                            # Basic variation parsing
                            if item.variation_aspects:
                                for aspect in item.variation_aspects:
                                    if aspect.name.lower() in ["color", "colour"]:
                                        reqs[0]["color"] = aspect.value
                                        break
                            
                            job = Job(
                                order_id=db_order.id,
                                gcode_path=product.file_path_3mf, # Using 3mf path as source
                                status=JobStatusEnum.PENDING,
                                filament_requirements=reqs
                            )
                            session.add(job)
                    else:
                        logger.warning(f"No Product or SKU found for SKU {item.sku}. No Job created.")
            
        await session.commit()
        logger.info(f"Order {ebay_order.order_id} processed successfully.")

# Singleton
order_processor = OrderProcessor()
