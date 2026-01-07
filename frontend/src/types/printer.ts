export interface AmsSlot {
    id?: string;
    ams_index: number;
    slot_index: number;
    color_hex?: string; // Hex, e.g. "FF0000"
    material?: string;
    remaining_percent?: number;
}

import { Job } from './job';

export interface Printer {
    serial: string;
    name: string;
    ip_address?: string;
    type: string;
    current_status: string;
    status?: string; // Alias for current_status (used by PrinterCard)
    current_progress?: number;
    progress?: number; // Alias for current_progress
    remaining_time?: number;
    remaining_time_min?: number; // Alias for remaining_time
    current_temp_nozzle?: number;
    current_temp_bed?: number;
    ams_inventory?: AmsSlot[];
    ams_slots?: AmsSlot[];
    is_plate_cleared?: boolean;
    hardware_model?: string;
    can_auto_eject?: boolean;
    thermal_release_temp?: number;
    clearing_strategy?: string;
    last_error_code?: string;
    last_error_time?: string;
    last_error_description?: string;
    last_job?: Job; // Support for Phase 10 clearance reasons
    telemetry?: {
        z_height?: number;
    };
}

