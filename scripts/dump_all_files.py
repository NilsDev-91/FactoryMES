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
        print(f"Total PrintFiles: {len(results)}")
        for p in results:
            print(f"{p.id}: {p.original_filename} -> {p.file_path}")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(dump_all_files())
