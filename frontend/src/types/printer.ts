export interface AmsSlot {
    id?: string;
    ams_index: number;
    slot_index: number;
    color_hex?: string; // Hex, e.g. "FF0000"
    material?: string;
    remaining_percent?: number;
}

export interface Printer {
    serial: string;
    name: string;
    ip_address?: string;
    type: string; // "P1S", "A1", etc.
    current_status: string; // "IDLE", "PRINTING", "ERROR", etc.
    current_progress?: number;
    remaining_time?: number;
    current_temp_nozzle?: number;
    current_temp_bed?: number;
    ams_inventory?: AmsSlot[]; // Legacy or New? Backend says ams_slots usually. Prompt says ams_inventory.
    ams_slots?: AmsSlot[]; // Support both for safety during migration
    is_plate_cleared?: boolean;
    hardware_model?: string;
    can_auto_eject?: boolean;
    // Phase 7: HMS Watchdog Error Tracking
    last_error_code?: string;
    last_error_time?: string;
    last_error_description?: string;
}

