from typing import Optional
from sqlmodel import SQLModel, Field

class Filament(SQLModel, table=True):
    """
    Filament Model - Single Source of Truth for material properties.
    Critical for 3MF weight calculation and color matching.
    """
    __tablename__ = "filaments"

    id: Optional[int] = Field(default=None, primary_key=True)
    collection_id: str = Field(unique=True, index=True, description="e.g., PLA-MATTE-BLACK")
    brand: str
    material: str  # e.g., PLA, PETG, ASA
    color_hex: str  # Required for Delta E (e.g., #000000)
    color_name: str
    density: float  # g/cm³
    diameter: float = Field(default=1.75)
    price_per_kg: Optional[float] = None
