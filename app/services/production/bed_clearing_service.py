import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
import xml.etree.ElementTree as ET

from app.models.core import Printer, ClearingStrategyEnum

logger = logging.getLogger("BedClearingService")

class BedClearingService:
    def __init__(self):
        self.temp_dir = Path(tempfile.gettempdir()) / "factoryos_maintenance"
        self.temp_dir.mkdir(exist_ok=True)

    def generate_clearing_gcode(self, printer: Printer) -> str:
        """
        Generates strategy-specific G-code for bed clearing.
        """
        strategy = printer.clearing_strategy
        
        gcode = [
            "; --- FACTORYOS AUTO-CLEARING ---",
            "M1002 gcode_claim_action : 0",
            "M400 ; Finish moves",
            "G90 ; Absolute positioning",
            "M83 ; Relative extrusion",
        ]

        if strategy == ClearingStrategyEnum.A1_INERTIAL_FLING:
            # A1 "Y-Axis Fling" strategy
            # Move X to center, then rapid Y moves
            gcode += [
                "G1 X128 Y200 F12000 ; Move to back center",
                "M400",
                "; --- THE FLING ---",
                "G1 Y250 F12000",
                "G1 Y10 F18000 ; Rapid forward",
                "G1 Y250 F18000 ; Rapid backward",
                "G1 Y10 F21000 ; Even faster forward",
                "M400",
                "G1 X20 Y50 F12000 ; Success position",
            ]

        elif strategy == ClearingStrategyEnum.X1_MECHANICAL_SWEEP:
            # X1 "Mechanical Sweep" strategy
            # CRITICAL: Z-Hop 2mm above max layer or just safe height
            gcode += [
                "G1 Z10 F600 ; Safe Z height",
                "G1 X240 Y240 F12000 ; Move to rear far corner",
                "M400",
                "; --- THE SWEEP ---",
                "G1 X30 Y240 F12000 ; Sweep across while staying back",
                "G1 X30 Y30 F12000  ; Sweep forward",
                "G1 X240 Y30 F12000 ; Sweep across right",
                "M400",
                "G1 X240 Y240 F12000 ; Back to safety",
            ]
        
        else:
            # Fallback/Manual
            gcode.append("; Strategy MANUAL or unknown. No moves generated.")

        gcode.append("M400")
        gcode.append("; --- END AUTO-CLEARING ---")
        
        return "\n".join(gcode)

    def create_maintenance_3mf(self, printer: Printer) -> Path:
        """
        Packages the clearing G-code into a .3mf archive.
        """
        gcode_content = self.generate_clearing_gcode(printer)
        
        # Create a tiny 3MF structure
        output_path = self.temp_dir / f"clear_plate_{printer.serial}.3mf"
        
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
            # 1. G-code
            z.writestr("Metadata/plate_1.gcode", gcode_content)
            
            # 2. Minimal slice_info.config to satisfy parser
            config_xml = self._generate_minimal_config()
            z.writestr("Metadata/slice_info.config", config_xml)
            
            # 3. [Content_Types].xml
            z.writestr("[Content_Types].xml", self._generate_content_types())

        logger.info(f"Generated maintenance 3MF for {printer.serial} at {output_path}")
        return output_path

    def _generate_minimal_config(self) -> str:
        root = ET.Element("config")
        plate = ET.SubElement(root, "plate")
        # Add one dummy filament to keep firmware happy
        filament = ET.SubElement(plate, "filament")
        filament.set("id", "1")
        filament.set("type", "PLA")
        filament.set("color", "#FFFFFF")
        
        # Add metadata for gcode_path
        meta = ET.SubElement(root, "metadata")
        meta.set("key", "gcode_path")
        meta.set("value", "Metadata/plate_1.gcode")

        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode()

    def _generate_content_types(self) -> str:
        return """<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
 <Default Extension="gcode" ContentType="text/x.gcode"/>
 <Default Extension="config" ContentType="application/xml"/>
</Types>"""
