/**
 * Represents a filament material profile.
 */
export interface FilamentProfile {
    id: string; // UUID from backend
    brand: string;
    material: string; // e.g., "PLA"
    color_hex: string; // e.g., "#FF0000"
    density: number;
    spool_weight: number;
}
