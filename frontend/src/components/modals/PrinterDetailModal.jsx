import React from 'react';
import { X, Thermometer, Wind, Box, Play, Square, Download, Activity, FileText, Layers } from 'lucide-react';
import LiveTelemetryCard from '../printers/LiveTelemetryCard';

const PrinterDetailModal = ({ printer, isOpen, onClose }) => {
    if (!isOpen || !printer) return null;

    const isPrinting = printer.current_status === 'PRINTING';

    return (
        <div className="fixed inset-0 z-[110] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-slate-950/80 backdrop-blur-md transition-opacity"
                onClick={onClose}
            />

            {/* Modal Container */}
            <div className="relative bg-[#0a0f1a] border border-slate-800 rounded-3xl shadow-[0_0_50px_-12px_rgba(59,130,246,0.3)] w-full max-w-4xl max-h-[90vh] overflow-hidden animate-in zoom-in-95 duration-300">

                {/* Header - Industrial Style */}
                <div className="flex items-center justify-between p-8 border-b border-slate-800 bg-gradient-to-r from-slate-900/50 to-transparent">
                    <div>
                        <div className="flex items-center gap-3 mb-1">
                            <h2 className="text-3xl font-black text-white tracking-tighter uppercase">{printer.name}</h2>
                            <span className={`px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-[0.2em] shadow-lg
                ${isPrinting ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-slate-800 text-slate-400 border border-slate-700'}`}>
                                {printer.current_status}
                            </span>
                        </div>
                        <div className="flex gap-4 text-xs font-mono text-slate-500">
                            <span className="flex items-center gap-1.5"><Activity size={12} /> {printer.ip_address}</span>
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

                <div className="p-8 overflow-y-auto max-h-[calc(90vh-120px)] scrollbar-hide">
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
                                    value={32.4}
                                    unit="°C"
                                    icon={Box}
                                    color="emerald"
                                />
                                <LiveTelemetryCard
                                    label="Fan Speed"
                                    value={85}
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
                                {[0, 1, 2, 3].map((slotIdx) => {
                                    const ams = (printer.ams_data || []).find(a => a.slot === slotIdx);
                                    return (
                                        <div key={slotIdx} className="bg-slate-900 border border-slate-800 p-4 rounded-2xl flex flex-col items-center gap-3">
                                            <div
                                                className="w-8 h-8 rounded-full border-2 border-slate-700 shadow-inner"
                                                style={{ backgroundColor: ams?.color || '#334155' }}
                                            />
                                            <span className="text-[10px] font-bold text-slate-500">S-{slotIdx + 1}</span>
                                        </div>
                                    );
                                })}
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
                        <div className="md:col-span-2 grid grid-cols-3 gap-4">
                            <ControlButton label="Pause" icon={<Play size={20} />} color="hover:bg-amber-500/10 hover:text-amber-500 hover:border-amber-500/50" />
                            <ControlButton label="Stop" icon={<Square size={20} />} color="hover:bg-rose-500/10 hover:text-rose-500 hover:border-rose-500/50" />
                            <ControlButton label="Unload" icon={<Download size={20} />} color="hover:bg-blue-500/10 hover:text-blue-500 hover:border-blue-500/50" />
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
};

const TelemetryCard = ({ label, value, unit, icon, color }) => (
    <div className={`p-4 rounded-2xl border transition-all ${color}`}>
        <div className="flex items-center gap-2 mb-2 font-mono uppercase tracking-widest text-[9px] text-slate-400">
            {icon} {label}
        </div>
        <div className="text-2xl font-black text-white tabular-nums">
            {value}<span className="text-sm text-slate-500 ml-1 font-mono uppercase tracking-normal">{unit}</span>
        </div>
    </div>
);

const ControlButton = ({ label, icon, color }) => (
    <button className={`flex flex-col items-center justify-center gap-3 p-6 bg-slate-900 border border-slate-800 rounded-3xl transition-all active:scale-95 group overflow-hidden relative ${color}`}>
        <div className="absolute inset-0 bg-white/0 group-hover:bg-white/[0.02] transition-colors" />
        <div className="relative group-hover:scale-110 transition-transform">
            {icon}
        </div>
        <span className="relative text-xs font-bold uppercase tracking-[0.2em]">{label}</span>
    </button>
);

export default PrinterDetailModal;
