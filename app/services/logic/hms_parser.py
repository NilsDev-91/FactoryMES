"""
HMS Parser Service - Phase 7: The Watchdog

Parses Bambu Lab Health Management System (HMS) hex codes from MQTT
and returns structured error events for automation control.

HMS Code Format: XXXX-XXXX-XXXX-XXXX
- First segment indicates module (0700=AMS, 0300=Motion, etc.)
- Remaining segments provide error specifics

Reference: Bambu Lab Wiki HMS Error Codes
"""
import logging
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from datetime import datetime, timezone

logger = logging.getLogger("HMSParser")


class ErrorSeverity(str, Enum):
    """Severity levels for HMS events."""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class ErrorModule(str, Enum):
    """Hardware modules that can report errors."""
    AMS = "AMS"
    MOTION = "MOTION"
    HOMING = "HOMING"
    CHAMBER = "CHAMBER"
    NOZZLE = "NOZZLE"
    BED = "BED"
    UNKNOWN = "UNKNOWN"


class HMSEvent(BaseModel):
    """Structured representation of an HMS error."""
    code: str
    severity: ErrorSeverity
    description: str
    module: ErrorModule
    raw_code: str  # Original hex string
    timestamp: datetime = None
    
    def __init__(self, **data):
        if data.get('timestamp') is None:
            data['timestamp'] = datetime.now(timezone.utc)
        super().__init__(**data)


# HMS Code Mapping - Source of Truth
# Format: "PREFIX" -> (Module, Severity, Description Template)
# Prefix is first 4 characters of HMS code
HMS_CODE_MAP: Dict[str, tuple] = {
    # === AMS / Filament Issues (0700) ===
    "0700": (ErrorModule.AMS, ErrorSeverity.WARNING, "AMS Filament Issue"),
    
    # === Motion Controller Issues (0300) ===
    "0300": (ErrorModule.MOTION, ErrorSeverity.CRITICAL, "Motion Controller Error (Stall/Collision)"),
    
    # === Homing Issues (0500) ===
    "0500": (ErrorModule.HOMING, ErrorSeverity.CRITICAL, "Axis Homing Failure"),
    
    # === Chamber/Temperature Issues (0C00) ===
    "0C00": (ErrorModule.CHAMBER, ErrorSeverity.WARNING, "Chamber Temperature Issue"),
    
    # === Nozzle Issues (0200) ===
    "0200": (ErrorModule.NOZZLE, ErrorSeverity.WARNING, "Nozzle/Hotend Issue"),
    
    # === Bed Issues (0400) ===
    "0400": (ErrorModule.BED, ErrorSeverity.WARNING, "Heated Bed Issue"),
}

# Specific code overrides for detailed descriptions
HMS_SPECIFIC_CODES: Dict[str, tuple] = {
    # AMS Specific
    "0700-2000-0002-0002": (ErrorModule.AMS, ErrorSeverity.CRITICAL, "AMS Slot 1 Empty / Feed Failure"),
    "0700-2000-0002-0003": (ErrorModule.AMS, ErrorSeverity.CRITICAL, "AMS Slot 2 Empty / Feed Failure"),
    "0700-2000-0002-0004": (ErrorModule.AMS, ErrorSeverity.CRITICAL, "AMS Slot 3 Empty / Feed Failure"),
    "0700-2000-0002-0005": (ErrorModule.AMS, ErrorSeverity.CRITICAL, "AMS Slot 4 Empty / Feed Failure"),
    "0700-4500-0001-0001": (ErrorModule.AMS, ErrorSeverity.CRITICAL, "AMS Cutter Stuck / Step Loss"),
    "0700-4500-0001-0002": (ErrorModule.AMS, ErrorSeverity.CRITICAL, "AMS Cutter Motor Stall"),
    "0700-0100-0001-0001": (ErrorModule.AMS, ErrorSeverity.WARNING, "AMS Filament Runout Detected"),
    "0700-0200-0001-0001": (ErrorModule.AMS, ErrorSeverity.WARNING, "AMS Filament Tangle Detected"),
    
    # Motion Specific
    "0300-0100-0001-0001": (ErrorModule.MOTION, ErrorSeverity.CRITICAL, "X-Axis Motor Stall"),
    "0300-0100-0001-0002": (ErrorModule.MOTION, ErrorSeverity.CRITICAL, "Y-Axis Motor Stall"),
    "0300-0100-0001-0003": (ErrorModule.MOTION, ErrorSeverity.CRITICAL, "Z-Axis Motor Stall"),
    "0300-0200-0001-0001": (ErrorModule.MOTION, ErrorSeverity.CRITICAL, "Gantry Collision Detected"),
    "0300-0300-0001-0001": (ErrorModule.MOTION, ErrorSeverity.CRITICAL, "Motor Step Loss Detected"),
    
    # Homing Specific
    "0500-0100-0001-0001": (ErrorModule.HOMING, ErrorSeverity.CRITICAL, "X-Axis Homing Timeout"),
    "0500-0100-0001-0002": (ErrorModule.HOMING, ErrorSeverity.CRITICAL, "Y-Axis Homing Timeout"),
    "0500-0100-0001-0003": (ErrorModule.HOMING, ErrorSeverity.CRITICAL, "Z-Axis Homing Timeout"),
}


