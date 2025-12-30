
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
