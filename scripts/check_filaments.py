import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select
from app.models.filament import FilamentProfile

async def check_filaments():
    async with async_session_maker() as session:
        stmt = select(FilamentProfile)
        result = await session.exec(stmt)
        filaments = result.all()
        
        print("🧵 Current Filament Profiles:")
        for f in filaments:
            print(f"   - {f.material} | {f.color_hex} | Name: {f.color_name} | ID: {f.id}")

if __name__ == "__main__":
    asyncio.run(check_filaments())
