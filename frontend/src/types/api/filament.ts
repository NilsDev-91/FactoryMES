/**
 * Filament Profile Types
 */

export interface FilamentProfile {
    id: string;
    name: string;
    material: string;
    color_hex: string;
    color_name?: string;
    brand?: string;
    price_per_kg?: number;
    density?: number;
}

