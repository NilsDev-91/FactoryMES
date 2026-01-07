from typing import Optional, Any, Dict, List
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field, JSON

class PrinterState(str, Enum):
    IDLE = "IDLE"
    PRINTING = "PRINTING"
    PAUSED = "PAUSED"
    COOLDOWN = "COOLDOWN"
    CLEARING_BED = "CLEARING_BED"
    AWAITING_CLEARANCE = "AWAITING_CLEARANCE"
    OFFLINE = "OFFLINE"
    ERROR = "ERROR"

class Printer(SQLModel, table=True):
    """
    Printer Model - Core hardware state representation.
    Supports a Single AMS (4 slots) or an External Spool via JSON config.
    """
    __tablename__ = "printers"

    serial: str = Field(primary_key=True)
    name: Optional[str] = None
    model: str = Field(description='e.g., "A1", "X1C"')
    ip_address: str
    access_code: str
    current_state: PrinterState = Field(default=PrinterState.IDLE)
    
    # Store either {"0": {...}, "1": ...} for AMS OR {"external": {...}} for 5kg spool
    ams_config: Dict[str, Any] = Field(default_factory=dict, sa_type=JSON)
    
    supports_auto_eject: bool = Field(default=False)
    last_seen: Optional[datetime] = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )

class PrinterRead(Printer):
    # Dynamic fields merged from Redis
    status: Optional[str] = "OFFLINE"
    progress: int = 0
    remaining_time_min: int = 0
    nozzle_temp: float = 0.0
    bed_temp: float = 0.0
    active_file: Optional[str] = None
    is_online: bool = False
    temps: Dict[str, float] = Field(default_factory=dict)
    ams: List[Dict[str, Any]] = Field(default_factory=list)
