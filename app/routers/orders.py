from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List
from datetime import datetime

from sqlalchemy.orm import selectinload
from app.core.database import get_session
from app.models.core import Product
from app.models.order import Order, OrderItem, OrderRead

router = APIRouter(prefix="/orders", tags=["Orders"])

@router.get("", response_model=List[OrderRead])
async def get_orders(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Order).options(selectinload(Order.items), selectinload(Order.jobs)).order_by(Order.created_at.desc()))
    return result.scalars().all()

@router.post("", response_model=Order)
async def create_order(order: Order, session: AsyncSession = Depends(get_session)):
    try:
        # Check for duplicate ebay_order_id
        result = await session.execute(select(Order).where(Order.ebay_order_id == order.ebay_order_id))
        existing_order = result.scalars().first()
        
        if existing_order:
            raise HTTPException(status_code=400, detail=f"Order with ID {order.ebay_order_id} already exists.")

        session.add(order)
        await session.commit()
        await session.refresh(order)

        return order
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")
