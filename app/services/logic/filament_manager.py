
import numpy as np
from typing import Optional, List, Tuple
from sqlmodel import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.core import Printer, PrinterStatusEnum, Job
from app.models.filament import AmsSlot

# --- Color Math Helpers (Numpy Implementation) ---

def _hex_to_rgb(hex_color: str) -> np.ndarray:
    """
    Convert hex string to RGB numpy array (0-1 range).
    """
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 8:
        hex_color = hex_color[:6]
    
    return np.array([int(hex_color[i:i+2], 16) for i in (0, 2, 4)]) / 255.0

def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """
    Convert sRGB (0-1) to CIE Lab.
    Uses D65 illuminant and 2 degree observer.
    """
    # 1. Linearize sRGB
    mask = rgb > 0.04045
    rgb[mask] = ((rgb[mask] + 0.055) / 1.055) ** 2.4
    rgb[~mask] = rgb[~mask] / 12.92
    
    # 2. sRGB to XYZ
    M = np.array([
        [0.4124564, 0.3575761, 0.1804375],
        [0.2126729, 0.7151522, 0.0721750],
        [0.0193339, 0.1191920, 0.9503041]
    ])
    XYZ = rgb @ M.T
    
    # 3. XYZ to Lab (Reference D65)
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
    """
    Calculate CIEDE2000 color difference between two hex strings using Numpy.
    """
    try:
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
            if abs(diff) <= 180:
                dh_prime = diff
            elif diff > 180:
                dh_prime = diff - 360
            elif diff < -180:
                dh_prime = diff + 360
                
        dH_prime = 2 * np.sqrt(C1_prime * C2_prime) * np.sin(np.radians(dH_prime / 2))
        
        L_bar_prime = (L1 + L2) / 2
        C_bar_prime = (C1_prime + C2_prime) / 2
        
        h_bar_prime = h1_prime + h2_prime
        if C1_prime * C2_prime != 0:
            if abs(h1_prime - h2_prime) <= 180:
                h_bar_prime = h_bar_prime / 2
            elif abs(h1_prime - h2_prime) > 180 and (h1_prime + h2_prime) < 360:
                h_bar_prime = (h_bar_prime + 360) / 2
            elif abs(h1_prime - h2_prime) > 180:
                h_bar_prime = (h_bar_prime - 360) / 2
        else:
             h_bar_prime = h1_prime + h2_prime
        
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
        print(f"Error calculating Delta E: {e}")
        return 999.0

# --- Service Logic ---

class FilamentManager:
    """
    The Brain of the Filament Management System (FMS).
    Matches jobs to printers based on filament requirements.
    """

    async def find_best_printer(
        self, 
        session: AsyncSession, 
        job: Job,
        product: Optional[any] = None # Avoid circular import if Product generic, or use forward ref
    ) -> Optional[Tuple[Printer, List[int]]]:
        """
        Finds the best idle printer for a given job.
        
        Args:
            session: Async DB session.
            job: The job to schedule.
            product: The product associated with the job (optional optimization vs lazy load).
            
        Returns:
            Tuple[Printer, List[int]]: (Best Printer, AMS Mapping) or None.
        """
        
        # Step A: Fetch Candidates
        query = (
            select(Printer)
            .where(Printer.current_status == PrinterStatusEnum.IDLE)
            .options(selectinload(Printer.ams_slots))
        )
        result = await session.execute(query)
        candidates = result.scalars().all()

        if not candidates:
            return None

        # Step B: Get Requirements
        requirements = self._get_job_requirements(job, product)
        
        if not requirements:
            # If no filament required, return first idle printer with empty mapping
            return candidates[0], []

        # Step C & D: Iterate and Match
        for printer in candidates:
            ams_mapping = self._match_printer(printer, requirements)
            if ams_mapping is not None:
                return printer, ams_mapping

        return None

    def _get_job_requirements(self, job: Job, product: Optional[any] = None) -> List[dict]:
        """
        Extracts filament requirements from the job.
        """
        # 0. Prioritize Job-Specific Requirements (e.g. from Order Processor overrides)
        if getattr(job, "filament_requirements", None):
             return [
                {
                    "material": r.get("material", "PLA"),
                    "hex_color": r.get("hex_color", "#000000"),
                    "virtual_id": r.get("virtual_id", 0)
                }
                for r in job.filament_requirements
             ]

        # product passed explicitly or try to find it
        if not product:
             product = getattr(job, "product", None)
        
        # Fallback if product not directly on job (e.g. check order items)
        if not product and job.order and job.order.items:
             # Logic to find product from order items would go here
             pass

        if not product:
            return []

        # Check for 'filament_requirements' list (New Model)
        if hasattr(product, "filament_requirements") and product.filament_requirements:
            return [
                {
                    "material": r.material,
                    "hex_color": r.hex_color,
                    "virtual_id": getattr(r, "virtual_slot_id", i)
                }
                for i, r in enumerate(product.filament_requirements)
            ]
        
        # Fallback to legacy fields (V1 Model)
        material = getattr(product, "required_filament_type", "PLA")
        color = getattr(product, "required_filament_color", None)
        
        if material and color:
            return [{"material": material, "hex_color": color, "virtual_id": 0}]
        
        return []

    def _match_printer(self, printer: Printer, requirements: List[dict]) -> Optional[List[int]]:
        """
        Checks if a printer satisfies all requirements.
        Returns the mapping list if valid, else None.
        """
        mapping = [None] * len(requirements)
        used_physical_slots = set()
        
        # Sort requirements by virtual_id
        sorted_reqs = sorted(requirements, key=lambda x: x.get('virtual_id', 0))
        
        for i, req in enumerate(sorted_reqs):
            req_material = req['material']
            req_color = req['hex_color']
            
            match_found = False
            best_slot_index = -1
            min_delta_e = 5.0 # Threshold
            
            for slot in printer.ams_slots:
                # Calculate global slot index (0-15)
                # ams_index (0-3) * 4 + slot_index (0-3)
                pid = slot.ams_index * 4 + slot.slot_index
                
                if pid in used_physical_slots:
                    continue
                
                # 1. Strict Material Match
                if not slot.tray_type or slot.tray_type.lower() != req_material.lower():
                    continue
                
                # 2. Color Match
                if not slot.tray_color:
                    continue
                    
                delta_e = calculate_delta_e_2000(req_color, slot.tray_color)
                
                if delta_e < min_delta_e:
                    min_delta_e = delta_e
                    best_slot_index = pid
                    match_found = True
            
            if match_found:
                mapping[i] = best_slot_index
                used_physical_slots.add(best_slot_index)
            else:
                return None # Fail

        return mapping
