from typing import Optional, List
from pydantic import BaseModel
from .core import PrinterStatusEnum, PrinterTypeEnum

class AmsSlotRead(BaseModel):
    ams_index: int
    slot_index: int
    tray_color: Optional[str] = None
    tray_type: Optional[str] = None
    remaining_percent: Optional[int] = None

    class Config:
        from_attributes = True

class PrinterRead(BaseModel):
    serial: str
    name: str
    ip_address: Optional[str] = None
    type: PrinterTypeEnum
    current_status: PrinterStatusEnum
    current_temp_nozzle: float
    current_temp_bed: float
    current_progress: int
    remaining_time: int
    ams_slots: List[AmsSlotRead] = []

    class Config:
        from_attributes = True
