export interface AmsSlot {
    id?: string;
    ams_index: number;
    slot_index: number;
    tray_color?: string; // Hex, e.g. "FF0000"
    tray_type?: string;
    remaining_percent?: number;
}

export interface Printer {
    serial: string;
    name: string;
    ip_address?: string;
    type: string; // "P1S", "A1", etc.
    current_status: string; // "IDLE", "PRINTING", etc.
    current_progress?: number;
    remaining_time?: number;
    current_temp_nozzle?: number;
    current_temp_bed?: number;
    ams_inventory?: AmsSlot[]; // Legacy or New? Backend says ams_slots usually. Prompt says ams_inventory.
    ams_slots?: AmsSlot[]; // Support both for safety during migration
    is_plate_cleared?: boolean;
}
