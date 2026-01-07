export type JobStatus = 'PENDING' | 'PRINTING' | 'SUCCESS' | 'NEEDS_CLEARING' | 'FAILED';

export interface Job {
    id: number;
    file_path: string;
    printer_id: string | null;
    status: JobStatus;
    required_material: string;
    required_color_hex: string | null;
    used_ams_slot: number | null;
    started_at: string | null;
    finished_at: string | null;
    created_at: string;
}
