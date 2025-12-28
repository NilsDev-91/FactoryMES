import React, { useMemo } from 'react';
import useSWR from 'swr';
import PrinterCard from '../PrinterCard';
import { Filter, Activity, Power, AlertCircle, Server } from 'lucide-react';
import { fetchPrinters } from '../../api';

// SWR Fetcher Wrapper
const fetcher = () => fetchPrinters();

const DashboardGrid = ({ initialPrinters = [] }) => {
    // Use SWR for data fetching with polling
    const { data: printers, error, isLoading } = useSWR('printers', fetcher, {
        fallbackData: initialPrinters,
        refreshInterval: 3000,
        keepPreviousData: true,
        revalidateOnFocus: true
    });

    const activeData = printers || [];

    // Memoized Stats Calculation (Efficient O(N))
    const stats = useMemo(() => {
        return activeData.reduce((acc, p) => {
            const status = (p.current_status || 'offline').toLowerCase();

            if (status === 'printing') {
                acc.printing++;
                acc.online++;
            } else if (['idle', 'ready', 'finish', 'prepare'].includes(status)) {
                acc.online++;
            } else {
                acc.offline++;
            }
            return acc;
        }, { online: 0, printing: 0, offline: 0 });
    }, [activeData]);

    if (isLoading && !activeData.length) return <div className="text-slate-500">Loading Fleet Data...</div>;
    if (error && !activeData.length) return <div className="text-red-500">Failed to load fleet data. Is the backend running?</div>;

    return (
        <div className="space-y-6">

            {/* Farm Overview Header */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatBadge icon={Power} label="Online" value={stats.online} color="bg-blue-500/10 border-blue-500/20 text-blue-400" />
                <StatBadge icon={Activity} label="Printing" value={stats.printing} color="bg-green-500/10 border-green-500/20 text-green-400" />
                <StatBadge icon={AlertCircle} label="Offline" value={stats.offline} color="bg-slate-800/50 border-slate-700 text-slate-500 opacity-75" />
            </div>

            {/* Controls Bar */}
            <div className="flex justify-between items-center bg-slate-800/50 p-3 rounded-lg border border-slate-700/50">
                <span className="text-sm font-medium text-slate-400">Fleet Status</span>
                <button className="flex items-center gap-2 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-md border border-slate-600 transition-colors">
                    <Filter size={14} /> Filter
                </button>
            </div>

            {/* Auto-fill Optimized Grid */}
            <div className="grid gap-4" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
                {activeData.map((printer) => (
                    // Pass raw printer object directly to allow strict prop comparison in child
                    <PrinterCard
                        key={printer.serial || printer.id}
                        printer={printer}
                    />
                ))}
            </div>
        </div>
    );
};

// Helper Component
const StatBadge = ({ icon: Icon, label, value, color }) => (
    <div className={`p-4 rounded-lg border flex items-center justify-between ${color}`}>
        <div className="flex flex-col">
            <span className="text-xs font-medium opacity-80 uppercase tracking-wider">{label}</span>
            <span className="text-2xl font-bold">{value}</span>
        </div>
        <Icon className="opacity-50" size={24} />
    </div>
);

export default DashboardGrid;
