import os
import uuid
import aiofiles
from datetime import datetime
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.models.print_file import PrintFile

# DTO for the response
class PrintFileUploadResponse(BaseModel):
    id: int
    original_filename: str
    upload_timestamp: datetime

async def upload_print_file(file: UploadFile, session: AsyncSession) -> PrintFileUploadResponse:
    """
    Handles the asynchronous upload of a 3D print file.
    1. Generates a unique storage path using UUID.
    2. Writes the file to disk chunk-by-chunk using aiofiles.
    3. Creates a PrintFile record in the database.
    """
    # 1. Extraction and Generation
    original_name = file.filename or "unknown_file"
    file_id = str(uuid.uuid4())
    filename = f"{file_id}.3mf"
    
    storage_dir = os.path.join("storage", "3mf")
    os.makedirs(storage_dir, exist_ok=True)
    
    target_path = os.path.join(storage_dir, filename)
    
    # 2. Async Writing (Strict Async Purity)
    async with aiofiles.open(target_path, 'wb') as out_file:
        while content := await file.read(1024 * 1024):  # 1MB chunks
            await out_file.write(content)
            
    # 3. Database Transaction
    db_file = PrintFile(
        file_path=target_path.replace("\\", "/"), # Use forward slashes for cross-platform consistency
        original_filename=original_name
    )
    
    session.add(db_file)
    await session.commit()
    await session.refresh(db_file)
    
    # 4. Return DTO
    return PrintFileUploadResponse(
        id=db_file.id,
        original_filename=db_file.original_filename or original_name,
        upload_timestamp=db_file.upload_timestamp
    )
