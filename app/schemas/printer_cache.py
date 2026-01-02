import time
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field
from app.models.core import PrinterStatusEnum

class AMSSlotCache(BaseModel):
    """Lightweight AMS state for cache."""
    slot_id: int
    color: Optional[str] = None
    material: Optional[str] = None

class PrinterStateCache(BaseModel):
    """
    Represents the ephemeral "Hot State" of a printer in Redis.
    Serialized from MQTT telemetry with strict Pydantic v2 validation.
    """
    serial: str
    status: PrinterStatusEnum
    temps: Dict[str, float] = Field(description="e.g., {'nozzle': 220.0, 'bed': 60.0}")
    progress: int = Field(ge=0, le=100)
    remaining_time_min: int
    active_file: Optional[str] = None
    ams: List[AMSSlotCache] = Field(default_factory=list)
    updated_at: float = Field(default_factory=time.time)

    @property
    def is_stale(self) -> bool:
        """Checks if the data is older than 60 seconds."""
        return (time.time() - self.updated_at) > 60

    class Config:
        from_attributes = True
