import asyncio
import os
import sys
from pathlib import Path
import zipfile

# Add project root
sys.path.append(".")

from app.services.logic.file_processor import FileProcessorService

async def test_sanitization():
    source = Path("storage/3mf/2feceedf-9dc7-4a65-8650-c76b99782f3a.3mf")
    print(f"Testing sanitization on: {source}")
    print(f"File exists: {source.exists()}")
    print(f"File size: {os.path.getsize(source)}")
    
    try:
        with zipfile.ZipFile(source, 'r') as z:
            print("Zip check: Success")
            print("Files in zip:", z.namelist()[:5])
    except Exception as e:
        print(f"Zip check: FAILED - {e}")

    processor = FileProcessorService()
    try:
        print("\nRunning sanitize_and_repack...")
        result = await processor.sanitize_and_repack(source, target_index=3, printer_type="A1")
        print(f"Sanitization Success: {result}")
        if result.exists():
            result.unlink()
    except Exception as e:
        print(f"Sanitization FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_sanitization())
