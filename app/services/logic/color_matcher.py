
import math
import logging
from typing import Tuple, Optional

logger = logging.getLogger("ColorMatcher")

class ColorMatcher:
    """
    Color Science Service - Phase 9
    Provides perceptually accurate color matching using CIEDE2000 (Delta E).
    """

    @staticmethod
    def hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
        """Convert hex string (e.g. '#FF0000' or 'FF0000FF') to RGB tuple."""
        hex_str = hex_str.lstrip('#')
        # Handle Bambu Lab's 8-char hex (RGBA), ignoring Alpha
        if len(hex_str) >= 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return r, g, b
        return 0, 0, 0

    @staticmethod
    def rgb_to_lab(r: int, g: int, b: int) -> Tuple[float, float, float]:
        """Convert RGB to LAB color space via XYZ."""
        # RGB to XYZ
        def pivot_rgb(n):
            n /= 255.0
            return math.pow((n + 0.055) / 1.055, 2.4) if n > 0.04045 else n / 12.92

        r, g, b = pivot_rgb(r), pivot_rgb(g), pivot_rgb(b)

        # Observer. = 2°, Illuminant = D65
        x = r * 0.4124 + g * 0.3576 + b * 0.1805
        y = r * 0.2126 + g * 0.7152 + b * 0.0722
        z = r * 0.0193 + g * 0.1192 + b * 0.9505

        # XYZ to LAB
        def pivot_xyz(n):
            return math.pow(n, 1/3) if n > 0.008856 else (7.787 * n) + (16 / 116)

        x, y, z = pivot_xyz(x / 0.95047), pivot_xyz(y / 1.00000), pivot_xyz(z / 1.08883)

        l = (116 * y) - 16
        a = 500 * (x - y)
        b_lab = 200 * (y - z)
        return l, a, b_lab

    @staticmethod
    def delta_e_cie2000(lab1: Tuple[float, float, float], lab2: Tuple[float, float, float]) -> float:
        """
        Implementation of CIEDE2000 Delta E algorithm.
        Returns the perceptual difference between two LAB colors.
        """
        L1, a1, b1 = lab1
        L2, a2, b2 = lab2

        kL = kC = kH = 1

        C1 = math.sqrt(a1**2 + b1**2)
        C2 = math.sqrt(a2**2 + b2**2)
        meanC = (C1 + C2) / 2

        G = 0.5 * (1 - math.sqrt(meanC**7 / (meanC**7 + 25**7)))

        a1p = (1 + G) * a1
        a2p = (1 + G) * a2

        C1p = math.sqrt(a1p**2 + b1**2)
        C2p = math.sqrt(a2p**2 + b2**2)

        h1p = math.degrees(math.atan2(b1, a1p)) % 360
        h2p = math.degrees(math.atan2(b2, a2p)) % 360

        dLp = L2 - L1
        dCp = C2p - C1p

        if C1p * C2p == 0:
            dhp = 0
        elif abs(h2p - h1p) <= 180:
            dhp = h2p - h1p
        elif h2p - h1p > 180:
            dhp = h2p - h1p - 360
        else:
            dhp = h2p - h1p + 360

        dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp / 2))

        meanLp = (L1 + L2) / 2
        meanCp = (C1p + C2p) / 2

        if C1p * C2p == 0:
            meanhp = h1p + h2p
        elif abs(h1p - h2p) <= 180:
            meanhp = (h1p + h2p) / 2
        elif h1p + h2p < 360:
            meanhp = (h1p + h2p + 360) / 2
        else:
            meanhp = (h1p + h2p - 360) / 2

        T = 1 - 0.17 * math.cos(math.radians(meanhp - 30)) + \
            0.24 * math.cos(math.radians(2 * meanhp)) + \
            0.32 * math.cos(math.radians(3 * meanhp + 6)) - \
            0.20 * math.cos(math.radians(4 * meanhp - 63))

        d_ro = 30 * math.exp(-((meanhp - 275) / 25)**2)
        RC = 2 * math.sqrt(meanCp**7 / (meanCp**7 + 25**7))
        SL = 1 + (0.015 * (meanLp - 50)**2) / math.sqrt(20 + (meanLp - 50)**2)
        SC = 1 + 0.045 * meanCp
        SH = 1 + 0.015 * meanCp * T
        RT = -math.sin(math.radians(2 * d_ro)) * RC

        delta_e = math.sqrt(
            (dLp / (kL * SL))**2 +
            (dCp / (kC * SC))**2 +
            (dHp / (kH * SH))**2 +
            RT * (dCp / (kC * SC)) * (dHp / (kH * SH))
        )

        return delta_e

    def is_color_match(self, target_hex: Optional[str], slot_hex: Optional[str], threshold: float = 45.0) -> bool:
        """
        Main entry point for color matching.
        Returns True if perceptual difference is within threshold.
        """
        if not target_hex or not slot_hex:
            return False
            
        try:
            rgb1 = self.hex_to_rgb(target_hex)
            rgb2 = self.hex_to_rgb(slot_hex)
            
            lab1 = self.rgb_to_lab(*rgb1)
            lab2 = self.rgb_to_lab(*rgb2)
            
            diff = self.delta_e_cie2000(lab1, lab2)
            result = diff <= threshold
            
            logger.debug(f"Color Match: Calculated dE={diff:.2f}, Threshold={threshold} => {'MATCH' if result else 'NO MATCH'}")
            return result
        except Exception as e:
            logger.error(f"Error in color matching: {e}")
            return False

# Singleton
color_matcher = ColorMatcher()
