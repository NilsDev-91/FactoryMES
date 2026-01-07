import logging

logger = logging.getLogger(__name__)

class A1Kinematics:
    """
    Single Source of Truth for A1 Mechanical Sequences.
    
    Validated Direction: 
    - Setup at Y256 (Bed Forward / Nozzle relative to Bed is at Back)
    - Sweep to Y0 (Bed Backward / Nozzle relative to Bed moves Forward)
    """
    
    # Absolute limits validated against hardware
    SAFE_Z_FLOOR = 2.0      # mm
    BEAM_OFFSET = 33.0      # mm (Height of Gantry beam above nozzle)
    GANTRY_THRESHOLD = 50.0 # mm (Min height for gantry use)

    @staticmethod
    def generate_sweep_sequence(height_mm: float) -> str:
        """
        Generates the G-Code for the Bed Clearing Sweep.
        Handles the logic for Gantry (Tall) vs Toolhead (Short) push.
        """
        if height_mm >= A1Kinematics.GANTRY_THRESHOLD:
            return A1Kinematics._gantry_sweep(height_mm)
        else:
            return A1Kinematics._toolhead_push(height_mm)

    @staticmethod
    def _gantry_sweep(height_mm: float) -> str:
        # Calculate leverage point (60% of part height), clamped to safe floor
        target_beam_z = height_mm * 0.6
        sweep_z = max(A1Kinematics.SAFE_Z_FLOOR, target_beam_z - A1Kinematics.BEAM_OFFSET)
        
        return f"""
; --- FACTORYOS A1 KINEMATICS: GANTRY SWEEP ---
; Part Height: {height_mm:.1f}mm | Target Z: {sweep_z:.2f}mm
M84 S0           ; Disable idle hold (Safety)
M140 S0          ; Bed Off
M106 P1 S255     ; Fan Max
M190 R28         ; Wait for release temp
G90              ; Absolute Mode
G28              ; Home All (Ensure accuracy)
G1 Z100 F3000    ; Lift Safe
G1 X-13.5 F12000 ; Park Toolhead (Cutter Area - Safe from collision)
G1 Y256 F12000   ; SETUP: Move Bed Forward (Nozzle is now at Back)
G1 Z{sweep_z:.2f} F3000 ; Lower Beam
M400             ; Wait for move
G1 Y0 F2000      ; ACTION: Move Bed Backward (Nozzle sweeps forward)
G1 Z100 F3000    ; Recovery Lift
G28              ; Re-Home
; -------------------------------------------
"""

    @staticmethod
    def _toolhead_push(height_mm: float) -> str:
        push_z = max(5.0, height_mm + 1.0) # Push slightly above part center or just above bed
        
        return f"""
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
