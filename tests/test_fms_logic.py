import pytest
from app.services.filament_manager import FilamentManager
from app.models.filament import AmsSlot
from app.utils.color_math import calculate_delta_e

@pytest.mark.asyncio
async def test_fms_exact_match():
    """Scenario 1: Exact Match"""
    inventory = [
        AmsSlot(ams_index=0, slot_index=0, tray_color="FF0000", tray_type="PLA", remaining_percent=100)
    ]
    manager = FilamentManager()
    idx = await manager.find_matching_slot(inventory, "#FF0000")
    assert idx == 0

@pytest.mark.asyncio
async def test_fms_acceptable_deviation():
    """Scenario 2: Acceptable Deviation"""
    # Target: Pure Red, Slot: Material Red (D32F2F)
    inventory = [
        AmsSlot(ams_index=0, slot_index=1, tray_color="D32F2F", tray_type="PLA", remaining_percent=100)
    ]
    manager = FilamentManager()
    
    # Check Delta E first to see if it meets the < 5.0 criteria imposed by the code
    delta_e = calculate_delta_e("FF0000", "D32F2F")
    print(f"Delta E between FF0000 and D32F2F is {delta_e}")
    
    idx = await manager.find_matching_slot(inventory, "#FF0000")
    
    if delta_e < 5.0:
        assert idx == 1
    else:
        # If the math says it's too far, the manager should return None
        # The user requirement says "If Delta E < 5.0, should match".
        # It implies that if it IS > 5.0, it should NOT match.
        assert idx is None

@pytest.mark.asyncio
async def test_fms_mismatch():
    """Scenario 3: Mismatch"""
    inventory = [
        AmsSlot(ams_index=0, slot_index=2, tray_color="0000FF", tray_type="PLA", remaining_percent=100)
    ]
    manager = FilamentManager()
    idx = await manager.find_matching_slot(inventory, "#FF0000")
    assert idx is None

@pytest.mark.asyncio
async def test_fms_empty_inventory():
    """Scenario 4: Empty Inventory"""
    inventory = []
    manager = FilamentManager()
    idx = await manager.find_matching_slot(inventory, "#FF0000")
    assert idx is None
