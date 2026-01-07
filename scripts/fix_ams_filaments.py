import asyncio
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import async_session_maker
from sqlmodel import select, delete
from app.models.filament import FilamentProfile, AmsSlot

async def fix_ams_filaments():
    async with async_session_maker() as session:
        print("🔧 Repairing Filament Profiles and AMS Slots...")
        
        # 1. Fetch all profiles
        profiles_res = await session.exec(select(FilamentProfile))
        profiles = profiles_res.all()
        
        # 2. Update names for known hex codes
        known_colors = {
            "#000000": "Black",
            "000000": "Black",
            "#000000FF": "Black",
            "000000FF": "Black",
            "#FF0000": "Red",
            "FF0000": "Red",
            "#FF0000FF": "Red",
            "FF0000FF": "Red",
            "#FFFFFF": "White",
            "FFFFFF": "White",
            "#0000FF": "Blue",
            "0000FF": "Blue"
        }
        
        for p in profiles:
            hex_val = p.color_hex.upper()
            if hex_val in known_colors and not p.color_name:
                print(f"   - Updating profile {p.id} ({p.color_hex}) -> {known_colors[hex_val]}")
                p.color_name = known_colors[hex_val]
                session.add(p)
        
        await session.flush()
        
        # 3. Fetch AMS slots and update color names
        slots_res = await session.exec(select(AmsSlot))
        slots = slots_res.all()
        
        for s in slots:
            if s.material and s.color_hex:
                # Try to find a profile match
                norm_hex = s.color_hex.lstrip("#")[:6].upper()
                match = next((p for p in profiles if p.material == s.material and p.color_hex.lstrip("#")[:6].upper() == norm_hex and p.color_name), None)
                if match:
                    print(f"   - Updating AMS Slot {s.slot_id} (Tray {s.slot_index}) on {s.printer_id} -> {match.color_name}")
                    s.color_name = match.color_name
                    session.add(s)
                else:
                    # Fallback to known colors dict
                    lookup_hex = s.color_hex.upper()
                    if lookup_hex in known_colors:
                         print(f"   - Updating AMS Slot {s.slot_id} from known_colors -> {known_colors[lookup_hex]}")
                         s.color_name = known_colors[lookup_hex]
                         session.add(s)
                    elif "#"+lookup_hex if not lookup_hex.startswith("#") else lookup_hex in known_colors:
                         # Handle cases with or without '#'
                         key = "#"+lookup_hex if not lookup_hex.startswith("#") else lookup_hex
                         print(f"   - Updating AMS Slot {s.slot_id} from known_colors -> {known_colors[key]}")
                         s.color_name = known_colors[key]
                         session.add(s)

        await session.commit()
    print("✅ AMS Filament data repaired.")

if __name__ == "__main__":
    asyncio.run(fix_ams_filaments())
