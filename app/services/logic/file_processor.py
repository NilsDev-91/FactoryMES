import asyncio
import hashlib
import json
import logging
import re
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

from pydantic import BaseModel, Field
from app.services.logic.gcode_modifier import GCodeModifier
from app.core.exceptions import SafetyException

# Setup logging
logger = logging.getLogger(__name__)

class FileSanitizationError(Exception):
    """Custom exception for errors during file sanitization."""
    pass

class FilamentInfo(BaseModel):
    id: str = Field(default="0", description="Filament ID")
    type: str = Field(default="PLA", description="Filament Type")
    color: str = Field(default="#FFFFFF", description="Hex Color Code")

class PlateMetadata(BaseModel):
    filament_id: List[str] = Field(default_factory=list)
    filament_type: List[str] = Field(default_factory=list)
    filament_colors: List[str] = Field(default_factory=list)
    
    class Config:
        extra = "allow"

class FileProcessorService:
    """
    Service to sanitize 3MF files on-the-fly to prevent Filament Mismatch race conditions.
    Acts as a proxy that "nukes" conflicting metadata and normalizes G-code.
    """
    
    # Files to explicitly remove from the archive to prevent override conflicts
    EXCLUDED_FILES = {
        "Metadata/filament_sequence.json",
        "Metadata/model_settings.config"
    }

    async def sanitize_and_repack(self, source_path: Path, target_index: int, filament_color: str = "#FFFFFF", filament_type: str = "PLA", printer_type: Optional[str] = None, is_calibration_due: bool = True) -> Path:
        """
        Asynchronously sanitizes the provided 3MF file.
        Injects the target tool index directly into G-code and Metadata.
        
        Args:
            source_path (Path): Absolute path to the source .3mf file.
            target_index (int): The 0-based AMS slot index (0-15) to force.
            filament_color (str): Hex color code (e.g. #FF0000).
            filament_type (str): Material type (e.g. PLA).
            printer_type (Optional[str]): The hardware model (e.g. "A1", "X1C") for auto-ejection.
            
        Returns:
            Path: Path to the newly created sanitized .3mf file.
            
        Raises:
            FileSanitizationError: If processing fails.
        """
        if not source_path.exists():
            raise FileSanitizationError(f"Source file not found: {source_path}")

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._sync_sanitize, source_path, target_index, filament_color, filament_type, printer_type, is_calibration_due)
        except Exception as e:
            logger.error(f"Failed to sanitize file {source_path}: {e}", exc_info=True)
            raise FileSanitizationError(f"Sanitization failed: {str(e)}") from e

    def _sync_sanitize(self, source_path: Path, target_index: int, filament_color: str, filament_type: str, printer_type: Optional[str] = None, is_calibration_due: bool = True) -> Path:
        """
        Synchronous core logic: Excludes bad files, neutralizes metadata, normalizes G-code.
        """
        fd, temp_output_path_str = tempfile.mkstemp(suffix=".3mf", prefix="sanitized_")
        temp_output_path = Path(temp_output_path_str)
        
        with open(fd, 'wb') as _: 
            pass

        logger.info(f"Starting DIRECT INJECTION sanitization for {source_path.name} -> {temp_output_path.name} (Target: T{target_index})")

        new_gcode_content: Optional[bytes] = None
        active_gcode_filename: Optional[str] = None
        part_height_mm: Optional[float] = None  # Extract from metadata for A1 sweep
        
        try:
            with zipfile.ZipFile(source_path, "r") as source_zip, \
                 zipfile.ZipFile(temp_output_path, "w", compression=zipfile.ZIP_DEFLATED) as target_zip:

                # --- PRE-PASS: Extract part height from metadata ---
                for item in source_zip.infolist():
                    if re.match(r"Metadata/plate_.*\.json$", item.filename):
                        try:
                            metadata_content = source_zip.read(item.filename)
                            part_height_mm = self._extract_part_height(metadata_content)
                            if part_height_mm:
                                logger.info(f"Extracted part height: {part_height_mm:.1f}mm from {item.filename}")
                            break  # Only need first plate metadata
                        except Exception as e:
                            logger.warning(f"Failed to extract part height from {item.filename}: {e}")

                # --- MAIN PASS: Process all files ---
                for item in source_zip.infolist():
                    file_name = item.filename
                    
                    # A. File Exclusion (Nuclear Option)
                    if file_name in self.EXCLUDED_FILES:
                        logger.warning(f"NUCLEAR: Deleting excluded file {file_name}")
                        continue

                    # B. Metadata Neutralization (Metadata/plate_*.json)
                    if re.match(r"Metadata/plate_.*\.json$", file_name):
                        logger.debug(f"Neutralizing metadata in {file_name}")
                        original_content = source_zip.read(file_name)
                        modified_content = self._neutralize_metadata_json(original_content, target_index, filament_color, filament_type)
                        target_zip.writestr(item, modified_content)

                    # C. G-Code Normalization (Metadata/plate_*.gcode)
                    elif re.match(r"Metadata/plate_.*\.gcode$", file_name):
                        logger.debug(f"Normalizing G-Code in {file_name} -> T{target_index} (Type: {printer_type}, Part Height: {part_height_mm})")
                        original_gcode = source_zip.read(file_name)
                        new_gcode_content = self._normalize_gcode(
                            original_gcode, 
                            target_index, 
                            printer_type, 
                            is_calibration_due,
                            part_height_mm=part_height_mm
                        )
                        active_gcode_filename = file_name
                        target_zip.writestr(item, new_gcode_content)

                    # D. Integrity Verification (Metadata/plate_*.gcode.md5)
                    elif re.match(r"Metadata/plate_.*\.gcode\.md5$", file_name):
                        # Determine which GCode this MD5 belongs to
                        logger.debug(f"Recalculating hash for {file_name}")
                        
                        expected_gcode_name = file_name.replace(".md5", "")
                        current_gcode_content = new_gcode_content
                        
                        if active_gcode_filename != expected_gcode_name:
                             # We need to read the specific G-code for this MD5
                             try:
                                with source_zip.open(expected_gcode_name) as gcode_file:
                                    raw_gcode = gcode_file.read()
                                    current_gcode_content = self._normalize_gcode(raw_gcode, target_index, printer_type, is_calibration_due)
                             except KeyError:
                                logger.warning(f"{expected_gcode_name} not found for MD5 calculation.")
                                current_gcode_content = b""

                        new_md5 = self._calculate_md5(current_gcode_content)
                        target_zip.writestr(item, new_md5)

                    # F. Slice Info Manifest (Metadata/slice_info.config) - NEW
                    elif re.match(r"Metadata/slice_info\.config$", file_name):
                         logger.debug(f"Synchronizing Slice Info for T{target_index}")
                         original_xml = source_zip.read(file_name)
                         new_xml = self._synchronize_metadata(original_xml, target_index, filament_color, filament_type)
                         target_zip.writestr(item, new_xml)

                    # G. PASSTHROUGH: Copy all other files as-is (CRITICAL for valid 3MF)
                    else:
                         # This includes essential files like:
                         # - [Content_Types].xml
                         # - _rels/.rels
                         # - 3D/3dmodel.model
                         # - Metadata/*.png (thumbnails)
                         # - etc.
                         target_zip.writestr(item, source_zip.read(file_name))

                # Final ensure: If we have an active GCode but no MD5 was written for it
                if active_gcode_filename:
                    expected_md5_name = active_gcode_filename + ".md5"
                    if expected_md5_name not in source_zip.namelist() and new_gcode_content is not None:
                         logger.info(f"Adding missing MD5 file: {expected_md5_name}")
                         new_md5 = self._calculate_md5(new_gcode_content)
                         target_zip.writestr(expected_md5_name, new_md5)

        except Exception as e:
            try:
                temp_output_path.unlink()
            except OSError:
                pass
            raise e

        return temp_output_path

    def _synchronize_metadata(self, content: bytes, target_index: int, filament_color: str, filament_type: str) -> bytes:
        """
        Parses `slice_info.config` XML and forces exactly one filament entry.
        Reasoning: This prevents "Filament Mismatch" errors by removing strict checks
        and aligns with the T0-only G-code strategy.
        Now also aligns the target slot with physical reality.
        """
        try:
            import xml.etree.ElementTree as ET
            
            # Parse XML
            root = ET.fromstring(content)
            
            # Find the <plate> tag.
            plate = root.find("plate")
            if plate is None:
                for child in root:
                    if "plate" in child.tag:
                        plate = child
                        break
            
            if plate is None:
                logger.warning("No <plate> tag found in slice_info.config. Skipping sync.")
                return content

            # Get existing filaments
            filaments = plate.findall("filament")
            if not filaments:
                 filaments = [child for child in plate if "filament" in child.tag]

            # FORCE 4 ENTRIES: Remove all existing filaments
            for f in filaments:
                plate.remove(f)
            
            # Create 4 generic filaments (IDs 1, 2, 3, 4)
            for i in range(1, 5):
                f_elem = ET.Element("filament")
                f_elem.set("id", str(i))
                f_elem.set("vendor", "Generic")
                
                # If this is the target filament, use the real specs to satisfy AMS pre-flight checks
                if (i - 1) == target_index:
                    f_elem.set("type", filament_type)
                    f_elem.set("color", filament_color)
                else:
                    f_elem.set("type", "PLA")
                    f_elem.set("color", "#FFFFFF")
                
                plate.append(f_elem)
            
            logger.info("Scrubbed manifest: Forced 4 'Generic PLA' filament entries (Native Strategy).")

            return ET.tostring(root, encoding="utf-8", xml_declaration=True)
                
        except Exception as e:
            logger.error(f"Failed to synchronize metadata: {e}")
            return content

    def _neutralize_metadata_json(self, content: bytes, target_index: int, filament_color: str, filament_type: str) -> bytes:
        """
        Parses JSON.
        Actions:
        - EXPAND to 5 generic filaments (Indices 0-4).
        - Randomize IDs.
        - Force real specs for the target index to satisfy printer.
        """
        try:
            data = json.loads(content.decode("utf-8"))
            
            count = 5 # Cover generic slots 0-4

            # Generate random IDs to be absolutely sure no internal ID cache matches
            new_ids = [str(uuid.uuid4()) for _ in range(count)]
            
            data["filament_id"] = new_ids
            data["filament_type"] = ["PLA"] * count
            data["filament_colors"] = ["#FFFFFF"] * count
            
            # Use real specs for the target slot!
            if 0 <= target_index < count:
                data["filament_type"][target_index] = filament_type
                data["filament_colors"][target_index] = filament_color

            data["filament_is_support"] = [False] * count
            
            return json.dumps(data, indent=4).encode("utf-8")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse metadata JSON: {e}. Returning original.")
            return content

    def _extract_part_height(self, content: bytes) -> Optional[float]:
        """
        Extracts the model/part height from plate metadata JSON.
        
        Looks for common height fields in Bambu Lab 3MF metadata:
        - model_height / modelHeight
        - objects[*].height / bbox_z
        - print_height
        
        Returns:
            The part height in mm, or None if not found.
        """
        try:
            data = json.loads(content.decode("utf-8"))
            
            # Try direct height fields
            for key in ["model_height", "modelHeight", "print_height", "height", "z_height"]:
                if key in data and data[key]:
                    try:
                        return float(data[key])
                    except (ValueError, TypeError):
                        continue
            
            # Try objects array (common in Bambu Studio exports)
            if "objects" in data and isinstance(data["objects"], list):
                max_height = 0.0
                for obj in data["objects"]:
                    for key in ["height", "bbox_z", "z_max", "model_height"]:
                        if key in obj:
                            try:
                                h = float(obj[key])
                                max_height = max(max_height, h)
                            except (ValueError, TypeError):
                                continue
                if max_height > 0:
                    return max_height
            
            # Try bounding box (some slicers use this format)
            if "bounding_box" in data:
                bbox = data["bounding_box"]
                if isinstance(bbox, dict) and "z_max" in bbox:
                    return float(bbox["z_max"])
                elif isinstance(bbox, list) and len(bbox) >= 6:
                    # Format: [x_min, y_min, z_min, x_max, y_max, z_max]
                    return float(bbox[5])
            
            logger.debug("No part height field found in metadata")
            return None
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse metadata JSON for height extraction: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error extracting part height: {e}")
            return None

    def _normalize_gcode(self, content: bytes, target_index: int, printer_type: Optional[str] = None, is_calibration_due: bool = True, part_height_mm: Optional[float] = None) -> bytes:
        """
        Normalizes the G-code to T0 Master protocol and injects Auto-Ejection footer.
        1. Injects Cache Busting Header (M620 S255, T255).
        2. Normalizes all tool calls to T0.
        3. Appends T0 after reset to trigger load.
        4. Appends Auto-Ejection Footer.
        """
        text = content.decode("utf-8")
        
        # 1. Regex replace all occurrences of T\d+ with T{target_index}.
        # This forces the printer to use the physical slot mapped to target_index.
        sanitized_text = re.sub(r'\bT[0-9]+\b', f'T{target_index}', text)
        
        # 1.5. Dynamic Calibration Optimization
        sanitized_text = GCodeModifier.optimize_start_gcode(sanitized_text, is_calibration_due)
        
        # 2. Construct Injection Sequence (The "Native Select")
        injection_sequence = (
            f"\n; --- FACTORYOS NATIVE SELECT ---\n"
            f"M1002 gcode_claim_action : 0\n"
            f"M109 S220      ; Ensure Nozzle soft\n"
            f"G1 X20 Y50 F12000 ; Move near cutter\n"
            f"M620 S{target_index}A  ; Select Physical Slot\n"
            f"T{target_index}        ; Select Tool\n"
            f"M621 S{target_index}A  ; Sync\n"
            f"; -----------------------------\n"
        )
        
        # 3. Smart Insertion: Find First G28
        lines = sanitized_text.splitlines()
        insertion_index = -1
        
        for i, line in enumerate(lines):
            # regex to match G28 at start of line (ignoring leading whitespace)
            if re.match(r'^\s*G28', line.strip()):
                insertion_index = i
                break
        
        if insertion_index != -1:
            # Insert after G28
            lines.insert(insertion_index + 1, injection_sequence)
            final_text = "\n".join(lines)
            logger.info(f"FMS: Kinematic-Aware Injection successful after line {insertion_index + 1} (G28).")
        else:
            # Fallback: Prepend G28 + Sequence if no G28 found
            logger.warning("FMS: No G28 found in G-code! Prepending Homing + Injection Sequence.")
            final_text = "G28 ; Force Home (Fallback)\n" + injection_sequence + sanitized_text

        # 4. Inject Auto-Ejection Footer
        if printer_type:
             final_text = self._inject_ejection_footer(final_text, printer_type, part_height_mm=part_height_mm)

        return final_text.encode("utf-8")

    def _generate_a1_sweep_gcode(self, part_height_mm: float) -> Optional[str]:
        """
        Generates the A1 "Safe Gantry Sweep" (Bulldozer) G-code macro.
        
        **Valid only for parts > 38mm due to Z+2.0mm safety floor.**
        
        Physics Constraints (User-Verified):
        - HARD Z-FLOOR: Nozzle MUST NEVER go below Z = +2.0 mm.
        - KINEMATIC OFFSET: Gantry Beam bottom is 33.0 mm above Nozzle Tip.
        - MINIMUM PART HEIGHT: Beam at Z=2.0 is at 35.0mm effective height.
          Parts must be > 38.0 mm for reliable mechanical sweep (3mm overlap margin).
        
        Args:
            part_height_mm: The height of the printed part in millimeters.
            
        Returns:
            G-code string if part is tall enough for safe sweep, None otherwise.
            
        Raises:
            SafetyException: If part height is below the mechanical threshold.
        """
        # --- SAFETY CONSTANTS ---
        Z_HARD_FLOOR = 2.0  # mm - ABSOLUTE MINIMUM Z (Nozzle NEVER goes below)
        KINEMATIC_OFFSET = 33.0  # mm - Beam bottom above nozzle tip
        MIN_PART_HEIGHT = 38.0  # mm - Minimum part height for safe sweep
        BED_COOLDOWN_TEMP = 28  # °C - Passive cooling target
        SWEEP_FEEDRATE = 400  # mm/min - Slow sweep for reliability
        
        # --- VALIDATION GATE ---
        if part_height_mm < MIN_PART_HEIGHT:
            # Parts below threshold cannot be safely swept - log and return None
            # Caller should fall back to manual removal or alternative strategy
            logger.warning(
                f"A1 Sweep BLOCKED: Part height ({part_height_mm:.1f}mm) is below "
                f"the mechanical sweep threshold ({MIN_PART_HEIGHT}mm). "
                f"Z-Floor: {Z_HARD_FLOOR}mm, Beam Offset: {KINEMATIC_OFFSET}mm. "
                f"Manual removal required."
            )
            return None
        
        # --- THE SAFE SWEEP SEQUENCE ---
        # This sequence is designed with zero risk tolerance for bed collisions.
        sweep_gcode = (
            "\n; === FACTORYOS A1 GANTRY SWEEP (SAFE BULLDOZER) ==="
            f"\n; Part Height: {part_height_mm:.1f}mm (Threshold: {MIN_PART_HEIGHT}mm)\n"
            f"; Z-FLOOR: {Z_HARD_FLOOR}mm (HARD LIMIT - NOZZLE NEVER BELOW THIS)\n"
            f"; Effective Beam Position: {Z_HARD_FLOOR + KINEMATIC_OFFSET}mm\n"
            "\n"
            "; --- PHASE 1: SECURE & COOL ---\n"
            "M84 S0        ; Lock Motors (Prevent idle timeout during cooldown)\n"
            "M140 S0       ; Bed Heater OFF\n"
            "M104 S0       ; Nozzle Heater OFF\n"
            f"M190 R{BED_COOLDOWN_TEMP}    ; Wait for Bed < {BED_COOLDOWN_TEMP}C (Passive Cooling ONLY - NO FAN)\n"
            "\n"
            "; --- PHASE 2: POSITION ---\n"
            "G90           ; Absolute Positioning\n"
            "G1 Z100 F3000 ; Safety Lift (Clear any obstacles)\n"
            "G1 X0 Y0 F6000  ; Park: Nozzle X-Left, Bed to Front\n"
            f"G1 Z{Z_HARD_FLOOR:.1f} F1000  ; *** CRITICAL: THE HARD FLOOR (Z={Z_HARD_FLOOR}mm) ***\n"
            "\n"
            "; --- PHASE 3: SWEEP ACTION ---\n"
            f"G1 Y256 F{SWEEP_FEEDRATE}  ; Execute Sweep: Bed moves back, Part pushed off by Gantry Beam\n"
            "\n"
            "; --- PHASE 4: RESET ---\n"
            "G1 Z50 F3000  ; Lift Gantry (Clear bed for homing)\n"
            "G28           ; Home All Axes (Safe now that bed is clear)\n"
            "M84 S120      ; Restore Default Idle Timeout (120 seconds)\n"
            "; === END A1 GANTRY SWEEP ==="
        )
        
        logger.info(
            f"A1 Sweep GENERATED: Part {part_height_mm:.1f}mm, "
            f"Z-Floor {Z_HARD_FLOOR}mm, Effective Beam at {Z_HARD_FLOOR + KINEMATIC_OFFSET}mm"
        )
        
        return sweep_gcode

    def _inject_ejection_footer(self, gcode_text: str, printer_type: str, part_height_mm: Optional[float] = None) -> str:
        """
        Appends hardware-specific ejection sequence to the G-code.
        
        For A1 printers with tall parts (> 38mm), uses the Safe Gantry Sweep.
        Falls back to Y-Axis Fling for shorter parts or when height is unknown.
        
        Args:
            gcode_text: The G-code string to append to.
            printer_type: Hardware model (e.g., "A1", "X1C").
            part_height_mm: Optional part height for A1 sweep logic.
        """
        p_type = printer_type.upper()
        footer = ""

        if "A1" in p_type:
            # Try the Safe Gantry Sweep for tall parts
            if part_height_mm is not None:
                sweep_gcode = self._generate_a1_sweep_gcode(part_height_mm)
                if sweep_gcode:
                    logger.info(f"FMS: Using A1 Safe Gantry Sweep for {part_height_mm:.1f}mm part.")
                    return gcode_text + sweep_gcode
                else:
                    logger.info(f"FMS: Part too short for sweep ({part_height_mm:.1f}mm), using standard fling.")
            
            # Fallback: A1 / A1 Mini: Y-Axis Fling (for short parts or unknown height)
            footer = (
                "\n; --- FACTORYOS AUTO-EJECTION (A1 Fling) ---\n"
                "; NOTE: Part height below sweep threshold or unknown.\n"
                "; Using inertial ejection instead of gantry sweep.\n"
                "M104 S0 ; Heat off\n"
                "M140 S0 ; Bed off\n"
                "M106 S255 ; Max fan for fast cooling\n"
                "M109 R28 ; Wait for nozzle < 28C (Safety)\n"
                "G28 ; Home All\n"
                "M221 S100 ; Reset flow\n"
                "; Physical Ejection Moves\n"
                "G1 Y250 F12000 ; High accel fling\n"
                "G1 Y10 F12000\n"
                "G1 Y250 F12000\n"
                "; ------------------------------------------\n"
            )
        elif any(x in p_type for x in ["X1", "P1"]):
             # X1C / P1P / P1S: Sweep
             footer = (
                "\n; --- FACTORYOS AUTO-EJECTION (Sweep) ---\n"
                "M140 S0 ; Bed off\n"
                "M106 S255 ; Max fan\n"
                "M109 R28 ; Wait for safe temp\n"
                "G91 ; Relative mode\n"
                "G1 Z10 F600 ; Safety Z-hop\n"
                "G90 ; Absolute mode\n"
                "; Concept Sweep Motion\n"
                "G1 X10 Y10 F12000\n"
                "G1 X240 F12000\n"
                "; ------------------------------------------\n"
             )
        
        if footer:
            logger.info(f"FMS: Injected {p_type} ejection footer.")
            return gcode_text + footer
        
        return gcode_text

    def _calculate_md5(self, content: bytes) -> str:
        return hashlib.md5(content).hexdigest()
