from fastapi import APIRouter, Depends
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List, Dict
from pydantic import BaseModel

from app.core.database import get_session
from app.models.filament import AmsSlot

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
        if not slot.tray_type or not slot.tray_color:
            continue
            
        key = (slot.tray_type, slot.tray_color)
        
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
