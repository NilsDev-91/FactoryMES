from typing import Optional, List, Any
from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, DateTime

class OrderStatusEnum(str, Enum):
    OPEN = "OPEN"
    QUEUED = "QUEUED"
    PRINTING = "PRINTING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    ebay_order_id: str = Field(unique=True, index=True)
    buyer_username: str
    total_price: float
    currency: str
    status: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
    
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
    jobs: List["JobRead"] = []

class JobRead(SQLModel):
    id: int
    status: str
    filament_requirements: Optional[Any] = None
    gcode_path: str
    assigned_printer_serial: Optional[str] = None
    job_metadata: Optional[dict] = {}

# Relationship to Job is handled via string reference
