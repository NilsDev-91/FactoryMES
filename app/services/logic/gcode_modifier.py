import re
import logging

logger = logging.getLogger("GCodeModifier")

class GCodeModifier:
    """
    Intelligent G-Code optimization service.
    Phase 5: Smart Calibration Logic (Dynamic start-up checks).
    """

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
            logger.info("Calibration DUE: Returning G-Code untouched.")
            return gcode_text

        logger.info("Calibration SKIPPED: Optimizing Start G-Code...")
        
        lines = gcode_text.splitlines()
        optimized_lines = []
        
        # Regex patterns to comment out
        # G29: Bed Leveling
        # M968: Lidar/Flow Dynamics
        # M984: Resonance/Vibration
        # Any line containing "; Calibration"
        patterns = [
            r"^\s*G29",
            r"^\s*M968",
            r"^\s*M984", 
            r".*;\s*Calibration.*"
        ]
        
        compiled_patterns = [re.compile(p, re.IGNORECASE) for p in patterns]

        count = 0
        for line in lines:
            should_comment = False
            for p in compiled_patterns:
                if p.match(line) or ("; Calibration" in line and not line.strip().startswith(";")): 
                     # Note: The regex r".*;\s*Calibration.*" matches lines with the comment.
                     # But we should also check if it's NOT already commented (to avoid double commenting)
                     # Although ; G29 is fine.
                     # The prompt says "re lines containing G29...".
                     should_comment = True
                     break
            
            if should_comment and not line.strip().startswith(";"):
                optimized_lines.append(f"; [OPTIMIZED] {line}")
                count += 1
            else:
                optimized_lines.append(line)
        
        logger.info(f"Optimization Complete: Commented out {count} calibration lines.")
        return "\n".join(optimized_lines)
