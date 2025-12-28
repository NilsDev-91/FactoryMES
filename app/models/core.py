
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime
from sqlalchemy import JSON, Column
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
if TYPE_CHECKING:
    from app.models.filament import AmsSlot

class PlatformEnum(str, Enum):
    ETSY = "ETSY"
    EBAY = "EBAY"

class OrderStatusEnum(str, Enum):
    OPEN = "OPEN"
    QUEUED = "QUEUED"
    PRINTING = "PRINTING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"

class PrinterTypeEnum(str, Enum):
    P1S = "P1S"
    A1 = "A1"
    X1C = "X1C"
    P1P = "P1P"
    A1_MINI = "A1 Mini"

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

# Legacy Order removed, moved to app.models.order

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
    
    current_progress: int = Field(default=0) # Percentage 0-100
    remaining_time: int = Field(default=0) # Minutes
    
    # Stores AMS state as JSON
    # Example: [{"slot": 0, "type": "PLA", "color": "#FF0000", "remaining": 100}, ...]
    ams_data: List[dict] = Field(default=[], sa_column=Column(JSON))
    
    jobs: List["Job"] = Relationship(back_populates="assigned_printer")
    ams_slots: List["AmsSlot"] = Relationship(back_populates="printer")

class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    assigned_printer_serial: Optional[str] = Field(default=None, foreign_key="printers.serial")
    gcode_path: str
    status: JobStatusEnum = Field(default=JobStatusEnum.PENDING)
    error_message: Optional[str] = None
    
    # Requirements derived from Product/Variation
    filament_requirements: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(default_factory=datetime.now)

    order: Optional["Order"] = Relationship(back_populates="jobs")
    assigned_printer: Optional[Printer] = Relationship(back_populates="jobs")

class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: str = Field(unique=True, index=True)
    description: Optional[str] = None
    file_path_3mf: str
    
    # Material Requirements
    required_filament_type: str = Field(default="PLA") # e.g. PLA, PETG, ABS
    required_filament_color: Optional[str] = Field(default=None) # Hex Code or Name, e.g. "#FF0000"

    created_at: datetime = Field(default_factory=datetime.now)
