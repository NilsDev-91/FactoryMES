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

class SanitizationResult(BaseModel):
    """
    Strictly typed result of the sanitization process.
    Validated on physical hardware (User Reference).
    """
    file_path: Path
    is_auto_eject_enabled: bool  # True ONLY if sweep/fling G-code was appended
    target_slot: int
    detected_height: Optional[float]

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

    async def sanitize_and_repack(self, source_path: Path, target_index: int, filament_color: str = "#FFFFFF", filament_type: str = "PLA", printer_type: Optional[str] = None, is_calibration_due: bool = True, part_height_mm: float = 38.0) -> SanitizationResult:
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
            SanitizationResult: Detailed result of processing.
            
        Raises:
            FileSanitizationError: If processing fails.
        """
        if not source_path.exists():
            raise FileSanitizationError(f"Source file not found: {source_path}")

        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(None, self._sync_sanitize, source_path, target_index, filament_color, filament_type, printer_type, is_calibration_due, part_height_mm)
        except Exception as e:
            logger.error(f"Failed to sanitize file {source_path}: {e}", exc_info=True)
            raise FileSanitizationError(f"Sanitization failed: {str(e)}") from e

    def _sync_sanitize(self, source_path: Path, target_index: int, filament_color: str, filament_type: str, printer_type: Optional[str] = None, is_calibration_due: bool = True, part_height_mm_override: Optional[float] = None) -> SanitizationResult:
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
        eject_status = False
        
        try:
            with zipfile.ZipFile(source_path, "r") as source_zip, \
                 zipfile.ZipFile(temp_output_path, "w", compression=zipfile.ZIP_DEFLATED) as target_zip:

                if part_height_mm_override is not None:
                    part_height_mm = part_height_mm_override
                    logger.info(f"Using provided part height: {part_height_mm:.1f}mm (Override)")
                else:
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
                        
                        # Fix: Unpack the tuple from _normalize_gcode
                        processed_bytes, is_eject_enabled = self._normalize_gcode(
                            original_gcode, 
                            target_index, 
                            printer_type, 
                            is_calibration_due,
                            part_height_mm=part_height_mm
                        )
                        
                        eject_status |= is_eject_enabled
                        new_gcode_content = processed_bytes
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
                                    # Fix: Unpack tuple here as well if we re-process
                                    current_gcode_content, _ = self._normalize_gcode(raw_gcode, target_index, printer_type, is_calibration_due)
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

        # Return structured result
        return SanitizationResult(
            file_path=temp_output_path,
            is_auto_eject_enabled=eject_status,
            target_slot=target_index,
            detected_height=part_height_mm
        )

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

    def _normalize_gcode(self, content: bytes, target_index: int, printer_type: Optional[str] = None, is_calibration_due: bool = True, part_height_mm: Optional[float] = None) -> Tuple[bytes, bool]:
        """
        Normalizes the G-code to T0 Master protocol and injects Auto-Ejection footer.
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
        is_eject_enabled = False
        if printer_type:
             final_text, is_eject_enabled = self._inject_ejection_footer(final_text, printer_type, part_height_mm=part_height_mm)

        return final_text.encode("utf-8"), is_eject_enabled

    def _generate_a1_sweep_gcode(self, part_height_mm: float) -> List[str]:
        """
        Generates the A1 Safe Sweep sequence based on PART HEIGHT from DB.
        Safe Floor: Z=2.0mm. Beam Offset: 33.0mm.
        Validated on physical hardware (User Reference).
        """
        SAFE_FLOOR = 2.0
        BEAM_OFFSET = 33.0
        MIN_SWEEP_HEIGHT = 38.0

        if part_height_mm < MIN_SWEEP_HEIGHT:
            logger.warning(f"Part height {part_height_mm}mm < {MIN_SWEEP_HEIGHT}mm. Manual removal required.")
            return []  # No G-code -> Printer stops -> Human intervention

        # Dynamic Leverage Calculation (Hit at 60% height)
        target_beam_z = part_height_mm * 0.6
        ideal_nozzle_z = target_beam_z - BEAM_OFFSET
        
        # CLAMP to Safe Floor (Crucial Safety Step)
        sweep_z = max(SAFE_FLOOR, ideal_nozzle_z)

        return [
            "; --- A1 SAFE SWEEP (FactoryMES) ---",
            f"; Part Height: {part_height_mm}mm | Sweep Z: {sweep_z:.2f}mm",
            "M84 S0       ; 1. Lock Motors (Infinite Timeout)",
            "M140 S0      ; 2. Bed Off",
            "M104 S0      ; 3. Nozzle Off",
            "M190 R28     ; 4. WAIT for Cool (Passive < 28C)",
            "G90          ; 5. Absolute Positioning",
            "G1 Z100 F3000; 6. Safety Lift",
            "G1 X0 Y0     ; 7. Park (Nozzle Left, Bed Front)",
            f"G1 Z{sweep_z:.2f}  ; 8. Move to Sweep Height",
            "G1 Y256 F1500; 9. EXECUTE SWEEP (Push Part)",
            "G1 Z50 F3000 ; 10. Lift",
            "G28          ; 11. Re-Home (Safe now)",
            "M84 S120     ; 12. Restore Idle Timeout",
            "; --- END SWEEP ---"
        ]

    def _generate_a1_toolhead_push_gcode(self, part_height_mm: float) -> List[str]:
        """
        Generates A1 Toolhead Push (Nozzle Ram) sequence for SMALL parts (<38mm).
        Uses the toolhead itself to gently push the part off the bed.
        Safety: Z >= 10mm to prevent nozzle crash.
        """
        SAFE_Z = 10.0  # Minimum Z height for toolhead push
        PUSH_Z = max(SAFE_Z, part_height_mm + 2.0)  # Stay above part

        return [
            "; --- A1 TOOLHEAD PUSH (FactoryMES) ---",
            f"; Part Height: {part_height_mm}mm | Push Z: {PUSH_Z:.2f}mm",
            "M84 S0       ; 1. Lock Motors",
            "M140 S0      ; 2. Bed Off",
            "M104 S0      ; 3. Nozzle Off",
            "M190 R28     ; 4. WAIT for Cool (Passive < 28C)",
            "G90          ; 5. Absolute Positioning",
            "G1 Z50 F3000 ; 6. Safety Lift",
            "G1 X128 Y10 F12000 ; 7. Move to Center-Back",
            f"G1 Z{PUSH_Z:.2f} F3000 ; 8. Lower to Push Height",
            "G1 Y256 F2000; 9. PUSH FORWARD (Eject Part)",
            "G1 Z50 F3000 ; 10. Lift",
            "G28          ; 11. Re-Home",
            "M84 S120     ; 12. Restore Idle Timeout",
            "; --- END TOOLHEAD PUSH ---"
        ]

    def _inject_ejection_footer(self, gcode_text: str, printer_type: str, part_height_mm: Optional[float] = None) -> Tuple[str, bool]:
        """
        Appends hardware-specific ejection sequence to the G-code.
        
        For A1 printers:
        - Gantry Sweep (X-Axis Ram): Parts >= 38mm
        - Toolhead Push (Nozzle Ram): Parts < 38mm
        """
        p_type = printer_type.upper()
        footer = ""
        is_enabled = False

        if "A1" in p_type:
            MIN_SWEEP_HEIGHT = 38.0
            
            if part_height_mm is not None:
                if part_height_mm >= MIN_SWEEP_HEIGHT:
                    # GANTRY SWEEP: X-Axis Ram for tall parts
                    sweep_lines = self._generate_a1_sweep_gcode(part_height_mm)
                    if sweep_lines:
                        logger.info(f"FMS: Selected A1 Gantry Sweep (Height {part_height_mm:.1f}mm >= {MIN_SWEEP_HEIGHT}mm)")
                        return gcode_text + "\n".join(sweep_lines), True
                else:
                    # TOOLHEAD PUSH: Nozzle Ram for small parts
                    push_lines = self._generate_a1_toolhead_push_gcode(part_height_mm)
                    logger.info(f"FMS: Selected A1 Toolhead Push (Height {part_height_mm:.1f}mm < {MIN_SWEEP_HEIGHT}mm)")
                    return gcode_text + "\n".join(push_lines), True
            else:
                # Unknown height: Default to Gantry Sweep at safe Z (conservative)
                logger.warning("FMS: Part height unknown, defaulting to A1 Gantry Sweep at Z=50mm")
                sweep_lines = self._generate_a1_sweep_gcode(50.0)
                return gcode_text + "\n".join(sweep_lines), True
                
        elif any(x in p_type for x in ["X1", "P1"]):
             # X1C / P1P / P1S: Mechanical Sweep
             footer = (
                "\n; --- FACTORYOS AUTO-EJECTION (X1/P1 Sweep) ---\n"
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
             is_enabled = True
        
        if footer:
            logger.info(f"FMS: Injected {p_type} ejection footer.")
            return gcode_text + footer, is_enabled
        
        return gcode_text, False

    def _calculate_md5(self, content: bytes) -> str:
        return hashlib.md5(content).hexdigest()
