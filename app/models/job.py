from typing import Optional
from datetime import datetime
from enum import Enum
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field

class JobStatus(str, Enum):
    PENDING = "PENDING"
    UPLOADING = "UPLOADING"
    PRINTING = "PRINTING"
    SUCCESS = "SUCCESS"
    FINISHED = "FINISHED"  # Alias for SUCCESS
    BED_CLEARING = "BED_CLEARING"
    NEEDS_CLEARING = "NEEDS_CLEARING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class PrintJob(SQLModel, table=True):
    """
    PrintJob Model - Tracking the lifecycle of a single print task.
    """
    __tablename__ = "print_jobs"

    id: Optional[int] = Field(default=None, primary_key=True)
    file_path: str
    printer_id: Optional[str] = Field(default=None, foreign_key="printers.serial")
    status: JobStatus = Field(default=JobStatus.PENDING)
    
    # Requirements
    required_material: str  # e.g., "PLA"
    required_color_hex: Optional[str] = None
    
    # Execution Tracking
    used_ams_slot: Optional[int] = Field(default=None)  # 0-3, or None for External
    
    started_at: Optional[datetime] = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    finished_at: Optional[datetime] = Field(
        default=None, 
        sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

class JobRead(PrintJob):
    pass

class JobCreate(PrintJob):
    pass
