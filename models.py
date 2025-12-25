
from typing import Optional, List
from datetime import datetime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum

class PlatformEnum(str, Enum):
    ETSY = "ETSY"
    EBAY = "EBAY"

class OrderStatusEnum(str, Enum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"

class PrinterTypeEnum(str, Enum):
    P1S = "P1S"
    A1 = "A1"
    X1C = "X1C"

class PrinterStatusEnum(str, Enum):
    IDLE = "IDLE"
    PRINTING = "PRINTING"
    OFFLINE = "OFFLINE"

class JobStatusEnum(str, Enum):
    PENDING = "PENDING"
    UPLOADING = "UPLOADING"
    PRINTING = "PRINTING"
    FINISHED = "FINISHED"
    FAILED = "FAILED"

class Order(SQLModel, table=True):
    __tablename__ = "orders"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    platform: PlatformEnum
    platform_order_id: str = Field(unique=True, index=True)
    sku: str
    quantity: int
    purchase_date: datetime
    status: OrderStatusEnum = Field(default=OrderStatusEnum.OPEN)
    
    jobs: List["Job"] = Relationship(back_populates="order")

class Printer(SQLModel, table=True):
    __tablename__ = "printers"

    serial: str = Field(primary_key=True)
    name: str
    ip_address: Optional[str] = None
    access_code: Optional[str] = None
    type: PrinterTypeEnum
    current_status: PrinterStatusEnum = Field(default=PrinterStatusEnum.IDLE)
    current_temp_nozzle: float = Field(default=0.0)
    current_temp_bed: float = Field(default=0.0)
    
    jobs: List["Job"] = Relationship(back_populates="assigned_printer")

class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    assigned_printer_serial: Optional[str] = Field(default=None, foreign_key="printers.serial")
    gcode_path: str
    status: JobStatusEnum = Field(default=JobStatusEnum.PENDING)
    created_at: datetime = Field(default_factory=datetime.now)

    order: Optional[Order] = Relationship(back_populates="jobs")
    assigned_printer: Optional[Printer] = Relationship(back_populates="jobs")

class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: str = Field(unique=True, index=True)
    description: Optional[str] = None
    file_path_3mf: str
    created_at: datetime = Field(default_factory=datetime.now)
