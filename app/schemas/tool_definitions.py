from typing import Optional
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import re

class PrinterActionEnum(str, Enum):
    PAUSE = "PAUSE"
    RESUME = "RESUME"
    STOP = "STOP"
    CLEAR_BED = "CLEAR_BED"

class PrinterActionRequest(BaseModel):
    """
    Arguments for executing a high-level operational command on a printer.
    """
    action: PrinterActionEnum = Field(
        ..., 
        description="The specific operational command to execute. 'STOP' is an emergency halt. 'CLEAR_BED' initiates the clearing sequence and requires the printer to be in a safe state."
    )
    force: bool = Field(
        False, 
        description="If True, overrides safety checks (e.g. state locks). Use with extreme caution only if standard commands fail."
    )

class ProductionJobRequest(BaseModel):
    """
    Arguments for queuing a new production job.
    """
    file_id: int = Field(
        ..., 
        description="The unique identifier of the PrintFile asset to be printed."
    )
    material_color: str = Field(
        ..., 
        description="The mandatory filament color requirements in Hex format (e.g., #FF0000). Must match a loaded spool."
    )
    priority: int = Field(
        0, 
        description="Priority level (0-100). Higher values are processed first."
    )

    @field_validator('material_color')
    @classmethod
    def validate_hex_color(cls, v: str) -> str:
        if not re.match(r"^#(?:[0-9a-fA-F]{3}){1,2}$", v):
             raise ValueError("material_color must be a valid Hex code (e.g., #FF0000)")
        return v.upper()