class HMSParser:
    """
    Parses HMS error codes from Bambu Lab printers.
    
    Usage:
        parser = HMSParser()
        events = parser.parse(["0700-2000-0002-0002", "0300-0100-0001-0001"])
        for event in events:
            if event.severity == ErrorSeverity.CRITICAL:
                # Handle critical error
    """
    
    def __init__(self):
        self._last_codes: Dict[str, set] = {}  # serial -> set of active codes (for idempotency)
    
    def parse(self, hms_codes: List[Any]) -> List[HMSEvent]:
        """
        Parse a list of HMS hex codes and return structured events.
        Handles both List[str] and List[dict] (MQTT format).
        """
        events = []
        
        for item in hms_codes:
            code = None
            if isinstance(item, str):
                code = item
            elif isinstance(item, dict):
                code = item.get("code")
                
            if not code or not isinstance(code, str):
                continue
                
            event = self._parse_single(code)
            if event:
                events.append(event)
                
        return events
    
    def _parse_single(self, code: str) -> Optional[HMSEvent]:
        """Parse a single HMS code."""
        code = code.upper().strip()
        
        # Try specific code first
        if code in HMS_SPECIFIC_CODES:
            module, severity, description = HMS_SPECIFIC_CODES[code]
            return HMSEvent(
                code=code,
                severity=severity,
                description=description,
                module=module,
                raw_code=code
            )
        
        # Fall back to prefix matching
        prefix = code[:4] if len(code) >= 4 else code
        
        if prefix in HMS_CODE_MAP:
            module, severity, description = HMS_CODE_MAP[prefix]
            return HMSEvent(
                code=code,
                severity=severity,
                description=f"{description} ({code})",
                module=module,
                raw_code=code
            )
        
        # Unknown code
        logger.warning(f"Unknown HMS code: {code}")
        return HMSEvent(
            code=code,
            severity=ErrorSeverity.WARNING,
            description=f"Unknown Hardware Error ({code})",
            module=ErrorModule.UNKNOWN,
            raw_code=code
        )
    
    def get_most_severe(self, events: List[HMSEvent]) -> Optional[HMSEvent]:
        """Return the most severe event from a list."""
        if not events:
            return None
            
        severity_order = {
            ErrorSeverity.CRITICAL: 3,
            ErrorSeverity.WARNING: 2,
            ErrorSeverity.INFO: 1
        }
        
        return max(events, key=lambda e: severity_order.get(e.severity, 0))
    
    def has_critical(self, events: List[HMSEvent]) -> bool:
        """Check if any event is CRITICAL severity."""
        return any(e.severity == ErrorSeverity.CRITICAL for e in events)
    
    def filter_by_module(self, events: List[HMSEvent], module: ErrorModule) -> List[HMSEvent]:
        """Filter events by module."""
        return [e for e in events if e.module == module]
    
    def is_new_error(self, serial: str, code: str) -> bool:
        """
        Check if this error code is new for this printer (idempotency).
        Returns True if code is new, False if already seen.
        """
        if serial not in self._last_codes:
            self._last_codes[serial] = set()
        
        if code in self._last_codes[serial]:
            return False
        
        self._last_codes[serial].add(code)
        return True
    
    def clear_errors(self, serial: str):
        """Clear tracked errors for a printer (after error acknowledgement)."""
        if serial in self._last_codes:
            self._last_codes[serial].clear()


# Singleton instance for global use
hms_parser = HMSParser()
