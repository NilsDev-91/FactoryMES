import { FilamentProfile } from '@/types/api/filament';

export interface MaterialAvailability {
    hex_code: string;
    material: string;
    color_name: string;
    ams_slots: string[];
}

const API_BASE = 'http://127.0.0.1:8000/api';

export async function fetchAvailableMaterials(): Promise<MaterialAvailability[]> {
    const res = await fetch(`${API_BASE}/fms/ams/available-materials`);
    if (!res.ok) {
        throw new Error('Failed to fetch available materials');
    }
    return res.json();
}

export async function fetchFilamentProfiles(): Promise<FilamentProfile[]> {
    const res = await fetch(`${API_BASE}/fms/profiles`);
    if (!res.ok) {
        throw new Error('Failed to fetch filament profiles');
    }
    return res.json();
}

export async function createFilamentProfile(data: {
    brand: string;
    material: string;
    color_hex: string;
    density?: number;
    spool_weight?: number;
}): Promise<FilamentProfile> {
    const res = await fetch(`${API_BASE}/fms/profiles`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!res.ok) {
        throw new Error('Failed to create filament profile');
    }
    return res.json();
}

