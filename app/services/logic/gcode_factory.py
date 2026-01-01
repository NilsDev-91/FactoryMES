from abc import ABC, abstractmethod
from typing import Dict, Type
import logging

from app.models.core import Printer, PrinterTypeEnum

logger = logging.getLogger("GCodeFactory")

class ClearingStrategy(ABC):
    @abstractmethod
    def generate_code(self, printer: Printer, **kwargs) -> str:
        """Generate model-specific clearing G-Code."""
        pass

class A1SmartSweepStrategy(ClearingStrategy):
    """
    Phase 5: A1 Smart Gantry Sweep ("The Bulldozer").
    Uses the X-Axis Gantry to mechanically sweep parts off the bed.
    
    Physics Constants:
    - MIN_SWEEP_HEIGHT_MM: 50.0 - Parts below this height risk nozzle collision
    - SWEEP_RATIO: 0.8 - Gantry lowers to 80% of part height for mechanical grip
    - MIN_Z_HEIGHT: 15.0 - Absolute minimum Z to prevent bed crash
    """
    MIN_SWEEP_HEIGHT_MM = 50.0
    SWEEP_RATIO = 0.8
    MIN_Z_HEIGHT = 15.0
    
    def generate_code(self, printer: Printer, **kwargs) -> str:
        from app.core.exceptions import SafetyException
        
        # Get model height from kwargs (default to safe value)
        model_height_mm = kwargs.get('model_height_mm', 50.0)
        
        # Safety Check: Parts below MIN_SWEEP_HEIGHT are too risky for gantry sweep
        if model_height_mm < self.MIN_SWEEP_HEIGHT_MM:
            raise SafetyException(
                f"Part height {model_height_mm}mm is below minimum {self.MIN_SWEEP_HEIGHT_MM}mm for Smart Gantry Sweep. "
                f"Use standard inertial ejection instead."
            )
        
        # Calculate Sweep Height (80% of part height, but at least 15mm)
        sweep_height_z = max(self.MIN_Z_HEIGHT, model_height_mm * self.SWEEP_RATIO)
        
        thermal_temp = printer.thermal_release_temp or 28.0

        return "\n".join([
            "; --- STRATEGY: A1 SMART GANTRY SWEEP (BULLDOZER) ---",
            f"; Part Height: {model_height_mm}mm, Sweep Z: {sweep_height_z:.2f}mm",
            "M400      ; 0. Wait for buffer clear before cooldown",
            f"M190 R{thermal_temp} ; 1. Thermal Release (Wait for Bed Cool)",
            "M620 S255 ; 2. Enable Agitation Mode",
            "M621 S1   ;    Execute Shake (Break static friction)",
            "M400      ;    Wait for shake completion",
            "G1 X252 F12000 ; 3. Safety Park (Toolhead Far Right)",
            "G1 Y0 F12000   ; 4. Prep Position (Bed Fully Front)",
            "G90            ;    Absolute Positioning",
            f"G1 Z{sweep_height_z:.2f} F3000 ; 5. Form Barrier (Lower Gantry to {self.SWEEP_RATIO*100:.0f}% height)",
            "G1 Y250 F3000  ; 6. EXECUTE SWEEP (Bed Moves Back, Part hits Gantry)",
            "G1 Z50 F3000   ; 7. Raise Gantry (Release)",
            "M400",
            "; --- END STRATEGY ---"
        ])

class X1RammingStrategy(ClearingStrategy):
    """
    Strategy B: The "Ram"
    Mechanical sweeping macro for CoreXY Series (X1C, X1E, P1S, P1P).
    """
    def generate_code(self, printer: Printer, **kwargs) -> str:
        # P1/X1 Series: Mechanical Ramming
        return "\n".join([
            "; --- STRATEGY: X1 MECHANICAL SWEEP ---",
            "M106 P2 S255 ; Aux Fan 100% to assist detachment",
            "G28          ; Home all axes",
            "G90          ; Absolute positioning",
            "G1 Z10 F600  ; Safe Z height",
            "G1 X128 Y250 F12000 ; Move to safe clearance position (Rear Center)",
            "M400",
            "; INSERT CUSTOM RAMMING GCODE HERE",
            "; Users can inject specific motion based on their rammer design",
            "; Example: G1 Y0 F20000",
            "M400",
            "M106 P2 S0   ; Turn off Aux Fan",
            "; --- END STRATEGY ---"
        ])

class ManualStrategy(ClearingStrategy):
    """Fallback strategy"""
    def generate_code(self, printer: Printer, **kwargs) -> str:
        return "; MANUAL CLEARING STRATEGY - NO MOVES GENERATED"

class GCodeFactory:
    _STRATEGIES: Dict[PrinterTypeEnum, Type[ClearingStrategy]] = {
        PrinterTypeEnum.A1: A1SmartSweepStrategy,
        PrinterTypeEnum.A1_MINI: A1SmartSweepStrategy,
        PrinterTypeEnum.X1C: X1RammingStrategy,
        PrinterTypeEnum.X1E: X1RammingStrategy,
        PrinterTypeEnum.P1S: X1RammingStrategy,
        PrinterTypeEnum.P1P: X1RammingStrategy
    }

    @classmethod
    def get_strategy(cls, printer_type: PrinterTypeEnum) -> ClearingStrategy:
        strategy_class = cls._STRATEGIES.get(printer_type, ManualStrategy)
        logger.info(f"Selected {strategy_class.__name__} for {printer_type}")
        return strategy_class()
