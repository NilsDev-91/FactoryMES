from typing import Optional, List, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
import uuid

if TYPE_CHECKING:
    from app.models.core import Printer

class FilamentProfile(SQLModel, table=True):
    __tablename__ = "filament_profiles"
    
    id: Optional[uuid.UUID] = Field(default_factory=uuid.uuid4, primary_key=True)
    brand: str
    material: str # e.g. "PLA"
    color_hex: str # e.g. "FF0000"
    color_name: Optional[str] = Field(default=None, description="Human readable color name, e.g. 'Red'")
    density: float # g/cm3
    spool_weight: float # grams

class AmsSlot(SQLModel, table=True):
    __tablename__ = "ams_slots"
    __table_args__ = (
        UniqueConstraint("printer_id", "ams_index", "slot_index", name="unique_ams_slot"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    printer_id: str = Field(foreign_key="printers.serial")
    ams_index: int # 0-3
    slot_index: int # 0-3
    slot_id: int # 0-15 (Flat index for dispatcher)
    color_hex: str # Hex code, e.g. "FF0000FF"
    color_name: Optional[str] = None # Human readable name
    material: str # e.g. "PLA"
    remaining_percent: Optional[int] = None

    printer: Optional["Printer"] = Relationship(back_populates="ams_slots")
