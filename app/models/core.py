
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON, Column, DateTime
from sqlmodel import SQLModel, Field, Relationship
from enum import Enum
if TYPE_CHECKING:
    from app.models.filament import AmsSlot, FilamentProfile
    from app.models.product_sku import ProductSKU
    from app.models.print_file import PrintFile

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
    AWAITING_CLEARANCE = "AWAITING_CLEARANCE"
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
    is_plate_cleared: bool = Field(default=True)
    
    current_progress: int = Field(default=0) # Percentage 0-100
    remaining_time: int = Field(default=0) # Minutes
    
    # Stores AMS state as JSON
    # Example: [{"slot": 0, "type": "PLA", "color": "#FF0000", "remaining": 100}, ...]
    ams_data: List[dict] = Field(default=[], sa_column=Column(JSON))
    
    current_job_id: Optional[int] = Field(default=None)

    jobs: List["Job"] = Relationship(back_populates="assigned_printer")
    ams_slots: List["AmsSlot"] = Relationship(back_populates="printer")

class Job(SQLModel, table=True):
    __tablename__ = "jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    assigned_printer_serial: Optional[str] = Field(default=None, foreign_key="printers.serial")
    gcode_path: str
    status: JobStatusEnum = Field(default=JobStatusEnum.PENDING)
    priority: int = Field(default=0, index=True)
    error_message: Optional[str] = None
    
    # Requirements derived from Product/Variation
    filament_requirements: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    order: Optional["Order"] = Relationship(back_populates="jobs")
    assigned_printer: Optional[Printer] = Relationship(back_populates="jobs")

class ProductRequirement(SQLModel, table=True):
    """
    Links a ProductSKU to a specific FilamentProfile requirement.
    """
    __tablename__ = "product_requirements"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_sku_id: int = Field(foreign_key="product_skus.id")
    filament_profile_id: uuid.UUID = Field(foreign_key="filament_profiles.id")

    product_sku: Optional["ProductSKU"] = Relationship(back_populates="requirements")
    filament_profile: Optional["FilamentProfile"] = Relationship()

    @property
    def material(self) -> str:
        return self.filament_profile.material if self.filament_profile else "Unknown"

    @property
    def color_hex(self) -> str:
        return self.filament_profile.color_hex if self.filament_profile else "#000000"

    @property
    def brand(self) -> str:
        return self.filament_profile.brand if self.filament_profile else "Generic"

class Product(SQLModel, table=True):
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    sku: Optional[str] = Field(default=None, unique=True, index=True)
    description: Optional[str] = None
    is_catalog_visible: bool = Field(default=True)
    
    # DEPRECATED: Use print_file relationship
    file_path_3mf: str = Field(default="")
    
    # New: Single Source of Truth for assets
    print_file_id: Optional[int] = Field(default=None, foreign_key="print_files.id")

    # Material Requirements
    required_filament_type: str = Field(default="PLA") # e.g. PLA, PETG, ABS
    required_filament_color: Optional[str] = Field(default=None) # Hex Code or Name, e.g. "#FF0000"
    
    # New: JSON Requirements for multi-color/master slicing
    filament_requirements: Optional[List[dict]] = Field(default=None, sa_column=Column(JSON))

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    print_file: Optional["PrintFile"] = Relationship()
    variants: List["ProductSKU"] = Relationship(back_populates="product", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

# ProductVariant removed, moved to app.models.product_sku as ProductSKU
