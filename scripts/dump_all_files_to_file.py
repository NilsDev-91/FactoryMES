import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.print_file import PrintFile

async def dump_all_files():
    async with async_session_maker() as session:
        stmt = select(PrintFile)
        results = (await session.exec(stmt)).all()
        with open("all_print_files.txt", "w", encoding="utf-8") as f:
            f.write(f"Total PrintFiles: {len(results)}\n")
            for p in results:
                f.write(f"{p.id}: {p.original_filename} -> {p.file_path}\n")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(dump_all_files())
