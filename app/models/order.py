from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ebay_order_id: str = Field(unique=True, index=True)
    buyer_username: str
    total_price: float
    currency: str
    status: str
    created_at: datetime = Field(default_factory=datetime.now)
    
    items: List["OrderItem"] = Relationship(back_populates="order", sa_relationship_kwargs={"cascade": "all, delete-orphan"})
    jobs: List["Job"] = Relationship(back_populates="order")

class OrderItem(SQLModel, table=True):
    __tablename__ = "order_items"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    sku: str
    title: str
    quantity: int
    variation_details: Optional[str] = None # Stores color/material details

    order: Optional["Order"] = Relationship(back_populates="items")

class OrderItemRead(SQLModel):
    id: int
    order_id: int
    sku: str
    title: str
    quantity: int
    variation_details: Optional[str] = None

class OrderRead(SQLModel):
    id: int
    ebay_order_id: str
    buyer_username: str
    total_price: float
    currency: str
    status: str
    created_at: datetime
    items: List[OrderItemRead] = []

# Relationship to Job is handled via string reference
