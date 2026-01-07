
import logging
import numpy as np
from typing import List, Optional, Any, Dict, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.filament import Filament
from app.models import Printer

logger = logging.getLogger("FilamentService")

class FilamentError(Exception):
    """Base exception for filament service errors."""
    pass

class FilamentNotFoundError(FilamentError):
    """Raised when a required filament match cannot be found."""
    pass

class AMSSyncError(FilamentError):
    """Raised when AMS synchronization fails."""
    pass

class FilamentService:
    """
    Filament Management Service (FMS) - Unified logic for color matching and AMS syncing.
    Follows the "Guardian Protocol" for data integrity and "Async Iron Law" for DB I/O.
    """

    KNOWN_COLORS = {
        "#000000": "Black",
        "000000": "Black",
        "#000000FF": "Black",
        "000000FF": "Black",
        "#FF0000": "Red",
        "FF0000": "Red",
        "#FF0000FF": "Red",
        "FF0000FF": "Red",
        "#FFFFFF": "White",
        "FFFFFF": "White",
        "#0000FF": "Blue",
        "0000FF": "Blue"
    }

    def __init__(self, session: AsyncSession):
        """
        Initializes the service with a database session.
        
        Args:
            session: The asynchronous database session.
        """
        self.session = session

    # --- Color Math Logic (Delta E 2000) ---

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> np.ndarray:
        """
        Convert hex string to RGB numpy array (0-1 range).
        """
        hex_color = hex_color.lstrip('#')
        if len(hex_color) >= 8:
            hex_color = hex_color[:6]
        
        if len(hex_color) != 6:
            raise ValueError(f"Invalid hex color format: {hex_color}")
            
        return np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)]) / 255.0

    @staticmethod
    def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
        """
        Convert sRGB (0-1) to CIE Lab.
        """
        res = rgb.copy()
        mask = res > 0.04045
        res[mask] = ((res[mask] + 0.055) / 1.055) ** 2.4
        res[~mask] = res[~mask] / 12.92
        
        M = np.array([
            [0.4124564, 0.3575761, 0.1804375],
            [0.2126729, 0.7151522, 0.0721750],
            [0.0193339, 0.1191920, 0.9503041]
        ])
        XYZ = res @ M.T
        
        Xn, Yn, Zn = 0.95047, 1.00000, 1.08883
        XYZ = XYZ / np.array([Xn, Yn, Zn])
        
        mask = XYZ > 0.008856
        XYZ[mask] = XYZ[mask] ** (1/3)
        XYZ[~mask] = (7.787 * XYZ[~mask]) + (16/116)
        
        L = 116 * XYZ[1] - 16
        a = 500 * (XYZ[0] - XYZ[1])
        b = 200 * (XYZ[1] - XYZ[2])
        
        return np.array([L, a, b])

    def calculate_delta_e(self, hex_a: str, hex_b: str) -> float:
        """
        Calculate CIEDE2000 color difference between two hex strings.
        """
        try:
            rgb_a = self._hex_to_rgb(hex_a)
            rgb_b = self._hex_to_rgb(hex_b)
            
            lab_a = self._rgb_to_lab(rgb_a)
            lab_b = self._rgb_to_lab(rgb_b)
            
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
            dh_prime = 0
            if C1_prime * C2_prime != 0:
                diff = h2_prime - h1_prime
                if abs(diff) <= 180: dh_prime = diff
                elif diff > 180: dh_prime = diff - 360
                elif diff < -180: dh_prime = diff + 360
            dH_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(dh_prime / 2))
            L_bar_prime = (L1 + L2) / 2
            C_bar_prime = (C1_prime + C2_prime) / 2
            if C1_prime * C2_prime != 0:
                if abs(h1_prime - h2_prime) <= 180: h_bar_prime = (h1_prime + h2_prime) / 2
                elif abs(h1_prime - h2_prime) > 180 and (h1_prime + h2_prime) < 360: h_bar_prime = (h1_prime + h2_prime + 360) / 2
                else: h_bar_prime = (h1_prime + h2_prime - 360) / 2
            else: h_bar_prime = h1_prime + h2_prime
            T = 1 - 0.17 * np.cos(np.radians(h_bar_prime - 30)) + \
                0.24 * np.cos(np.radians(2 * h_bar_prime)) + \
                0.32 * np.cos(np.radians(3 * h_bar_prime + 6)) - \
                0.20 * np.cos(np.radians(4 * h_bar_prime - 63))
            dTheta = 30 * np.exp(-((h_bar_prime - 275) / 25)**2)
            Rc = 2 * np.sqrt(C_bar_prime**7 / (C_bar_prime**7 + 25**7))
            SL = 1 + (0.015 * (L_bar_prime - 50)**2) / np.sqrt(20 + (L_bar_prime - 50)**2)
            SC = 1 + 0.045 * C_bar_prime
            SH = 1 + 0.015 * C_bar_prime * T
            RT = -np.sin(np.radians(2 * dTheta)) * Rc
            delta_e = np.sqrt(
                (dL_prime / (kL * SL))**2 +
                (dC_prime / (kC * SC))**2 +
                (dH_prime / (kH * SH))**2 +
                RT * (dC_prime / (kC * SC)) * (dH_prime / (kH * SH))
            )
            return float(delta_e)
        except Exception as e:
            logger.error(f"Error calculating Delta E: {e}")
            return 999.0

    # --- AMS Synchronization ---

    async def sync_ams_configuration(self, printer_id: str, ams_payload: Dict[str, Any]):
        """
        Updates the Printer.ams_config with the current AMS state from MQTT.
        """
        try:
            ams_list = ams_payload.get("ams", [])
            
            # Fetch the printer
            stmt = select(Printer).where(Printer.serial == printer_id)
            res = await self.session.execute(stmt)
            printer = res.scalars().first()
            if not printer:
                logger.error(f"Printer {printer_id} not found during AMS sync")
                return

            # Fetch filaments to resolve names
            filaments_res = await self.session.execute(select(Filament))
            filaments = filaments_res.scalars().all()
            
            new_config = {}
            
            # 2. Iterate through AMS units and trays
            for ams_idx, ams_unit in enumerate(ams_list):
                trays = ams_unit.get("tray", [])
                for tray_data in trays:
                    if not tray_data or "id" not in tray_data:
                        continue
                        
                    slot_index = int(tray_data["id"])
                    slot_id = str((ams_idx * 4) + slot_index)
                    
                    hex_val = tray_data.get("tray_color")
                    material = tray_data.get("tray_type")
                    
                    if not hex_val:
                        # Empty slot
                        continue
                    
                    new_config[slot_id] = {
                        "color_hex": hex_val,
                        "material": material,
                        "remaining_percent": int(tray_data.get("remain", 0)),
                        "color_name": self._resolve_color_name(hex_val, material, filaments)
                    }

            # Update printer
            printer.ams_config = new_config
            self.session.add(printer)
            await self.session.flush()
            logger.info(f"AMS configuration synced for printer {printer_id}: {list(new_config.keys())}")
            
        except Exception as e:
            logger.error(f"Failed to sync AMS configuration for {printer_id}: {e}")
            raise AMSSyncError(f"AMS sync failed: {str(e)}")

    def _resolve_color_name(self, hex_val: str, material: str, filaments: List[Filament]) -> Optional[str]:
        """Helper to resolve a human-readable color name using the filaments table."""
        if not hex_val:
            return None
            
        norm_hex = hex_val.lstrip("#")[:6].upper()
        
        # 1. Check Filaments Table
        for f in filaments:
            if f.material == material and f.color_hex.lstrip("#")[:6].upper() == norm_hex:
                return f.color_name
                    
        # 2. Check Known Colors Map
        lookup_key = f"#{norm_hex}"
        if lookup_key in self.KNOWN_COLORS:
            return self.KNOWN_COLORS[lookup_key]
            
        return None

    # --- Best Match Engine ---

    async def find_best_match_for_job(
        self, 
        target_color_hex: str, 
        material_type: str, 
        printer_id: str
    ) -> Optional[int]:
        """
        Finds the best matching slot ID on a specific printer.
        Returns the slot ID (0-3 for AMS) or None.
        """
        stmt = select(Printer).where(Printer.serial == printer_id)
        result = await self.session.execute(stmt)
        printer = result.scalars().first()
        
        if not printer or not printer.ams_config:
            return None
        
        best_slot_id = None
        min_delta_e = 5.0 # Threshold for "acceptable" match
        
        for slot_id, config in printer.ams_config.items():
            if config.get("material") != material_type:
                continue
                
            if config.get("remaining_percent", 0) < 5:
                continue
                
            slot_color = config.get("color_hex")
            if not slot_color:
                continue
                
            de = self.calculate_delta_e(target_color_hex, slot_color)
            
            if de < min_delta_e:
                min_delta_e = de
                best_slot_id = int(slot_id)
                
            if de == 0:
                break # Perfect match found
                
        return best_slot_id
