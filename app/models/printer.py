from typing import Optional, List, Dict
from pydantic import BaseModel
from .core import PrinterStatusEnum, PrinterTypeEnum, ClearingStrategyEnum
from .order import JobRead
from app.schemas.printer_cache import AMSSlotCache

class AmsSlotRead(BaseModel):
    ams_index: int
    slot_index: int
    slot_id: int
    color_hex: Optional[str] = None
    material: Optional[str] = None
    remaining_percent: Optional[int] = None

    class Config:
        from_attributes = True

class PrinterRead(BaseModel):
    serial: str
    name: str
    ip_address: Optional[str] = None
    type: PrinterTypeEnum
    status: PrinterStatusEnum # Renamed from current_status
    temps: Dict[str, float] = {"nozzle": 0.0, "bed": 0.0}
    nozzle_temp: float = 0.0
    bed_temp: float = 0.0
    progress: int = 0
    remaining_time_min: int = 0
    active_file: Optional[str] = None
    is_online: bool = False
    is_plate_cleared: bool
    
    # Legacy fields (for backward compatibility if needed, otherwise remove)
    current_temp_nozzle: float = 0.0
    current_temp_bed: float = 0.0
    current_progress: int = 0
    remaining_time: int = 0
    
    # NEW FIELDS:
    hardware_model: Optional[str] = "GENERIC"
    can_auto_eject: bool
    clearing_strategy: ClearingStrategyEnum
    thermal_release_temp: float
    jobs_since_calibration: int
    calibration_interval: int
    ams: List[AMSSlotCache] = []
    ams_slots: List[AmsSlotRead] = [] # Keeping DB relationship separate
    last_job: Optional["JobRead"] = None

    class Config:
        from_attributes = True
        populate_by_name = True

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
    jobs_since_calibration: Optional[int] = None
    calibration_interval: Optional[int] = None


class AutomationConfigUpdate(BaseModel):
    """Schema for updating automation configuration on a printer."""
    can_auto_eject: Optional[bool] = None
    thermal_release_temp: Optional[float] = None
    clearing_strategy: Optional[ClearingStrategyEnum] = None

