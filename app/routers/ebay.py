from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from app.core.database import get_session
from app.services.ebay.orders import ebay_orders
from app.models.order import Order, OrderItem

router = APIRouter(prefix="/ebay", tags=["eBay"])

@router.post("/sync")
async def sync_ebay_orders(session: AsyncSession = Depends(get_session)):
    """
    Fetches latest orders from eBay and persists them into the database.
    """
    try:
        # 1. Fetch orders from eBay API
        ebay_orders_list = await ebay_orders.fetch_orders(limit=20)
        new_orders_count = 0
        
        for ebay_order in ebay_orders_list:
            # 2. Check if order already exists
            statement = select(Order).where(Order.ebay_order_id == ebay_order.order_id)
            result = await session.execute(statement)
            existing_order = result.scalar_one_or_none()
            
            if not existing_order:
                # 3. Create new Order
                new_order = Order(
                    ebay_order_id=ebay_order.order_id,
                    buyer_username=ebay_order.buyer.username,
                    total_price=0.0, # You might want to calculate this from line items if available
                    currency="USD",   # Default if not in EbayOrder model
                    status=ebay_order.order_payment_status,
                    created_at=ebay_order.creation_date
                )
                session.add(new_order)
                await session.flush() # Get ID for OrderItems
                
                # 4. Create OrderItems
                for item in ebay_order.line_items:
                    # Collect variation details
                    variations = []
                    for aspect in item.variation_aspects:
                        variations.append(f"{aspect.name}: {aspect.value}")
                    variation_str = ", ".join(variations) if variations else None
                    
                    new_item = OrderItem(
                        order_id=new_order.id,
                        sku=item.sku or "UNSET",
                        title=item.title,
                        quantity=item.quantity,
                        variation_details=variation_str
                    )
                    session.add(new_item)
                
                new_orders_count += 1
            else:
                # 5. Update existing order status if changed
                if existing_order.status != ebay_order.order_payment_status:
                    existing_order.status = ebay_order.order_payment_status
                    session.add(existing_order)

        # 6. Final commit
        await session.commit()
        return {"status": "success", "new_orders": new_orders_count}

    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"eBay sync failed: {str(e)}")
