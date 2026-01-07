'use client';

import React from 'react';
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Printer as PrinterIcon, Clock, FileText, CheckCircle2, AlertTriangle, XCircle, RotateCcw } from 'lucide-react';
import { Job, JobStatus } from '@/types/job';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface JobTableProps {
    jobs: Job[];
    isLoading?: boolean;
}

export function JobTable({ jobs, isLoading }: JobTableProps) {
    const formatDate = (dateStr: string | null) => {
        if (!dateStr) return '-';
        try {
            const date = new Date(dateStr);
            return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        } catch (e) {
            return '-';
        }
    };

    const getStatusBadge = (status: JobStatus) => {
        switch (status) {
            case 'PENDING':
                return <Badge variant="warning">PENDING</Badge>;
            case 'PRINTING':
                return (
                    <Badge variant="info" className="animate-pulse">
                        PRINTING
                    </Badge>
                );
            case 'SUCCESS':
                return (
                    <Badge variant="success" className="flex items-center gap-1">
                        <CheckCircle2 size={12} /> SUCCESS
                    </Badge>
                );
            case 'NEEDS_CLEARING':
                return (
                    <Badge variant="warning" className="bg-orange-500/20 text-orange-400 border-orange-500/50 flex items-center gap-1">
                        <AlertTriangle size={12} /> NEEDS CLEARING
                    </Badge>
                );
            case 'FAILED':
                return (
                    <Badge variant="destructive" className="flex items-center gap-1">
                        <XCircle size={12} /> FAILED
                    </Badge>
                );
            default:
                return <Badge>{status}</Badge>;
        }
    };

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-slate-500">
                <RotateCcw className="animate-spin mb-4" />
                <p>Loading jobs...</p>
            </div>
        );
    }

    if (!jobs || jobs.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-slate-500 border border-slate-800 rounded-xl bg-slate-900/50 border-dashed">
                <FileText size={48} className="mb-4 opacity-50" />
                <p className="text-lg font-medium">No print jobs found</p>
                <p className="text-sm">Jobs will appear here once orders are processed.</p>
            </div>
        );
    }

    return (
        <div className="w-full rounded-xl border border-slate-800 bg-slate-900 shadow-xl overflow-hidden">
            <Table>
                <TableHeader className="bg-slate-950/50">
                    <TableRow className="border-slate-800 hover:bg-transparent">
                        <TableHead className="text-slate-200 font-semibold py-4 px-6">ID</TableHead>
                        <TableHead className="text-slate-200 font-semibold py-4 px-6">File</TableHead>
                        <TableHead className="text-slate-200 font-semibold py-4 px-6">Printer</TableHead>
                        <TableHead className="text-slate-200 font-semibold py-4 px-6">Material</TableHead>
                        <TableHead className="text-slate-200 font-semibold py-4 px-6">Started</TableHead>
                        <TableHead className="text-slate-200 font-semibold py-4 px-6">Finished</TableHead>
                        <TableHead className="text-slate-200 font-semibold py-4 px-6 text-center">Status</TableHead>
                    </TableRow>
                </TableHeader>
                <TableBody className="divide-y divide-slate-800">
                    {jobs.map((job) => (
                        <TableRow key={job.id} className="border-slate-800 hover:bg-slate-800/40 transition-colors">
                            <TableCell className="px-6 py-4 font-mono text-xs text-slate-400">
                                #{job.id}
                            </TableCell>
                            <TableCell className="px-6 py-4 max-w-[200px] truncate">
                                <div className="flex flex-col">
                                    <span className="text-slate-200" title={job.file_path}>
                                        {job.file_path.split('/').pop()}
                                    </span>
                                    <span className="text-[10px] text-slate-500 truncate">{job.file_path}</span>
                                </div>
                            </TableCell>
                            <TableCell className="px-6 py-4">
                                {job.printer_id ? (
                                    <div className="flex items-center gap-2 text-slate-300">
                                        <PrinterIcon size={14} className="text-slate-500" />
                                        <span>{job.printer_id}</span>
                                    </div>
                                ) : (
                                    <span className="text-slate-600 italic text-xs">Unassigned</span>
                                )}
                            </TableCell>
                            <TableCell className="px-6 py-4">
                                <div className="flex items-center gap-2">
                                    {job.required_color_hex && (
                                        <div
                                            className="w-3 h-3 rounded-full border border-slate-700"
                                            style={{ backgroundColor: job.required_color_hex }}
                                        />
                                    )}
                                    <span className="text-slate-300 text-xs">{job.required_material}</span>
                                </div>
                            </TableCell>
                            <TableCell className="px-6 py-4 text-xs text-slate-400">
                                <div className="flex items-center gap-1">
                                    <Clock size={12} /> {formatDate(job.started_at)}
                                </div>
                            </TableCell>
                            <TableCell className="px-6 py-4 text-xs text-slate-400">
                                {formatDate(job.finished_at)}
                            </TableCell>
                            <TableCell className="px-6 py-4 text-center">
                                {getStatusBadge(job.status)}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </div>
    );
}
