
import React from 'react';
import { X, Thermometer, Wind, Box, Play, Square, Download, Activity, FileText, Layers, Trash2 } from 'lucide-react';
import { mutate } from 'swr';
import { Printer } from '@/components/dashboard/PrinterCard';
import { LiveTelemetryCard } from '@/components/printers/LiveTelemetryCard';
import { cn } from '@/lib/utils'; // Assuming you might have a utils file, if not I'll inline.

// Inline util for now to be safe
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
function cnUtils(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface PrinterDetailModalProps {
    printer: Printer | null;
    isOpen: boolean;
    onClose: () => void;
}

export function PrinterDetailModal({ printer, isOpen, onClose }: PrinterDetailModalProps) {
    if (!isOpen || !printer) return null;

    const isPrinting = printer.current_status === 'PRINTING';

    const handleDelete = async () => {
        if (!confirm(`Are you sure you want to remove ${printer.name}? This cannot be undone.`)) return;

        try {
            const res = await fetch(`http://127.0.0.1:8000/api/printers/${printer.serial}`, {
                method: 'DELETE'
            });

            if (!res.ok) throw new Error('Failed to delete printer');

            onClose();
            mutate('http://127.0.0.1:8000/api/printers');
        } catch (e) {
            alert('Failed to delete printer');
        }
    };

    // Helper for AMS Slot Visuals
    const getAmsColor = (slotIdx: number) => {
        const slot = printer.ams_slots?.find(s => s.ams_index * 4 + s.slot_index === slotIdx); // Assuming simplistic mapping or just checking available slots
        // Better logic based on backend model:
        // Backend: ams_index (0-3), slot_index (0-3). 
        // Frontend Modal legacy code shows 4 slots [0,1,2,3]. Assuming single AMS unit for now.
        const targetSlot = printer.ams_slots?.find(s => s.slot_index === slotIdx);

        if (!targetSlot?.tray_color) return '#334155';
        let hex = targetSlot.tray_color;
        if (!hex.startsWith('#')) hex = '#' + hex;
        return hex.substring(0, 7);
    };

    return (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-slate-950/80 backdrop-blur-md transition-opacity animate-in fade-in duration-200"
                onClick={onClose}
            />

            {/* Modal Container */}
            <div className="relative bg-[#0a0f1a] border border-slate-800 rounded-3xl shadow-[0_0_50px_-12px_rgba(59,130,246,0.3)] w-full max-w-4xl max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-300">

                {/* Header - Industrial Style */}
                <div className="flex items-center justify-between p-8 border-b border-slate-800 bg-gradient-to-r from-slate-900/50 to-transparent">
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <h2 className="text-3xl font-black text-white tracking-tighter uppercase">{printer.name}</h2>
                            <span className={cnUtils("px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] shadow-lg",
                                isPrinting ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400 border border-slate-700'
                            )}>
                                {printer.current_status}
                            </span>
                        </div>
                        <div className="flex gap-4 text-xs font-mono text-slate-500">
                            {/* @ts-ignore: ip_address might be missing in type but present in API */}
                            <span className="flex items-center gap-1.5"><Activity size={12} /> {printer.ip_address || 'Unknown IP'}</span>
                            <span className="flex items-center gap-1.5">SN: {printer.serial}</span>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-3 text-slate-500 hover:text-white hover:bg-slate-800 rounded-2xl transition-all border border-transparent hover:border-slate-700"
                    >
                        <X size={24} />
                    </button>
                </div>

                <div className="p-8 overflow-y-auto max-h-[calc(90vh-120px)]">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-8">

                        {/* Section 1: Telemetry Grid */}
                        <div className="space-y-4">
                            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] flex items-center gap-2">
                                <Activity size={14} className="text-blue-500" /> System Telemetry
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <LiveTelemetryCard
                                    label="Nozzle Temp"
                                    value={printer.current_temp_nozzle}
                                    unit="°C"
                                    icon={Thermometer}
                                    color="orange"
                                />
                                <LiveTelemetryCard
                                    label="Bed Temp"
                                    value={printer.current_temp_bed}
                                    unit="°C"
                                    icon={Thermometer}
                                    color="orange"
                                />
                                <LiveTelemetryCard
                                    label="Chamber"
                                    value={32.4} // Mock
                                    unit="°C"
                                    icon={Box}
                                    color="emerald"
                                />
                                <LiveTelemetryCard
                                    label="Fan Speed"
                                    value={100} // Mock
                                    unit="%"
                                    icon={Wind}
                                    color="cyan"
                                />
                            </div>
                        </div>

                        {/* Section 2: AMS / Material */}
                        <div className="space-y-4">
                            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] flex items-center gap-2">
                                <Box size={14} className="text-purple-500" /> AMS Slots
                            </h3>
                            <div className="grid grid-cols-4 gap-3">
                                {[0, 1, 2, 3].map((slotIdx) => (
                                    <div key={slotIdx} className="bg-slate-900 border border-slate-800 p-4 rounded-2xl flex flex-col items-center gap-3">
                                        <div
                                            className="w-8 h-8 rounded-full border-2 border-slate-700 shadow-inner"
                                            style={{ backgroundColor: getAmsColor(slotIdx) }}
                                        />
                                        <span className="text-[10px] font-bold text-slate-500">S-{slotIdx + 1}</span>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* Section 3: Current Job */}
                        <div className="md:col-span-2 space-y-4 bg-slate-900/50 border border-slate-800 p-6 rounded-3xl relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-4 opacity-5 pointer-events-none">
                                <FileText size={120} />
                            </div>

                            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] flex items-center gap-2">
                                <FileText size={14} className="text-emerald-500" /> Active Job Execution
                            </h3>

                            {isPrinting ? (
                                <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-center">
                                    <div className="space-y-1">
                                        <p className="text-xs text-slate-500 font-mono">Filename</p>
                                        <p className="text-white font-bold truncate">Plate_Operations_v2.gcode</p>
                                    </div>
                                    <div className="flex gap-8">
                                        <div className="space-y-1 text-center">
                                            <p className="text-xs text-slate-500 font-mono flex items-center gap-1 justify-center"><Layers size={12} /> Layer</p>
                                            <p className="text-white font-bold">142<span className="text-slate-600 text-[10px] ml-1">/ 350</span></p>
                                        </div>
                                        <div className="space-y-1 text-center font-mono">
                                            <p className="text-xs text-slate-500">Progress</p>
                                            <p className="text-emerald-400 font-bold">{printer.current_progress}%</p>
                                        </div>
                                    </div>
                                    <div className="space-y-1 text-right font-mono">
                                        <p className="text-xs text-slate-500 italic">Remaining Time</p>
                                        <p className="text-2xl text-white font-black">{printer.remaining_time}m</p>
                                    </div>
                                    <div className="md:col-span-3 h-2 bg-slate-950 rounded-full overflow-hidden border border-slate-800">
                                        <div
                                            className="h-full bg-emerald-500 shadow-[0_0_10px_rgba(16,185,129,0.5)] transition-all duration-1000"
                                            style={{ width: `${printer.current_progress}%` }}
                                        />
                                    </div>
                                </div>
                            ) : (
                                <div className="py-8 flex flex-col items-center justify-center text-slate-600 gap-2">
                                    <Square size={32} strokeWidth={1} />
                                    <p className="text-sm font-mono tracking-widest uppercase">System Standby</p>
                                </div>
                            )}
                        </div>

                        {/* Section 4: Controls */}
                        <div className="md:col-span-2 grid grid-cols-4 gap-4">
                            <ControlButton label="Pause" icon={<Play size={20} />} className="hover:bg-amber-500/10 hover:text-amber-500 hover:border-amber-500/50" />
                            <ControlButton label="Stop" icon={<Square size={20} />} className="hover:bg-rose-500/10 hover:text-rose-500 hover:border-rose-500/50" />
                            <ControlButton label="Unload" icon={<Download size={20} />} className="hover:bg-blue-500/10 hover:text-blue-500 hover:border-blue-500/50" />
                            <ControlButton
                                label="Delete"
                                icon={<Trash2 size={20} />}
                                className="hover:bg-red-500/10 hover:text-red-500 hover:border-red-500/50"
                                onClick={handleDelete}
                            />
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
};

interface ControlButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    label: string;
    icon: React.ReactNode;
}

const ControlButton = ({ label, icon, className, ...props }: ControlButtonProps) => (
    <button
        className={cnUtils(`flex flex-col items-center justify-center gap-3 p-6 bg-slate-900 border border-slate-800 rounded-3xl transition-all active:scale-95 group overflow-hidden relative`, className)}
        {...props}
    >
        <div className="absolute inset-0 bg-white/0 group-hover:bg-white/[0.02] transition-colors" />
        <div className="relative group-hover:scale-110 transition-transform">
            {icon}
        </div>
        <span className="relative text-xs font-bold uppercase tracking-[0.2em]">{label}</span>
    </button>
);
