import logging
import asyncio
from typing import List, Optional
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_session
from app.core.config import settings
from app.models import PrintJob as Job, Product, JobStatusEnum, ProductRequirement
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
            logger.debug("OrderProcessor heartbeat...")
            try:
                # 1. Fetch from eBay
                await self.sync_ebay_orders()
                # 2. Sync from local DB (Manual/Simplified simulations)
                await self.sync_local_orders()
            except Exception as e:
                logger.error(f"Error in OrderProcessor loop: {e}", exc_info=True)
            
            await asyncio.sleep(15) # Shorter loop for responsiveness

    async def sync_ebay_orders(self):
        """Fetches new orders from eBay API."""
        logger.debug("Syncing eBay orders via API...")
        try:
            new_orders = await ebay_orders.fetch_orders()
        except Exception as e:
            logger.error(f"Failed to fetch eBay orders: {e}")
            return

        if not new_orders:
            return

        async for session in get_session():
            for ebay_order in new_orders:
                # Deduplication
                stmt = select(Order).where(Order.ebay_order_id == ebay_order.order_id)
                result = await session.exec(stmt)
                if result.first():
                    continue
                
                try:
                    await self.process_ebay_order(session, ebay_order)
                except Exception as e:
                    logger.error(f"Failed to process eBay order {ebay_order.order_id}: {e}", exc_info=True)

    async def sync_local_orders(self):
        """Processes PENDING orders in the DB that have no Jobs yet."""
        async for session in get_session():
            # Find Orders with status PENDING
            # We filter for those without jobs in convert_order_to_jobs to be safe
            stmt = (
                select(Order)
                .where(Order.status == "PENDING")
                .options(selectinload(Order.items), selectinload(Order.jobs))
            )
            result = await session.exec(stmt)
            orders = result.all()
            
            for order in orders:
                if not order.jobs:
                    logger.info(f"Auto-processing internal Order {order.ebay_order_id}")
                    try:
                        await self.convert_order_to_jobs(session, order)
                        await session.commit()
                    except Exception as e:
                        logger.error(f"Failed to auto-process Order {order.id}: {e}")
                        await session.rollback()

    async def process_ebay_order(self, session: AsyncSession, ebay_order: EbayOrder):
        """Converts an EbayOrder object to a DB Order and then to Jobs."""
        logger.info(f"Ingesting eBay order: {ebay_order.order_id}")
        
        db_order = Order(
            ebay_order_id=ebay_order.order_id,
            buyer_username=ebay_order.buyer.username,
            total_price=float(ebay_order.pricing_summary.total.value),
            currency=ebay_order.pricing_summary.total.currency,
            status=ebay_order.order_fulfillment_status,
            created_at=ebay_order.creation_date
        )
        session.add(db_order)
        await session.flush()
        
        for item in ebay_order.line_items:
            db_item = OrderItem(
                order_id=db_order.id,
                sku=item.sku or "UNKNOWN",
                title=item.title,
                quantity=item.quantity,
                variation_details=str(item.variation_aspects) if item.variation_aspects else None
            )
            session.add(db_item)
        
        await session.commit()
        await session.refresh(db_order, ["items", "jobs"]) # Ensure relations are ready
        
        # Now convert to jobs
        await self.convert_order_to_jobs(session, db_order)
        await session.commit()

    async def convert_order_to_jobs(self, session: AsyncSession, order: Order):
        """The core 'Brain' that maps OrderItems to G-code and creates Jobs."""
        logger.info(f"Converting Order {order.id} to Jobs...")
        
        # Ensure items are loaded
        if not order.items:
            # Re-fetch with items if needed
            stmt = select(Order).where(Order.id == order.id).options(selectinload(Order.items))
            order = (await session.exec(stmt)).first()

        for item in order.items:
            # Match Product/SKU
            if item.sku:
                # 1. Master-Variant Lookup
                sku_stmt = (
                    select(ProductSKU)
                    .where(ProductSKU.sku == item.sku)
                    .options(
                        selectinload(ProductSKU.print_file), 
                        selectinload(ProductSKU.product).selectinload(Product.print_file),
                        selectinload(ProductSKU.requirements).selectinload(ProductRequirement.filament_profile)
                    )
                )
                sku_record = (await session.exec(sku_stmt)).first()
                
                if sku_record:
                    # Resolve File
                    file_path = None
                    if sku_record.print_file:
                        file_path = sku_record.print_file.file_path
                    elif sku_record.product and sku_record.product.print_file:
                        file_path = sku_record.product.print_file.file_path
                    
                    # Resolve Req (Priority: Requirements Table -> SKU Fields -> Product Fields)
                    reqs = []
                    if sku_record.requirements:
                        for r in sku_record.requirements:
                            reqs.append({
                                "material": r.material,
                                "color": r.color_hex
                            })
                    else:
                        reqs = [{
                            "material": sku_record.product.required_filament_type if sku_record.product else "PLA",
                            "color": sku_record.hex_color or (sku_record.product.required_filament_color if sku_record.product else None)
                        }]
                    
                    for _ in range(item.quantity):
                        job = Job(
                            order_id=order.id,
                            gcode_path=file_path or "MISSING_FILE",
                            status=JobStatusEnum.PENDING,
                            filament_requirements=reqs,
                            job_metadata={
                                "part_height_mm": sku_record.product.part_height_mm if sku_record.product else 0,
                                "is_continuous": sku_record.product.is_continuous_printing if sku_record.product else False
                            }
                        )
                        session.add(job)
                else:
                    # 2. Legacy Product Fallback
                    stmt = select(Product).where(Product.sku == item.sku)
                    product = (await session.exec(stmt)).first()
                    
                    if product:
                        for _ in range(item.quantity):
                            reqs = [{
                                "material": product.required_filament_type,
                                "color": product.required_filament_color
                            }]
                            # Simple variation parsing if it was manual
                            # (variation_details is a string representation of list of aspects)
                            
                            job = Job(
                                order_id=order.id,
                                gcode_path=product.file_path_3mf,
                                status=JobStatusEnum.PENDING,
                                filament_requirements=reqs,
                                job_metadata={
                                    "part_height_mm": product.part_height_mm,
                                    "is_continuous": product.is_continuous_printing
                                }
                            )
                            session.add(job)
                    else:
                        logger.warning(f"No Product/SKU found for {item.sku}. Skipping.")
            
        await session.commit()
        logger.info(f"Order {order.ebay_order_id} processed successfully.")

# Singleton
order_processor = OrderProcessor()
