from typing import List, Optional
from app.models.filament import AmsSlot
from app.utils.color_math import calculate_delta_e

class FilamentManager:
    """
    Service for managing filament inventory and validating print jobs.
    """

    async def find_matching_slot(self, printer_inventory: List[AmsSlot], target_hex: str) -> Optional[int]:
        """
        Finds the best matching AMS slot for a given target hex color.

        Args:
            printer_inventory: A list of AmsSlot objects representing the printer's current inventory.
            target_hex: The target hex color string (e.g., "#FF0000").

        Returns:
            int: The 0-indexed slot index (ams_index * 4 + slot_index usually, but here we explicitly
                 return the index in the list, or better yet, let's assume the mapped slot ID.
                 Wait, the requirements say "Return the slot index". 
                 The AmsSlot has `ams_index` and `slot_index`.
                 However, usually 'slot index' in this context implies the flattened index or the specific identifier.
                 Let's check the requirement: "Return the slot index of the candidate".
                 If the input is a list of slots, returning the index IN THAT LIST makes sense?
                 Or the actual `slot_index` property?
                 
                 "Return the slot index of the candidate with the *lowest* Delta E."
                 
                 If I return the index in the list, the caller can retrieve the slot object. 
                 But often these are mapped 0-15. 
                 
                 Let's look at `AmsSlot` again. It has `ams_index` (0-3) and `slot_index` (0-3).
                 Usually Bambu printers have 4 slots per AMS. 
                 If the user means "the integer ID that the printer expects", it might be different.
                 
                 BUT, Requirement 2 says: "Return the slot index of the candidate".
                 Given `printer_inventory` is a list, returning the index IN THE LIST is safe if the list is ordered.
                 However, a safer bet for a "Manage" service is to return the `ams_id` or `tray_id` if it existed.
                 
                 Let's assume "slot index" means the `aims_index` if single AMS, or we might need to return a tuple?
                 
                 Actually, looking at `AmsSlot` definition:
                 `ams_index: int` # 0-3
                 `slot_index: int` # 0-3
                 
                 If the requirement says "Return the slot index", and signature is `-> Optional[int]`,
                 it implies a single integer.
                 
                 Standard mapping for Bambu is 0-15 (AMS 0: 0-3, AMS 1: 4-7, etc).
                 Let's implement a helper or assume the caller handles the mapping. 
                 
                 Wait, let's look at the standard logic for Bambu.
                 Users often refer to "Slot 1" -> 0.
                 
                 Let's sticking to the "return the slot index of the candidate" from the PROMPT.
                 "Iterate through all slots ... Return the slot index of the candidate ...".
                 
                 Let's return the `ams_index * 4 + slot_index` calculated value which is unique per printer?
                 Or simply the index of the item in the `printer_inventory` list? 
                 
                 "Return the slot index of the candidate with the lowest Delta E"
                 
                 I will implement it to return the flattened index (0-15) calculated from ams_index and slot_index,
                 as that allows unique identification.
                 
                 Wait, if the input is just a list, maybe it just wants the index inside `printer_inventory`?
                 
                 Let's look at `find_matching_slot` usage context: "This service will be used by the PrinterWorker before sending MQTT commands."
                 MQTT commands usually take `tray_id` or `target_tray`.
                 
                 I'll compute the flattened index: `slot.ams_index * 4 + slot.slot_index`.
                 This seems robust.
        """
        best_match_idx = None
        min_delta_e = float("inf")

        for slot in printer_inventory:
            # Skip empty slots (no color or no filament remaining)
            # Note: explicit check for empty string or None
            if not slot.tray_color: 
                continue
            
            # If remaining_percent is None or 0, we might want to skip, 
            # but requirements only say "Skip empty slots".
            # Usually empty means no tray inserted or no color data.
            # I will assume tray_color is the indicator.

            try:
                delta_e = calculate_delta_e(slot.tray_color, target_hex)
            except ValueError:
                # Handle invalid hex in inventory gracefully
                continue

            if delta_e == 0:
                # Exact match - return immediately
                return slot.ams_index * 4 + slot.slot_index

            if delta_e < 5.0:
                if delta_e < min_delta_e:
                    min_delta_e = delta_e
                    best_match_idx = slot.ams_index * 4 + slot.slot_index

        return best_match_idx

    def can_printer_print_job(self, printer: any, job: any) -> bool:
        """
        Determines if a printer is PHYSICALLY capable of printing a job based on loaded filaments.
        Checks for material type (PLA/PETG) and color (Delta E < 5.0).
        """
        # 1. Get Job Requirements
        reqs = job.filament_requirements
        if not reqs:
            return True # No requirements, safe to print
        
        # Normalize reqs to list
        if isinstance(reqs, dict):
            reqs = [reqs]
        
        # 2. Iterate requirements
        for req in reqs:
            target_hex = req.get("color_hex") or req.get("hex_color") or req.get("color")
            target_material = req.get("material", "PLA").upper()
            
            if not target_hex:
                continue
            
            # 3. Check for match in printer slots
            match_found = False
            for slot in printer.ams_slots:
                if not slot.tray_color or not slot.tray_type:
                    continue
                
                # Material Match
                if slot.tray_type.upper() != target_material:
                    continue
                
                # Color Match
                try:
                    de = calculate_delta_e(slot.tray_color, target_hex)
                    if de < 5.0:
                        match_found = True
                        break
                except Exception:
                    continue
            
            if not match_found:
                return False # One requirement not met
        
        return True
