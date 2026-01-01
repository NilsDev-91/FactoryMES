"""
Product Schemas with Phase 6 Safety Validation.
Enforces the 50mm minimum height for Continuous Printing (Gantry Sweep).
"""
from typing import Optional, List
from pydantic import BaseModel, model_validator


# Minimum height for safe Gantry Sweep operation
MIN_GANTRY_SWEEP_HEIGHT_MM = 50.0


class ProductBase(BaseModel):
    """Base schema shared by Create/Update/Read."""
    name: str
    sku: Optional[str] = None
    description: Optional[str] = None
    is_catalog_visible: bool = True
    print_file_id: Optional[int] = None
    required_filament_type: str = "PLA"
    required_filament_color: Optional[str] = None
    
    # Phase 6: Continuous Printing fields
    part_height_mm: Optional[float] = None
    is_continuous_printing: bool = False


class ProductCreate(ProductBase):
    """Schema for creating a new product."""
    generate_variants_for_profile_ids: List[str] = []
    
    @model_validator(mode='after')
    def validate_safety_constraints(self):
        """
        Enforce: Continuous Printing requires part_height_mm >= 50mm.
        This mirrors the A1SmartSweepStrategy.MIN_SWEEP_HEIGHT_MM constraint.
        """
        if self.is_continuous_printing:
            if self.part_height_mm is None:
                raise ValueError(
                    "Safety Violation: Continuous Printing requires a part height to be specified."
                )
            if self.part_height_mm < MIN_GANTRY_SWEEP_HEIGHT_MM:
                raise ValueError(
                    f"Safety Violation: Continuous Printing requires a part height of at least "
                    f"{MIN_GANTRY_SWEEP_HEIGHT_MM}mm due to A1 gantry geometry."
                )
        return self


class ProductUpdate(BaseModel):
    """Schema for updating an existing product (all fields optional)."""
    name: Optional[str] = None
    sku: Optional[str] = None
    description: Optional[str] = None
    is_catalog_visible: Optional[bool] = None
    print_file_id: Optional[int] = None
    required_filament_type: Optional[str] = None
    required_filament_color: Optional[str] = None
    
    # Phase 6: Continuous Printing fields
    part_height_mm: Optional[float] = None
    is_continuous_printing: Optional[bool] = None
    
    @model_validator(mode='after')
    def validate_safety_constraints(self):
        """
        Enforce safety on update only if is_continuous_printing is being set to True.
        """
        if self.is_continuous_printing is True:
            if self.part_height_mm is None:
                raise ValueError(
                    "Safety Violation: Continuous Printing requires a part height to be specified."
                )
            if self.part_height_mm < MIN_GANTRY_SWEEP_HEIGHT_MM:
                raise ValueError(
                    f"Safety Violation: Continuous Printing requires a part height of at least "
                    f"{MIN_GANTRY_SWEEP_HEIGHT_MM}mm due to A1 gantry geometry."
                )
        return self


class ProductRead(ProductBase):
    """Schema for reading a product (includes id and timestamps)."""
    id: int
    file_path_3mf: str = ""  # Legacy field
    
    class Config:
        from_attributes = True
