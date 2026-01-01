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
