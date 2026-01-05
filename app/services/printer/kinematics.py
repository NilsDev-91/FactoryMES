import logging
from app.schemas.job import PartMetadata
from app.core.exceptions import StrategyNotApplicableError

logger = logging.getLogger("Kinematics")

class KinematicSafetyError(StrategyNotApplicableError):
    """Raised when kinematic constraints are violated."""
    pass

class A1Kinematics:
    """
    User-Defined Kinematics for Bambu Lab A1 series.
    Consolidates movement logic for autonomous ejection.
    """
    
    # --- Validated Geometry ---
    GANTRY_OFFSET_MM = 33.0   # Physical distance Nozzle-to-Beam
    SWEEP_OVERLAP_MM = 5.0    # Required contact depth
    MIN_PART_HEIGHT_MM = 40.0 # Safety threshold
    SAFE_Z_FLOOR_MM = 2.0     # Final Z floor for nozzle
    
    @staticmethod
    def _calculate_sweep_z(part_height_mm: float) -> float:
        """
        Calculates the required Nozzle Z height to position the beam
        at the target contact zone.
        
        Math:
        Example: 40mm Part -> Target Beam 35mm -> Nozzle Z 2.0mm.
        calc_z = part_height - (GANTRY_OFFSET + SWEEP_OVERLAP)
        """
        if part_height_mm < A1Kinematics.MIN_PART_HEIGHT_MM:
            logger.warning(f"Part height {part_height_mm}mm < {A1Kinematics.MIN_PART_HEIGHT_MM}mm. Gantry Sweep unsafe.")
            raise KinematicSafetyError(f"Part height {part_height_mm}mm below safe limit of {A1Kinematics.MIN_PART_HEIGHT_MM}mm.")
            
        # Target Beam Height: part_height_mm - SWEEP_OVERLAP_MM
        # Nozzle Z = Target Beam - GANTRY_OFFSET
        calc_z = part_height_mm - (A1Kinematics.GANTRY_OFFSET_MM + A1Kinematics.SWEEP_OVERLAP_MM)
        
        # Clamp to floor
        return max(A1Kinematics.SAFE_Z_FLOOR_MM, calc_z)

    @staticmethod
    def generate_a1_gantry_sweep_gcode(meta: PartMetadata) -> str:
        """
        Implements the robust "Gantry Sweep" logic.
        Strictly adhering to user constraints and geometric safety.
        """
        # Pre-Condition: Bed cooldown is handled by MQTTWorker Thermal Watchdog.
        # This G-code assumes it is being executed on a cold bed (< 28C).
        
        target_z = A1Kinematics._calculate_sweep_z(meta.height_mm)
        
        return f"""
; --- STRATEGY: A1_GANTRY_SWEEP (User Defined) ---
; Protocol: A1 Gantry Sweep v1.3 | Height: {meta.height_mm}mm | Target Z: {target_z:.1f}
; Calculation: {meta.height_mm}mm - (33.0 offset + 5.0 overlap) = {meta.height_mm - 38.0:.1f}mm (Clamped to {A1Kinematics.SAFE_Z_FLOOR_MM}mm)

; 1. SAFETY: Disable Sensors & Heaters
M140 S0 ; Bed Off
M104 S0 ; Nozzle Off
M412 S0 ; Disable Filament Runout sensor
M975 S0 ; Disable Step Loss Recovery

; 2. POSITIONING
G90 ; Absolute Positioning
G1 X-13.5 F18000 ; Park X-Min (Safe Park)
G1 Y0 F12000      ; Align Bed: Bed ALL THE WAY BACK
G1 Z{target_z:.1f} F3000   ; Engage Z: Lower beam to contact zone
M400 ; Sync

; 3. EXECUTE
G1 Y256 F1500     ; THE SWEEP: Move Bed Forward (Push part off front)
M400 ; Sync

; 4. CLEANUP & RECOVERY
G1 Z20 F3000      ; Lift Z for clearance
G28               ; Re-home to reset coordinate system
; --- END SWEEP ---
"""
