import { Job } from '@/types/job';
import { API_BASE_URL } from '@/lib/api-client';

export async function fetchJobs(): Promise<Job[]> {
    const res = await fetch(`${API_BASE_URL}/jobs`);
    if (!res.ok) {
        throw new Error('Failed to fetch jobs');
    }
    return res.json();
}
