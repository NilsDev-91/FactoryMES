import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.print_file import PrintFile

async def file_audit():
    content = ["--- FILE AUDIT ---"]
    async with async_session_maker() as session:
        files = (await session.exec(select(PrintFile))).all()
        for f in files:
            content.append(f"ID: {f.id} | Name: {f.original_filename} | Path: {f.file_path}")

    with open("audit_files.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(content))
    print("Audit written to audit_files.txt")

if __name__ == "__main__":
    asyncio.run(file_audit())
