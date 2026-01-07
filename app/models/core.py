
from typing import Optional, List, Any, Dict, TYPE_CHECKING
from datetime import datetime, timezone
import uuid
from sqlalchemy import JSON, Column, DateTime
from sqlmodel import SQLModel, Field, Relationship, JSON
from enum import Enum
if TYPE_CHECKING:
    from app.models.filament import AmsSlot, FilamentProfile
    from app.models.product_sku import ProductSKU
    from app.models.print_file import PrintFile

class PlatformEnum(str, Enum):
    ETSY = "ETSY"
    EBAY = "EBAY"

class PrinterTypeEnum(str, Enum):
    P1S = "P1S"
    A1 = "A1"
    X1C = "X1C"
    P1P = "P1P"
    A1_MINI = "A1 Mini"
    X1E = "X1E"



class ClearingStrategyEnum(str, Enum):
    MANUAL = "MANUAL"
    A1_GANTRY_SWEEP = "A1_GANTRY_SWEEP"       # X-Axis Ram for parts ≥38mm
    A1_TOOLHEAD_PUSH = "A1_TOOLHEAD_PUSH"     # Nozzle Ram for parts <38mm
    X1_MECHANICAL_SWEEP = "X1_MECHANICAL_SWEEP"



# Legacy Order removed, moved to app.models.order

# --- Redundant Models Commented Out to resolve SQLModel metadata conflicts ---
# Use app.models.printer.Printer and app.models.job.PrintJob instead

# class Printer(SQLModel, table=True):
#     __tablename__ = "printers"
# ...
# class Job(SQLModel, table=True):
#     __tablename__ = "jobs"
# ...

# ProductRequirement commented out to resolve foreign key conflicts with deleted FilamentProfile
# class ProductRequirement(SQLModel, table=True):
#     """
#     Links a ProductSKU to a specific FilamentProfile requirement.
#     """
#     __tablename__ = "product_requirements"
# 
#     id: Optional[int] = Field(default=None, primary_key=True)
#     product_sku_id: int = Field(foreign_key="product_skus.id")
#     filament_profile_id: uuid.UUID = Field(foreign_key="filament_profiles.id")
# ...

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
    filament_requirements: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON)

    # Phase 6: Continuous Printing (Automation Safety)
    part_height_mm: Optional[float] = Field(
        default=None, 
        description="Part height in mm. Required for Gantry Sweep safety (min 50mm)."
    )
    is_continuous_printing: bool = Field(
        default=False,
        description="Enable automatic bed clearing via Gantry Sweep. Requires part_height_mm >= 50mm."
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    print_file: Optional["PrintFile"] = Relationship()
    variants: List["ProductSKU"] = Relationship(back_populates="product", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

# ProductVariant removed, moved to app.models.product_sku as ProductSKU
