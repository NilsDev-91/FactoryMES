from pydantic import BaseModel, Field

class PartMetadata(BaseModel):
    """
    Metadata about the part being printed, used for logic decisions 
    like automated bed clearing.
    """
    height_mm: float = Field(..., description="Z-height of the printed object")
    center_x: float = Field(128.0, description="X-center of the part bounding box (World Coordinates)")
    center_y: float = Field(128.0, description="Y-center of the part bounding box (World Coordinates)")
