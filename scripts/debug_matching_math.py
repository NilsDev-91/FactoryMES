import numpy as np

def _hex_to_rgb(hex_color: str) -> np.ndarray:
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 8:
        hex_color = hex_color[:6]
    return np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)]) / 255.0

def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    mask = rgb > 0.04045
    rgb[mask] = ((rgb[mask] + 0.055) / 1.055) ** 2.4
    rgb[~mask] = rgb[~mask] / 12.92
    
    M = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041]
    ])
    XYZ = rgb @ M.T
    
    Xn, Yn, Zn = 0.95047, 1.00000, 1.08883
    XYZ = XYZ / np.array([Xn, Yn, Zn])
    
    mask = XYZ > 0.008856
    XYZ[mask] = XYZ[mask] ** (1/3)
    XYZ[~mask] = (7.787 * XYZ[~mask]) + (16/116)
    
    L = 116 * XYZ[1] - 16
    a = 500 * (XYZ[0] - XYZ[1])
    b = 200 * (XYZ[1] - XYZ[2])
    
    return np.array([L, a, b])

def calculate_delta_e_2000(hex_a: str, hex_b: str) -> float:
    # (Simplified wrapper for testing, using the complex implementation copied exactly if needed, 
    # but for now I'll just use the one from the file or a simplified euclidean key as a sanity check first, 
    # but actually I should copy the full logic to be sure.)
    # Copying full logic...
    
    rgb_a = _hex_to_rgb(hex_a)
    rgb_b = _hex_to_rgb(hex_b)
    lab_a = _rgb_to_lab(rgb_a)
    lab_b = _rgb_to_lab(rgb_b)
    
    L1, a1, b1 = lab_a
    L2, a2, b2 = lab_b
    
    kL = kC = kH = 1
    C1 = np.sqrt(a1**2 + b1**2)
    C2 = np.sqrt(a2**2 + b2**2)
    C_bar = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(C_bar**7 / (C_bar**7 + 25**7)))
    a1_prime = (1 + G) * a1
    a2_prime = (1 + G) * a2
    C1_prime = np.sqrt(a1_prime**2 + b1**2)
    C2_prime = np.sqrt(a2_prime**2 + b2**2)
    h1_prime = np.degrees(np.arctan2(b1, a1_prime)) % 360
    h2_prime = np.degrees(np.arctan2(b2, a2_prime)) % 360
    if C1_prime == 0: h1_prime = 0
    if C2_prime == 0: h2_prime = 0
    dL_prime = L2 - L1
    dC_prime = C2_prime - C1_prime
    dH_prime = 0
    if C1_prime * C2_prime != 0:
        diff = h2_prime - h1_prime
        if abs(diff) <= 180: dh_prime = diff
        elif diff > 180: dh_prime = diff - 360
        elif diff < -180: dh_prime = diff + 360
    dH_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(dH_prime / 2))
    L_bar_prime = (L1 + L2) / 2
    C_bar_prime = (C1_prime + C2_prime) / 2
    h_bar_prime = h1_prime + h2_prime
    if C1_prime * C2_prime != 0:
        if abs(h1_prime - h2_prime) <= 180: h_bar_prime = h_bar_prime / 2
        elif abs(h1_prime - h2_prime) > 180 and (h1_prime + h2_prime) < 360: h_bar_prime = (h_bar_prime + 360) / 2
        elif abs(h1_prime - h2_prime) > 180: h_bar_prime = (h_bar_prime - 360) / 2
    else: h_bar_prime = h1_prime + h2_prime
    T = 1 - 0.17 * np.cos(np.radians(h_bar_prime - 30)) + 0.24 * np.cos(np.radians(2 * h_bar_prime)) + 0.32 * np.cos(np.radians(3 * h_bar_prime + 6)) - 0.20 * np.cos(np.radians(4 * h_bar_prime - 63))
    dTheta = 30 * np.exp(-((h_bar_prime - 275) / 25)**2)
    Rc = 2 * np.sqrt(C_bar_prime**7 / (C_bar_prime**7 + 25**7))
    SL = 1 + (0.015 * (L_bar_prime - 50)**2) / np.sqrt(20 + (L_bar_prime - 50)**2)
    SC = 1 + 0.045 * C_bar_prime
    SH = 1 + 0.015 * C_bar_prime * T
    RT = -np.sin(np.radians(2 * dTheta)) * Rc
    delta_e = np.sqrt((dL_prime / (kL * SL))**2 + (dC_prime / (kC * SC))**2 + (dH_prime / (kH * SH))**2 + RT * (dC_prime / (kC * SC)) * (dH_prime / (kH * SH)))
    return float(delta_e)

def test_matching():
    # FROM DATABASE
    slots = [
        {"id": 0, "color": "76D9F4FF", "type": "PLA"}, # 0: Blue-ish?
        {"id": 1, "color": "000000FF", "type": "PLA"}, # 1: Black
        {"id": 2, "color": "C12E1FFF", "type": "PLA"}, # 2: Red
        {"id": 3, "color": "FFFFFFFF", "type": "PLA"}, # 3: White
    ]
    
    # REQUIREMENT (White Eye)
    req_color = "#FFFFFF" # Short hex
    req_material = "PLA"
    
    print(f"Goal: {req_color} ({req_material})")
    
    best_slot = -1
    min_de = 999.0
    
    for s in slots:
        if s["type"] != req_material:
            continue
            
        de = calculate_delta_e_2000(req_color, s["color"])
        print(f"Slot {s['id']} ({s['color']}): dE = {de:.4f}")
        
        if de < min_de:
            min_de = de
            best_slot = s["id"]
            
    print(f"WINNER: Slot {best_slot} (Index {best_slot})")

if __name__ == "__main__":
    test_matching()
