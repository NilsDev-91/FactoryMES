import pytest
from app.services.filament_manager import FilamentManager
from app.models.filament import AmsSlot

@pytest.mark.asyncio
async def test_find_matching_slot_exact():
    inventory = [
        AmsSlot(ams_index=0, slot_index=0, tray_color="FFFFFF", tray_type="PLA", remaining_percent=100), # White
        AmsSlot(ams_index=0, slot_index=1, tray_color="000000", tray_type="PLA", remaining_percent=100), # Black
    ]
    manager = FilamentManager()
    
    # Exact match for White -> index 0
    idx = await manager.find_matching_slot(inventory, "#FFFFFF")
    assert idx == 0 # 0*4 + 0

    # Exact match for Black -> index 1
    idx = await manager.find_matching_slot(inventory, "000000")
    assert idx == 1 # 0*4 + 1

@pytest.mark.asyncio
async def test_find_matching_slot_close():
    inventory = [
        AmsSlot(ams_index=0, slot_index=0, tray_color="FF0000", tray_type="PLA", remaining_percent=100), # Red
        AmsSlot(ams_index=0, slot_index=1, tray_color="00FF00", tray_type="PLA", remaining_percent=100), # Green
    ]
    manager = FilamentManager()

    # Slightly off-red (#FE0101) - should match Red (slot 0)
    # Delta E should be small
    idx = await manager.find_matching_slot(inventory, "#FE0101")
    assert idx == 0

@pytest.mark.asyncio
async def test_find_matching_slot_no_match():
    inventory = [
        AmsSlot(ams_index=0, slot_index=0, tray_color="0000FF", tray_type="PLA", remaining_percent=100), # Blue
    ]
    manager = FilamentManager()

    # Target Red - should NOT match Blue (Delta E > 5.0)
    idx = await manager.find_matching_slot(inventory, "#FF0000")
    assert idx is None

@pytest.mark.asyncio
async def test_find_matching_slot_best_match():
    inventory = [
        # Slot 0: White
        AmsSlot(ams_index=0, slot_index=0, tray_color="FFFFFF", tray_type="PLA", remaining_percent=100),
        # Slot 1: Off-White (very close)
        AmsSlot(ams_index=0, slot_index=1, tray_color="F0F0F0", tray_type="PLA", remaining_percent=100),
    ]
    manager = FilamentManager()

    # Target: #F5F5F5 (Mid-gray/white)
    # Both are close, but one is closer.
    # calculate_delta_e("#F5F5F5", "#FFFFFF") vs calculate_delta_e("#F5F5F5", "#F0F0F0")
    
    # Let's test a simpler case logic-wise
    # Target: #FFFFFF
    # Slot 0 is EXACT -> returns 0 immediately
    idx = await manager.find_matching_slot(inventory, "#FFFFFF")
    assert idx == 0

    # Target: #EFEFEF
    # Slot 1 (F0F0F0) is closer to EFEFEF than FFFFFF
    idx = await manager.find_matching_slot(inventory, "#EFEFEF")
    assert idx == 1

@pytest.mark.asyncio
async def test_find_matching_slot_skip_empty():
    inventory = [
        AmsSlot(ams_index=0, slot_index=0, tray_color="", tray_type="PLA", remaining_percent=100), # Empty color
        AmsSlot(ams_index=0, slot_index=1, tray_color=None, tray_type="PLA", remaining_percent=100), # None color
        AmsSlot(ams_index=0, slot_index=2, tray_color="FFFFFF", tray_type="PLA", remaining_percent=100), # Valid
    ]
    manager = FilamentManager()

    idx = await manager.find_matching_slot(inventory, "#FFFFFF")
    assert idx == 2
