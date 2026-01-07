'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchJobs } from '@/lib/api/jobs';
import { JobTable } from '@/components/jobs/JobTable';
import { Job } from '@/types/job';
import { RefreshCw, Workflow, LayoutList, Filter } from 'lucide-react';

export default function JobsPage() {
    const { data: jobs, error, isLoading, refetch, isFetching } = useQuery<Job[]>({
        queryKey: ['jobs'],
        queryFn: fetchJobs,
        refetchInterval: 5000, // Auto-refresh every 5 seconds as requested
    });

    return (
        <div className="space-y-6 max-w-[1400px] mx-auto">
            {/* Header */}
            <header className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-blue-500/10 rounded-xl text-blue-500">
                        <Workflow size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Print Jobs</h1>
                        <p className="text-slate-400 text-sm">Monitor real-time factory execution state</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 rounded-lg border border-slate-700 text-[10px] font-bold text-slate-400 uppercase tracking-wider">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                        Auto-Refresh Active
                    </div>

                    <button
                        onClick={() => refetch()}
                        disabled={isFetching}
                        className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors border border-slate-700 font-medium text-sm disabled:opacity-50"
                    >
                        <RefreshCw size={16} className={isFetching ? "animate-spin" : ""} />
                        Manual Sync
                    </button>
                </div>
            </header>

            {/* Error State */}
            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg flex items-center gap-3">
                    <div className="p-2 bg-red-500/20 rounded-full">
                        <RefreshCw size={16} />
                    </div>
                    <div>
                        <p className="font-bold text-sm">Connection Error</p>
                        <p className="text-xs opacity-80">Failed to sync with factory execution service. Check backend connectivity.</p>
                    </div>
                </div>
            )}

            {/* Stats Overview (Optional but professional) */}
            {jobs && jobs.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    {[
                        { label: 'Total', value: jobs.length, color: 'bg-slate-500' },
                        { label: 'Printing', value: jobs.filter(j => j.status === 'PRINTING').length, color: 'bg-blue-500' },
                        { label: 'Pending', value: jobs.filter(j => j.status === 'PENDING').length, color: 'bg-yellow-500' },
                        { label: 'Success', value: jobs.filter(j => j.status === 'SUCCESS').length, color: 'bg-emerald-500' },
                    ].map((stat, idx) => (
                        <div key={idx} className="bg-slate-900 border border-slate-800 p-4 rounded-xl flex items-center justify-between">
                            <span className="text-slate-400 text-xs font-semibold uppercase tracking-wider">{stat.label}</span>
                            <div className="flex items-center gap-2">
                                <span className="text-xl font-bold text-white">{stat.value}</span>
                                <div className={`w-1 h-4 rounded-full ${stat.color}`} />
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Content Container */}
            <div className="relative">
                {isLoading && !jobs ? (
                    <div className="flex flex-col items-center justify-center p-20 text-slate-500 space-y-4">
                        <RefreshCw size={48} className="animate-spin text-blue-500 opacity-20" />
                        <p className="text-sm font-medium animate-pulse">Establishing data link...</p>
                    </div>
                ) : (
                    <JobTable jobs={jobs || []} />
                )}
            </div>
        </div>
    );
}
