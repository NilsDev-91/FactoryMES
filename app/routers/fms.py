from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict, Any
from pydantic import BaseModel

from app.core.database import get_session
from app.models.filament import Filament
from app.models.printer import Printer

router = APIRouter(prefix="/fms", tags=["Filament Management System"])

class MaterialAvailability(BaseModel):
    hex_code: str
    material: str
    color_name: str
    ams_slots: List[str] # Format: "Serial/Slot#"

@router.get("/ams/available-materials", response_model=List[MaterialAvailability])
async def get_available_materials(session: AsyncSession = Depends(get_session)):
    """
    Returns a deduplicated list of all available materials across the fleet.
    Aggregates by (Material Type, Hex Color) from Printer.ams_config JSON.
    """
    statement = select(Printer)
    result = await session.execute(statement)
    all_printers = result.scalars().all()

    # Aggregation Dictionary
    # Key: (material, hex_code) -> Value: { color_name, slots: [] }
    aggregator: Dict[tuple, dict] = {}

    for printer in all_printers:
        ams_config = printer.ams_config or {}
        for slot_id, slot_data in ams_config.items():
            # Skip empty entries
            if not slot_data or not slot_data.get("material") or not slot_data.get("color_hex"):
                continue
                
            material = slot_data.get("material")
            hex_code = slot_data.get("color_hex")
            
            key = (material, hex_code)
            
            if key not in aggregator:
                aggregator[key] = {
                    "color_name": slot_data.get("color_name") or "Unknown",
                    "slots": []
                }
                
            slot_identifier = f"{printer.serial}/Slot{slot_id}"
            aggregator[key]["slots"].append(slot_identifier)

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

@router.get("/profiles", response_model=List[Filament])
async def get_filament_profiles(session: AsyncSession = Depends(get_session)):
    """
    Returns all defined filament profiles (Filament model).
    """
    statement = select(Filament)
    result = await session.execute(statement)
    return result.scalars().all()

class FilamentCreate(BaseModel):
    collection_id: str
    brand: str
    material: str
    color_hex: str
    color_name: str
    density: float = 1.24
    price_per_kg: Optional[float] = None

@router.post("/profiles", response_model=Filament)
async def create_filament(
    filament_data: FilamentCreate, 
    session: AsyncSession = Depends(get_session)
):
    """
    Creates a new filament record.
    """
    # Check for existing
    statement = select(Filament).where(
        Filament.collection_id == filament_data.collection_id
    )
    existing = await session.execute(statement)
    if found := existing.scalar_one_or_none():
        return found
        
    # Create new
    filament = Filament(**filament_data.dict())
    session.add(filament)
    await session.commit()
    await session.refresh(filament)
    return filament
