
import asyncio
import hashlib
import json
import logging
import re
import tempfile
import uuid
import zipfile
from pathlib import Path
from typing import List, Optional, Tuple, Any
import xml.etree.ElementTree as ET

logger = logging.getLogger("GcodeService")

class GcodeService:
    """
    Unified Service for G-Code Generation and 3MF Manipulation.
    Phase 12: Consolidated Production Loop logic.
    Follows "Async Iron Law" (offloading CPU-bound ZIP/Regex to threads).
    """

    # --- KINEMATIC CONSTANTS & SEQUENCES ---
    
    A1_GANTRY_SWEEP_TEMPLATE = """
; --- FACTORYOS A1 KINEMATICS: GANTRY SWEEP ---
; Part Height: {height_mm:.1f}mm | Target Z: {sweep_z:.2f}mm
M84 S0           ; Disable idle hold (Safety)
M140 S0          ; Bed Off
M106 P1 S255     ; Fan Max
M190 R28         ; Wait for release temp
G90              ; Absolute Mode
G28              ; Home All
G1 Z100 F3000    ; Lift Safe
G1 X-13.5 F12000 ; Park Toolhead
G1 Y256 F12000   ; SETUP: Bed Forward
G1 Z{sweep_z:.2f} F3000 ; Lower Beam
M400             
G1 Y0 F2000      ; ACTION: Sweep Forward
G1 Z100 F3000    ; Recovery Lift
G28              ; Re-Home
; -------------------------------------------
"""

    A1_TOOLHEAD_PUSH_TEMPLATE = """
; --- FACTORYOS A1 KINEMATICS: TOOLHEAD PUSH ---
M140 S0
M190 R28
G28
G1 Z100
G1 X128 Y256 F12000 ; Setup: Center Back
G1 Z{push_z:.2f}    ; Lower Nozzle
G1 Y0 F2000         ; ACTION: Push Forward
G28
; -------------------------------------------
"""

    X1_MECHANICAL_SWEEP_TEMPLATE = """
; --- STRATEGY: X1 MECHANICAL SWEEP ---
M140 S0
M106 P2 S255 ; Aux Fan 100%
G28          ; Home all
G90          
G1 Z10 F600  ; Safe Z
G1 X128 Y250 F12000 ; Rear Center
M400
G1 Y0 F20000      ; RAM ACTION
M400
M106 P2 S0   ; Fan Off
; -------------------------------------------
"""

    # --- CONFIGURATION ---
    
    EXCLUDED_FILES = {
        "Metadata/filament_sequence.json",
        "Metadata/model_settings.config"
    }

    def __init__(self, temp_dir: Optional[Path] = None):
        self.temp_root = temp_dir or Path(tempfile.gettempdir()) / "factoryos_gcode"
        self.temp_root.mkdir(exist_ok=True, parents=True)

    # --- Public API ---

    async def prepare_print_file(
        self, 
        source_path: Path, 
        printer_model: str, 
        target_slot_id: int,
        filament_color: str = "#FFFFFF",
        filament_type: str = "PLA",
        is_calibration_due: bool = True,
        part_height_mm: float = 0.0
    ) -> Path:
        """
        Orchestrates 3MF surgery:
        1. Offloads blocking ZIP operations to a thread.
        2. Sanitizes metadata and synchronizes AMS mapping.
        3. Injects model-specific clearing G-Code.
        """
        if not source_path.exists():
            raise FileNotFoundError(f"Source 3MF not found: {source_path}")

        # Unique temp output
        output_path = self.temp_root / f"prepared_{uuid.uuid4().hex[:8]}.3mf"
        
        logger.info(f"Preparing 3MF: {source_path.name} for {printer_model} (T{target_slot_id})")
        
        await asyncio.to_thread(
            self._sync_prepare_3mf,
            source_path,
            output_path,
            printer_model,
            target_slot_id,
            filament_color,
            filament_type,
            is_calibration_due,
            part_height_mm
        )
        
        return output_path

    async def create_maintenance_3mf(self, serial: str, printer_model: str, height_mm: float = 50.0) -> Path:
        """Creates a standalone maintenance 3MF for bed clearing."""
        output_path = self.temp_root / f"maint_{serial}_{uuid.uuid4().hex[:4]}.3mf"
        
        gcode = self._generate_clearing_gcode(printer_model, height_mm)
        gcode = self.inject_dynamic_seed(gcode)
        
        def _build_zip():
            with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
                z.writestr("Metadata/plate_1.gcode", gcode)
                config_xml = self._generate_minimal_config()
                z.writestr("Metadata/slice_info.config", config_xml)
                z.writestr("[Content_Types].xml", self._generate_content_types())
        
        await asyncio.to_thread(_build_zip)
        return output_path

    # --- Private Implementation (Sync/Threaded) ---

    def _sync_prepare_3mf(
        self,
        source: Path,
        target: Path,
        model: str,
        slot_id: int,
        color: str,
        material: str,
        cali_due: bool,
        height: float
    ):
        """Synchronous 3MF surgery core."""
        with zipfile.ZipFile(source, "r") as src_zip, \
             zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as dst_zip:
            
            # 1. Main Pass
            for item in src_zip.infolist():
                fname = item.filename
                
                if fname in self.EXCLUDED_FILES:
                    continue

                content = src_zip.read(fname)

                # A. Metadata JSON
                if re.match(r"Metadata/plate_.*\.json$", fname):
                    content = self._modify_metadata_json(content, slot_id, color, material)

                # B. Slice Info Config
                elif fname == "Metadata/slice_info.config":
                    content = self._modify_slice_info(content, slot_id, color, material)

                # C. G-Code Analysis & Injection
                elif re.match(r"Metadata/plate_.*\.gcode$", fname):
                    content = self._modify_gcode(content.decode("utf-8"), model, slot_id, cali_due, height).encode("utf-8")
                    
                    # Also update MD5 if present
                    md5_name = f"{fname}.md5"
                    if md5_name in src_zip.namelist():
                         dst_zip.writestr(md5_name, hashlib.md5(content).hexdigest())

                # D. Copy others
                if fname.endswith(".md5") and fname.replace(".md5", "") == "Metadata/plate_1.gcode":
                    # Handled above
                    continue
                
                dst_zip.writestr(item, content)

    @staticmethod
    def inject_dynamic_seed(gcode: str) -> str:
        """
        Appends a unique comment line to the G-code header.
        Forces the printer to treat it as a new job, bypassing internal MD5 cache.
        """
        seed_comment = f"; FACTORY_MES_SEED: {uuid.uuid4()}\n"
        return seed_comment + gcode

    def _modify_gcode(self, text: str, model: str, slot: int, cali_due: bool, height: float) -> str:
        """G-Code Modification Pipeline."""
        # 1. Tool Mapping (Regex replace T\d+ with T{slot})
        text = re.sub(r'\bT[0-9]+\b', f'T{slot}', text)
        
        # 2. M600 Sanitization
        text = re.sub(r'^.*M600.*$', r'; [M600 REMOVED]', text, flags=re.MULTILINE | re.IGNORECASE)
        
        # 3. Calibration Optimization
        if not cali_due:
            patterns = [r"^\s*G29", r"^\s*M968", r"^\s*M984", r".*;\s*Calibration.*"]
            for p in patterns:
                text = re.sub(p, lambda m: f"; [OPTIMIZED] {m.group(0)}", text, flags=re.MULTILINE | re.IGNORECASE)

        # 4. Identity Mapping / Native Select Injection (Inject after first G28)
        injection = (
            f"\n; --- FACTORYOS NATIVE SELECT ---\n"
            f"M1002 gcode_claim_action : 0\n"
            f"M620 S{slot}A  ; Select Physical Slot\n"
            f"T{slot}        ; Force Tool\n"
            f"M621 S{slot}A  ; Sync\n"
            f"; -----------------------------\n"
        )
        
        # Find first line starting with G28
        match = re.search(r'^\s*G28.*$', text, re.MULTILINE)
        if match:
            text = text[:match.end()] + injection + text[match.end():]
        else:
            text = "G28 ; Home\n" + injection + text

        # 5. Model-Specific End G-Code (Auto-Eject)
        if height > 0:
            clearing = self._generate_clearing_gcode(model, height)
            text += f"\n; --- AUTO-EJECT INJECTION ---\n{clearing}"

        return text

    def _generate_clearing_gcode(self, model: str, height: float) -> str:
        """Factory for model-specific clearing sequences."""
        if "A1" in model:
            if height >= 50.0:
                # Gantry Sweep
                sweep_z = max(2.0, (height * 0.6) - 33.0)
                return self.A1_GANTRY_SWEEP_TEMPLATE.format(height_mm=height, sweep_z=sweep_z)
            else:
                # Toolhead Push
                push_z = max(5.0, height + 1.0)
                return self.A1_TOOLHEAD_PUSH_TEMPLATE.format(push_z=push_z)
        
        elif "X1" in model or "P1" in model:
            return self.X1_MECHANICAL_SWEEP_TEMPLATE
            
        return "; NO CLEARING STRATEGY FOR MODEL: " + model

    def _modify_metadata_json(self, content: bytes, slot: int, color: str, material: str) -> bytes:
        try:
            data = json.loads(content.decode("utf-8"))
            count = 5
            data["filament_id"] = [str(uuid.uuid4()) for _ in range(count)]
            data["filament_type"] = ["PLA"] * count
            data["filament_colors"] = ["#FFFFFF"] * count
            
            if 0 <= slot < count:
                data["filament_type"][slot] = material
                data["filament_colors"][slot] = color
                
            return json.dumps(data, indent=4).encode("utf-8")
        except:
            return content

    def _modify_slice_info(self, content: bytes, slot: int, color: str, material: str) -> bytes:
        try:
            root = ET.fromstring(content)
            plate = root.find(".//plate")
            if plate is not None:
                # Clear and force 4 slots
                for f in plate.findall("filament"):
                    plate.remove(f)
                
                for i in range(1, 5):
                    f_elem = ET.Element("filament")
                    f_elem.set("id", str(i))
                    if (i - 1) == slot:
                        f_elem.set("type", material)
                        f_elem.set("color", color)
                    else:
                        f_elem.set("type", "PLA")
                        f_elem.set("color", "#FFFFFF")
                    plate.append(f_elem)
            return ET.tostring(root, encoding="utf-8", xml_declaration=True)
        except:
            return content

    def _generate_minimal_config(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<config>
  <plate>
    <filament id="1" type="PLA" color="#FFFFFF"/>
  </plate>
  <metadata key="gcode_path" value="Metadata/plate_1.gcode"/>
</config>"""

    def _generate_content_types(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="gcode" ContentType="text/x.gcode"/>
  <Default Extension="config" ContentType="application/xml"/>
</Types>"""
