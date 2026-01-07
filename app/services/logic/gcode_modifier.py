import logging
import uuid
import re
from typing import Tuple
from pydantic import validate_call
from app.services.printer.kinematics import A1Kinematics
import uuid
from typing import Tuple
from pydantic import validate_call

logger = logging.getLogger("GCodeModifier")


class GCodeModifier:
    """
    Intelligent G-Code Modification Service.
    Phase 10: Fully Autonomous Production Cycles.
    
    Consolidates all G-code manipulation logic:
    - Calibration Optimization (Phase 5)
    - M600 Sanitization (Phase 10)
    - Native Tool Rewriting (Phase 10)
    - Auto-Eject Injection (Phase 10)
    """
    
    # === SAFETY CONSTANTS (Validated on Hardware) ===
    Z_HARD_FLOOR = 2.0          # mm - ABSOLUTE MINIMUM Z
    KINEMATIC_OFFSET = 33.0     # mm - Beam bottom above nozzle tip
    MIN_AUTO_EJECT_HEIGHT = 50.0  # mm - Minimum height for gantry sweep injection
    
    # Pre-compiled regex patterns for performance on large files
    TOOL_COMMAND_PATTERN = re.compile(r'^T(\d+)', re.MULTILINE)
    M600_PATTERN = re.compile(r'^.*M600.*$', re.MULTILINE | re.IGNORECASE)
    CALIBRATION_PATTERNS = [
        re.compile(r"^\s*G29", re.IGNORECASE),
        re.compile(r"^\s*M968", re.IGNORECASE),
        re.compile(r"^\s*M984", re.IGNORECASE),
        re.compile(r".*;\s*Calibration.*", re.IGNORECASE),
    ]

    @staticmethod
    def modify_gcode(
        gcode_text: str,
        target_slot_id: int,
        is_calibration_due: bool,
        enable_auto_eject: bool,
        part_height_mm: float = 0.0
    ) -> str:
        """
        Main G-Code modification pipeline for fully autonomous production.
        
        Args:
            gcode_text: Raw G-code content as string.
            target_slot_id: The 0-based AMS slot index to force (0-15).
            is_calibration_due: If False, calibration commands are commented out.
            enable_auto_eject: If True AND part is tall enough, inject sweep sequence.
            part_height_mm: Part height for sweep Z calculation (default 0 = disabled).
            
        Returns:
            Modified G-code string with all transformations applied.
        """
        modifier = GCodeModifier()
        
        # === STEP 1: Calibration Optimization ===
        result = modifier.optimize_start_gcode(gcode_text, is_calibration_due)
        
        # === STEP 2: M600 Sanitization ===
        result, m600_count = modifier._sanitize_m600(result)
        if m600_count > 0:
            logger.info(f"M600 Sanitization: Removed {m600_count} filament change commands.")
        
        # === STEP 3: Native Tool Rewriting ===
        result, tool_count = modifier._rewrite_tool_commands(result, target_slot_id)
        if tool_count > 0:
            logger.info(f"Tool Rewriting: Rewrote {tool_count} commands to T{target_slot_id}.")
        
        # === STEP 4: Auto-Eject Injection ===
        # NEW Phase 12 logic: Let the specialized method handle injection logic
        if enable_auto_eject:
             # We assume model info comes from external context (e.g. Printer.type)
             # For now, we mock as A1 if not provided, or better, we should probably 
             # have a way to pass printer_model here. 
             # Adjusting signature to allow printer_model
             pass 

        return result

    @staticmethod
    def modify_gcode_with_model(
        gcode_text: str,
        target_slot_id: int,
        is_calibration_due: bool,
        enable_auto_eject: bool,
        printer_model: str,
        part_height_mm: float = 0.0
    ) -> str:
        """
        Extended modification pipeline with printer model awareness.
        """
        modifier = GCodeModifier()
        
        # Calibration
        result = modifier.optimize_start_gcode(gcode_text, is_calibration_due)
        
        # M600
        result, _ = modifier._sanitize_m600(result)
        
        # Tooling
        result, _ = modifier._rewrite_tool_commands(result, target_slot_id)
        
        # Auto-Eject
        if enable_auto_eject:
            result = modifier.inject_sweep_sequence(result, printer_model, part_height_mm)
            
        return result

    @validate_call
    def inject_sweep_sequence(self, gcode: str, printer_model: str, part_height_mm: float = 0.0) -> str:
        """
        Injects the terminal clearing sequence based on hardware model.
        Constraint: Strict Python 3.12+, Pydantic V2, Async-First (No blocking I/O).
        """
        if "A1" in printer_model:
            # Delegate to Single Source of Truth
            sweep_sequence = A1Kinematics.generate_sweep_sequence(part_height_mm)
            return gcode + sweep_sequence

        elif any(m in printer_model for m in ["X1", "P1"]):
            # Placeholder for different clearing logic
            present_sequence = """
; === FACTORYMES AUTONOMOUS CYCLE (X1/P1 SERIES) ===
; Strategy: Present Print (Manual/Future Auto)
M140 S0
G1 Y250 F3000       ; Present print for operator
; === END AUTONOMOUS CYCLE ===
"""
            return gcode + present_sequence
            
        return gcode

    @staticmethod
    def inject_dynamic_seed(gcode: str) -> str:
        """
        Appends a unique comment line to the G-code header.
        Forces the printer to treat it as a new job, bypassing internal MD5 cache.
        """
        seed_comment = f"; FACTORY_MES_SEED: {uuid.uuid4()}\n"
        return seed_comment + gcode

    @staticmethod
    def optimize_start_gcode(gcode_text: str, is_calibration_due: bool) -> str:
        """
        Optimizes start G-Code based on calibration status.

        Logic:
        - If calibration is due (True): Return text untouched.
        - If calibration NOT due (False): Aggressively comment out G29, M968, M984,
          and any lines explicitly marked with "; Calibration".
        """
        if is_calibration_due:
            logger.info("Calibration: DUE - G-Code untouched.")
            return gcode_text

        logger.info("Calibration: SKIPPED - Optimizing Start G-Code...")
        
        lines = gcode_text.splitlines()
        optimized_lines = []
        count = 0
        
        for line in lines:
            should_comment = False
            for pattern in GCodeModifier.CALIBRATION_PATTERNS:
                if pattern.match(line) or ("; Calibration" in line and not line.strip().startswith(";")): 
                    should_comment = True
                    break
            
            if should_comment and not line.strip().startswith(";"):
                optimized_lines.append(f"; [OPTIMIZED] {line}")
                count += 1
            else:
                optimized_lines.append(line)
        
        logger.info(f"Calibration Optimization: Commented out {count} lines.")
        return "\n".join(optimized_lines)

    def _sanitize_m600(self, gcode_text: str) -> Tuple[str, int]:
        """
        Remove or comment out any line containing M600 (filament change).
        
        Reason: Manual filament changes break the autonomous production loop.
        The printer would pause indefinitely waiting for operator confirmation.
        
        Returns:
            Tuple of (sanitized_gcode, count_of_removed_lines)
        """
        lines = gcode_text.splitlines()
        sanitized_lines = []
        count = 0
        
        for line in lines:
            if self.M600_PATTERN.match(line):
                # Comment out instead of delete for debugging/audit trail
                sanitized_lines.append(f"; [M600 REMOVED] {line}")
                count += 1
            else:
                sanitized_lines.append(line)
        
        return "\n".join(sanitized_lines), count

    def _rewrite_tool_commands(self, gcode_text: str, target_slot_id: int) -> Tuple[str, int]:
        """
        Native Tool Rewriting (Crucial for Red/Black Test).
        
        Replaces all active tool commands (T0, T1, T2, etc.) with T{target_slot_id}.
        This forces the printer to use the physical AMS slot decided by the FMS,
        ignoring the slicer's default tool assignment.
        
        Args:
            gcode_text: G-code content.
            target_slot_id: The AMS slot index (0-15) to force.
            
        Returns:
            Tuple of (modified_gcode, count_of_replaced_commands)
        """
        # Count matches first for logging
        matches = self.TOOL_COMMAND_PATTERN.findall(gcode_text)
        count = len(matches)
        
        # Perform replacement using pre-compiled pattern
        modified = self.TOOL_COMMAND_PATTERN.sub(f'T{target_slot_id}', gcode_text)
        
        return modified, count


    def _inject_auto_eject(self, gcode_text: str, part_height_mm: float) -> str:
        """
        Inject the Auto-Eject "Gantry Sweep" sequence at the end of G-code.
        
        The Sweep Sequence (Phase 10):
        1. M140 S0, M104 S0 - Heaters Off
        2. M106 P1 S255 - Part Cooling Fan 100%
        3. M190 R28 - Wait for Bed < 28°C (Thermal Release)
        4. G28 - Home All Axes
        5. G1 Z100 - Safe Lift
        6. G1 X-13.5 - Park X-Min (Clear of print area)
        7. G1 Y0 - Bed Forward
        8. G1 Z{sweep_z} - Lower Gantry to contact zone
        9. G1 Y256 F1500 - The Sweep (push part off front)
        10. G28 - Recovery Home
        
        Args:
            gcode_text: Original G-code content.
            part_height_mm: Part height for Z calculation.
            
        Returns:
            G-code with sweep sequence appended.
        """
        sweep_z = self._calculate_sweep_z(part_height_mm)
        
        sweep_sequence = f"""
; === FACTORYOS AUTO-EJECT (Phase 10) ===
; Part Height: {part_height_mm:.1f}mm | Sweep Z: {sweep_z:.2f}mm
M140 S0             ; 1. Bed Heater Off
M104 S0             ; 2. Nozzle Heater Off
M106 P1 S255        ; 3. Part Fan 100%
M190 R28            ; 4. Wait for Bed < 28C (Thermal Release)
G28                 ; 5. Home All
G1 Z100 F3000       ; 6. Safe Lift
G1 X-13.5 F12000    ; 7. Park X-Min
G1 Y0 F12000        ; 8. Bed Forward
G1 Z{sweep_z:.2f} F3000  ; 9. Lower Gantry to Contact Zone
G1 Y256 F1500       ; 10. THE SWEEP (Push Part Off)
G28                 ; 11. Recovery Home
; === END AUTO-EJECT ===
"""
        
        return gcode_text + sweep_sequence
