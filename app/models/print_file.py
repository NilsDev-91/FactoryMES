from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Column, DateTime
from sqlmodel import SQLModel, Field
import os

class PrintFile(SQLModel, table=True):
    """
    PrintFile represents a 3D model file (e.g. .3mf) stored on disk.
    
    The file_path is the internal UUID-based storage path (for collision avoidance), 
    while original_filename is for UI presentation.
    """
    __tablename__ = "print_files"

    id: Optional[int] = Field(default=None, primary_key=True)
    
    # Internal path, e.g., storage/3mf/uuid-filename.3mf
    file_path: str = Field(unique=True, index=True)
    
    # User-friendly name, e.g., "Benchy.3mf"
    # Required for new uploads, but nullable for existing records to prevent migration issues.
    original_filename: Optional[str] = Field(default=None, nullable=True)
    
    upload_timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )

    @property
    def display_name(self) -> str:
        """
        Computed property for UI presentation.
        Returns original_filename if available, otherwise falls back 
        to the basename of the internal file_path.
        """
        if self.original_filename:
            return self.original_filename
        
        return os.path.basename(self.file_path)
