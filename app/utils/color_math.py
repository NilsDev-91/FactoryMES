import numpy as np


def hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    """
    Converts a hex string to an RGB tuple.
    Handles strings with or without '#' and is case-insensitive.
    """
    hex_str = hex_str.lstrip("#").upper()
    if len(hex_str) == 8:
        # Strip alpha channel if present
        hex_str = hex_str[:6]
    if len(hex_str) != 6:
        raise ValueError(f"Invalid hex color: {hex_str}")
    return tuple(int(hex_str[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_lab(r: int, g: int, b: int) -> tuple[float, float, float]:
    """
    Converts RGB to LAB color space.
    Assumes sRGB color space and D65 illuminant.
    """
    # Normalize RGB to [0, 1]
    _r = r / 255.0
    _g = g / 255.0
    _b = b / 255.0

    # Gamma correction to linear RGB
    def pivot_rgb(n):
        return ((n + 0.055) / 1.055) ** 2.4 if n > 0.04045 else n / 12.92

    _r = pivot_rgb(_r)
    _g = pivot_rgb(_g)
    _b = pivot_rgb(_b)

    # Linear RGB to XYZ (D65)
    x = _r * 0.4124564 + _g * 0.3575761 + _b * 0.1804375
    y = _r * 0.2126729 + _g * 0.7151522 + _b * 0.0721750
    z = _r * 0.0193339 + _g * 0.1191920 + _b * 0.9503041

    # XYZ to LAB
    # D65 White Point: x=0.95047, y=1.00000, z=1.08883
    xw, yw, zw = 0.95047, 1.00000, 1.08883

    def pivot_xyz(n):
        return n ** (1 / 3) if n > 0.008856 else (7.787 * n) + (16 / 116)

    fx = pivot_xyz(x / xw)
    fy = pivot_xyz(y / yw)
    fz = pivot_xyz(z / zw)

    lab_l = (116 * fy) - 16
    lab_a = 500 * (fx - fy)
    lab_b = 200 * (fy - fz)

    return (lab_l, lab_a, lab_b)


def calculate_delta_e(hex1: str, hex2: str) -> float:
    """
    Calculates the color distance between two hex colors using the CIEDE2000 algorithm.

    A result < 1.0 is generally unnoticeable to the human eye.
    A result < 5.0 is considered acceptable for our Filament Management System (FMS).

    Args:
        hex1: Hex color string (e.g., "#FFFFFF" or "FFFFFF")
        hex2: Hex color string (e.g., "#000000" or "000000")

    Returns:
        float: The Delta E distance (CIEDE2000).
    """
    lab1 = rgb_to_lab(*hex_to_rgb(hex1))
    lab2 = rgb_to_lab(*hex_to_rgb(hex2))

    # CIEDE2000 Implementation
    l1, a1, b1 = lab1
    l2, a2, b2 = lab2

    # Weighting factors
    kl, kc, kh = 1, 1, 1

    avg_lp = (l1 + l2) / 2
    c1 = np.sqrt(a1**2 + b1**2)
    c2 = np.sqrt(a2**2 + b2**2)
    avg_c = (c1 + c2) / 2

    g = 0.5 * (1 - np.sqrt(avg_c**7 / (avg_c**7 + 25**7)))

    a1p = (1 + g) * a1
    a2p = (1 + g) * a2

    c1p = np.sqrt(a1p**2 + b1**2)
    c2p = np.sqrt(a2p**2 + b2**2)
    avg_cp = (c1p + c2p) / 2

    def get_h(a, b):
        h = np.arctan2(b, a)
        return h + 2 * np.pi if h < 0 else h

    h1p = get_h(a1p, b1)
    h2p = get_h(a2p, b2)

    if abs(h1p - h2p) > np.pi:
        avg_hp = (h1p + h2p + 2 * np.pi) / 2 if (h1p + h2p) < 2 * np.pi else (h1p + h2p - 2 * np.pi) / 2
    else:
        avg_hp = (h1p + h2p) / 2

    t = (
        1
        - 0.17 * np.cos(avg_hp - np.deg2rad(30))
        + 0.24 * np.cos(2 * avg_hp)
        + 0.32 * np.cos(3 * avg_hp + np.deg2rad(6))
        - 0.20 * np.cos(4 * avg_hp - np.deg2rad(63))
    )

    delta_hp = h2p - h1p
    if abs(delta_hp) > np.pi:
        if h2p <= h1p:
            delta_hp += 2 * np.pi
        else:
            delta_hp -= 2 * np.pi

    delta_lp = l2 - l1
    delta_cp = c2p - c1p
    delta_Hp = 2 * np.sqrt(c1p * c2p) * np.sin(delta_hp / 2)

    sl = 1 + (0.015 * (avg_lp - 50) ** 2) / np.sqrt(20 + (avg_lp - 50) ** 2)
    sc = 1 + 0.045 * avg_cp
    sh = 1 + 0.015 * avg_cp * t

    delta_ro = np.deg2rad(30) * np.exp(-(((np.rad2deg(avg_hp) - 275) / 25) ** 2))
    rc = 2 * np.sqrt(avg_cp**7 / (avg_cp**7 + 25**7))
    rt = -np.sin(2 * delta_ro) * rc

    delta_e = np.sqrt(
        (delta_lp / (kl * sl)) ** 2
        + (delta_cp / (kc * sc)) ** 2
        + (delta_Hp / (kh * sh)) ** 2
        + rt * (delta_cp / (kc * sc)) * (delta_Hp / (kh * sh))
    )

    return float(delta_e)
