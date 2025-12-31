import asyncio
import hashlib
import json
import logging
import re
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import Dict, List, Optional, Any

from pydantic import BaseModel, Field

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

    async def sanitize_and_repack(self, source_path: Path, target_index: int, printer_type: Optional[str] = None) -> Path:
        """
        Asynchronously sanitizes the provided 3MF file.
        Injects the target tool index directly into G-code and Metadata.
        
        Args:
            source_path (Path): Absolute path to the source .3mf file.
            target_index (int): The 0-based AMS slot index (0-15) to force.
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
            return await loop.run_in_executor(None, self._sync_sanitize, source_path, target_index, printer_type)
        except Exception as e:
            logger.error(f"Failed to sanitize file {source_path}: {e}", exc_info=True)
            raise FileSanitizationError(f"Sanitization failed: {str(e)}") from e

    def _sync_sanitize(self, source_path: Path, target_index: int, printer_type: Optional[str] = None) -> Path:
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
        
        try:
            with zipfile.ZipFile(source_path, "r") as source_zip, \
                 zipfile.ZipFile(temp_output_path, "w", compression=zipfile.ZIP_DEFLATED) as target_zip:

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
                        modified_content = self._neutralize_metadata_json(original_content)
                        target_zip.writestr(item, modified_content)

                    # C. G-Code Normalization (Metadata/plate_*.gcode)
                    elif re.match(r"Metadata/plate_.*\.gcode$", file_name):
                        logger.debug(f"Normalizing G-Code in {file_name} -> T{target_index} (Type: {printer_type})")
                        original_gcode = source_zip.read(file_name)
                        new_gcode_content = self._normalize_gcode(original_gcode, target_index, printer_type)
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
                                    current_gcode_content = self._normalize_gcode(raw_gcode, target_index, printer_type)
                             except KeyError:
                                logger.warning(f"{expected_gcode_name} not found for MD5 calculation.")
                                current_gcode_content = b""

                        new_md5 = self._calculate_md5(current_gcode_content)
                        target_zip.writestr(item, new_md5)

                    # F. Slice Info Manifest (Metadata/slice_info.config) - NEW
                    elif re.match(r"Metadata/slice_info\.config$", file_name):
                         logger.debug(f"Synchronizing Slice Info for T{target_index}")
                         original_xml = source_zip.read(file_name)
                         new_xml = self._synchronize_metadata(original_xml, target_index)
                         target_zip.writestr(item, new_xml)

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

    def _synchronize_metadata(self, content: bytes, target_index: int) -> bytes:
        """
        Parses `slice_info.config` XML and forces exactly one filament entry.
        Reasoning: This prevents "Filament Mismatch" errors by removing strict checks
        and aligns with the T0-only G-code strategy.
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
                f_elem.set("type", "PLA")
                f_elem.set("color", "#FFFFFF")
                plate.append(f_elem)
            
            logger.info("Scrubbed manifest: Forced 4 'Generic PLA' filament entries (Native Strategy).")

            return ET.tostring(root, encoding="utf-8", xml_declaration=True)
                
        except Exception as e:
            logger.error(f"Failed to synchronize metadata: {e}")
            return content

    def _neutralize_metadata_json(self, content: bytes) -> bytes:
        """
        Parses JSON.
        Actions:
        - EXPAND to 5 generic filaments (Indices 0-4).
        - Randomize IDs.
        - Force PLA/White.
        """
        try:
            data = json.loads(content.decode("utf-8"))
            
            count = 5 # Cover generic slots 0-4

            # Generate random IDs to be absolutely sure no internal ID cache matches
            new_ids = [str(uuid.uuid4()) for _ in range(count)]
            
            data["filament_id"] = new_ids
            data["filament_type"] = ["PLA"] * count
            data["filament_colors"] = ["#FFFFFF"] * count
            data["filament_is_support"] = [False] * count
            
            return json.dumps(data, indent=4).encode("utf-8")
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse metadata JSON: {e}. Returning original.")
            return content

    def _normalize_gcode(self, content: bytes, target_index: int, printer_type: Optional[str] = None) -> bytes:
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
             final_text = self._inject_ejection_footer(final_text, printer_type)

        return final_text.encode("utf-8")

    def _inject_ejection_footer(self, gcode_text: str, printer_type: str) -> str:
        """
        Appends hardware-specific ejection sequence to the G-code.
        """
        p_type = printer_type.upper()
        footer = ""

        if "A1" in p_type:
            # A1 / A1 Mini: Y-Axis Fling
            footer = (
                "\n; --- FACTORYOS AUTO-EJECTION (A1 Fling) ---\n"
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
