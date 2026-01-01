import asyncio
import os
import sys
from sqlmodel import select

# Add project root
sys.path.append(".")

from app.core.database import async_session_maker
from app.models.print_file import PrintFile

async def find_zylinder_file():
    async with async_session_maker() as session:
        stmt = select(PrintFile).where(PrintFile.original_filename.like("%zylinder%"))
        results = (await session.exec(stmt)).all()
        if not results:
            print("No zylinder files found in PrintFile table.")
            # Let's list all files just in case
            stmt_all = select(PrintFile).limit(20)
            results_all = (await session.exec(stmt_all)).all()
            print("\nRecent PrintFiles:")
            for p in results_all:
                print(f"{p.id}: {p.original_filename} ({p.file_path})")
        else:
            for p in results:
                print(f"ID {p.id}: {p.original_filename} ({p.file_path})")

if __name__ == "__main__":
    if os.name == 'nt':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(find_zylinder_file())
