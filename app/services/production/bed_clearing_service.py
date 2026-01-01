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

    def generate_clearing_gcode(self, printer: Printer, **kwargs) -> str:
        """
        Generates strategy-specific G-code for bed clearing using Dynamic Factory.
        Includes safety guards for temperature and state.
        """
        from app.services.logic.gcode_factory import GCodeFactory
        
        # 1. Safety Guards
        # Force cold nozzle to prevent oozing/drooping during clearing moves
        safety_header = [
            "; --- FACTORYOS SAFETY GUARDS ---",
            "M1002 gcode_claim_action : 0",
            "M109 S0   ; Cooldown nozzle immediately",
            "M140 S0   ; Turn off bed (redundant safety)",
            "G90       ; Absolute positioning",
            "M83       ; Relative extrusion",
            "M400",
            "; --- END SAFETY ---"
        ]

        # 2. Strategy Generation
        strategy = GCodeFactory.get_strategy(printer.type)
        strategy_code = strategy.generate_code(printer, **kwargs)

        return "\n".join(safety_header + [strategy_code] + ["M400"])

    def create_maintenance_3mf(self, printer: Printer, **kwargs) -> Path:
        """
        Packages the clearing G-code into a .3mf archive.
        """
        gcode_content = self.generate_clearing_gcode(printer, **kwargs)
        
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
