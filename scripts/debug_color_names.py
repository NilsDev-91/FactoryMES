
import asyncio
import logging
from typing import Tuple, Optional
from sqlmodel import select
from app.core.database import async_session_maker
from app.models.filament import FilamentProfile
from app.services.logic.color_matcher import color_matcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DebugMatch")

def normalize_hex(h: str) -> str:
    if not h: return ""
    return h.lstrip("#")[:6].upper()

async def test_match():
    async with async_session_maker() as session:
        # Load profiles
        profiles_res = await session.execute(select(FilamentProfile))
        profiles = list(profiles_res.scalars().all())
        
        test_cases = [
            ("PLA", "#000000FF"),
            ("PLA", "#FF0000FF"),
            ("PLA", "#FFFFFFBB"),
        ]
        
        for material, slot_hex in test_cases:
            norm_hex = normalize_hex(slot_hex)
            print(f"Testing: {material} {slot_hex} (Normalized: {norm_hex})")
            
            match = next((p for p in profiles if p.material == material and normalize_hex(p.color_hex) == norm_hex), None)
            
            if match:
                print(f"  MATCH FOUND: {match.color_name} (Profile Hex: {match.color_hex})")
            else:
                print(f"  NO MATCH FOUND in {len(profiles)} profiles.")
                for p in profiles:
                    if p.material == material:
                        print(f"    Possible profile: {p.material} {p.color_hex} -> {normalize_hex(p.color_hex)}")

if __name__ == "__main__":
    asyncio.run(test_match())
