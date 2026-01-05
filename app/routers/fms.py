from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict
from pydantic import BaseModel

from app.core.database import get_session
from app.models.filament import AmsSlot, FilamentProfile

router = APIRouter(prefix="/fms", tags=["Filament Management System"])

class MaterialAvailability(BaseModel):
    hex_code: str
    material: str
    color_name: str
    ams_slots: List[str] # Format: "Serial/AMS#/Slot#"

@router.get("/ams/available-materials", response_model=List[MaterialAvailability])
async def get_available_materials(session: AsyncSession = Depends(get_session)):
    """
    Returns a deduplicated list of all available materials across the fleet.
    Aggregates by (Material Type, Hex Color).
    """
    statement = select(AmsSlot)
    result = await session.exec(statement)
    all_slots = result.all()

    # Aggregation Dictionary
    # Key: (material, hex_code) -> Value: { color_name, slots: [] }
    aggregator: Dict[tuple, dict] = {}

    for slot in all_slots:
        # Skip empty slots
        if not slot.material or not slot.color_hex:
            continue
            
        key = (slot.material, slot.color_hex)
        
        if key not in aggregator:
            aggregator[key] = {
                "color_name": "Unknown", # Placeholder for now
                "slots": []
            }
            
        slot_id = f"{slot.printer_id}/AMS{slot.ams_index}/Slot{slot.slot_index}"
        aggregator[key]["slots"].append(slot_id)

    # Build Response
    response_list = []
    for (material, hex_code), data in aggregator.items():
        response_list.append(MaterialAvailability(
            hex_code=hex_code,
            material=material,
            color_name=data["color_name"],
            ams_slots=data["slots"]
        ))

    return response_list

@router.get("/profiles", response_model=List[FilamentProfile])
async def get_filament_profiles(session: AsyncSession = Depends(get_session)):
    """
    Returns all defined filament profiles.
    """
    statement = select(FilamentProfile)
    result = await session.exec(statement)
    return result.all()

class FilamentProfileCreate(BaseModel):
    brand: str
    material: str
    color_hex: str
    density: float = 1.24 # Default PLA
    spool_weight: float = 1000.0

@router.post("/profiles", response_model=FilamentProfile)
async def create_filament_profile(
    profile_data: FilamentProfileCreate, 
    session: AsyncSession = Depends(get_session)
):
    """
    Creates a new filament profile.
    Used for auto-generating profiles from AMS data.
    """
    # Check for existing profile (Brand + Material + Hex)
    statement = select(FilamentProfile).where(
        FilamentProfile.brand == profile_data.brand,
        FilamentProfile.material == profile_data.material,
        FilamentProfile.color_hex == profile_data.color_hex
    )
    existing = await session.execute(statement)
    if found := existing.scalar_one_or_none():
        return found
        
    # Create new
    profile = FilamentProfile(**profile_data.dict())
    session.add(profile)
    await session.commit()
    await session.refresh(profile)
    return profile
