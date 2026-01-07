
export type JobStatus =
    | 'PENDING'
    | 'UPLOADING'
    | 'PRINTING'
    | 'FINISHED'
    | 'BED_CLEARING'
    | 'COMPLETED'
    | 'FAILED';

export interface FilamentReq {
    material: string;
    hex_color: string;
    virtual_id: number;
}

export interface JobMetadata {
    is_auto_eject_enabled?: boolean;
    detected_height?: number;
    model_height_mm?: number;
    part_height_mm?: number;
}

export interface Job {
    id: number;
    status: JobStatus;
    filament_requirements?: FilamentReq[];
    job_metadata?: JobMetadata;
}

export interface JobHistory extends Job {
    completed_at?: string;
}
