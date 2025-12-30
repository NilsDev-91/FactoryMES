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

class PrinterCreate(BaseModel):
    serial: str
    name: str
    ip_address: str
    access_code: str
    type: PrinterTypeEnum

class PrinterUpdate(BaseModel):
    name: Optional[str] = None
    ip_address: Optional[str] = None
    access_code: Optional[str] = None
    type: Optional[PrinterTypeEnum] = None
    current_status: Optional[PrinterStatusEnum] = None
    current_temp_nozzle: Optional[float] = None
    current_temp_bed: Optional[float] = None
    current_progress: Optional[int] = None

