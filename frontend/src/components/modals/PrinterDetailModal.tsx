
import React, { useState, useEffect, useCallback } from 'react';
import { X, Thermometer, Wind, Box, Play, Square, Download, Activity, FileText, Layers, Trash2, Settings, Zap, AlertTriangle } from 'lucide-react';
import { mutate } from 'swr';
import { Printer } from '@/types/printer';
import { LiveTelemetryCard } from '@/components/printers/LiveTelemetryCard';
import { ConfirmationModal } from './ConfirmationModal';
import { updateAutomationConfig, forceClearPrinter, ClearingStrategy } from '@/lib/api/printers';

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

type TabType = 'overview' | 'automation';

export function PrinterDetailModal({ printer, isOpen, onClose }: PrinterDetailModalProps) {
    const [activeTab, setActiveTab] = useState<TabType>('overview');
    const [showForceClearConfirm, setShowForceClearConfirm] = useState(false);

    // Automation config local state
    const [canAutoEject, setCanAutoEject] = useState(false);
    const [thermalReleaseTemp, setThermalReleaseTemp] = useState(29.0);
    const [clearingStrategy, setClearingStrategy] = useState<ClearingStrategy>('MANUAL');
    const [isSaving, setIsSaving] = useState(false);

    // Sync local state with printer prop
    useEffect(() => {
        if (printer) {
            setCanAutoEject(printer.can_auto_eject ?? false);
            setThermalReleaseTemp(printer.thermal_release_temp ?? 29.0);
            setClearingStrategy((printer.clearing_strategy as ClearingStrategy) ?? 'MANUAL');
        }
    }, [printer]);

    // Debounced save for automation config
    const saveConfig = useCallback(async (config: Partial<{
        can_auto_eject: boolean;
        thermal_release_temp: number;
        clearing_strategy: ClearingStrategy;
    }>) => {
        if (!printer) return;
        setIsSaving(true);
        try {
            await updateAutomationConfig(printer.serial, config);
            mutate('http://127.0.0.1:8000/api/printers');
        } catch (e) {
            console.error('Failed to save automation config:', e);
        } finally {
            setIsSaving(false);
        }
    }, [printer]);

    if (!isOpen || !printer) return null;

    const isPrinting = printer.current_status === 'PRINTING';
    const canForceClear = ['IDLE', 'COOLDOWN', 'AWAITING_CLEARANCE'].includes(printer.current_status);

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

    const handleForceClear = async () => {
        setShowForceClearConfirm(false);
        try {
            await forceClearPrinter(printer.serial);
            mutate('http://127.0.0.1:8000/api/printers');
        } catch (e) {
            alert(`Failed to trigger clearing: ${e instanceof Error ? e.message : 'Unknown error'}`);
        }
    };

    // Helper for AMS Slot Visuals
    const formatColor = (color: string | undefined) => {
        if (!color) return '#334155';
        let hex = color.replace('#', '');
        if (hex.length === 8) hex = hex.substring(0, 6);
        return `#${hex}`;
    };

    const getAmsSlot = (slotIdx: number) => {
        return printer.ams_slots?.find(s => s.slot_index === slotIdx) || null;
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

                {/* Tab Navigation */}
                <div className="flex border-b border-slate-800 bg-slate-900/30">
                    <TabButton
                        active={activeTab === 'overview'}
                        onClick={() => setActiveTab('overview')}
                        icon={<Activity size={16} />}
                    >
                        Overview
                    </TabButton>
                    <TabButton
                        active={activeTab === 'automation'}
                        onClick={() => setActiveTab('automation')}
                        icon={<Settings size={16} />}
                    >
                        Automation
                    </TabButton>
                </div>

                <div className="p-8 overflow-y-auto max-h-[calc(90vh-200px)]">
                    {activeTab === 'overview' && (
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
                                    {[0, 1, 2, 3].map((slotIdx) => {
                                        const slot = getAmsSlot(slotIdx);
                                        return (
                                            <div key={slotIdx} className="bg-slate-900 border border-slate-800 p-4 rounded-2xl flex flex-col items-center gap-3">
                                                <div
                                                    className="w-10 h-10 rounded-full border-2 border-slate-700 shadow-inner"
                                                    style={{ backgroundColor: formatColor(slot?.color_hex) }}
                                                    title={slot?.material || 'Empty'}
                                                />
                                                <div className="flex flex-col items-center">
                                                    <span className="text-[10px] font-bold text-slate-500 uppercase tracking-tighter">S-{slotIdx + 1}</span>
                                                    <span className="text-[9px] font-black text-slate-400 mt-0.5">{slot?.material || '---'}</span>
                                                </div>
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
                    )}

                    {activeTab === 'automation' && (
                        <div className="space-y-8">

                            {/* Configuration Card */}
                            <div className="bg-slate-900/50 border border-slate-800 p-6 rounded-3xl space-y-6">
                                <div className="flex items-center justify-between">
                                    <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.3em] flex items-center gap-2">
                                        <Zap size={14} className="text-amber-500" /> Infinite Loop Configuration
                                    </h3>
                                    {isSaving && (
                                        <span className="text-[10px] text-slate-500 font-mono animate-pulse">Saving...</span>
                                    )}
                                </div>

                                {/* Enable Infinite Loop Switch */}
                                <div className="flex items-center justify-between p-4 bg-slate-950/50 rounded-2xl border border-slate-800">
                                    <div>
                                        <p className="text-sm font-bold text-white">Enable Infinite Loop</p>
                                        <p className="text-xs text-slate-500 mt-1">Automatically eject prints and start next job</p>
                                    </div>
                                    <Switch
                                        checked={canAutoEject}
                                        onChange={(checked) => {
                                            setCanAutoEject(checked);
                                            saveConfig({ can_auto_eject: checked });
                                        }}
                                    />
                                </div>

                                {/* Thermal Release Temp Input */}
                                <div className="p-4 bg-slate-950/50 rounded-2xl border border-slate-800 space-y-3">
                                    <div>
                                        <p className="text-sm font-bold text-white">Thermal Release Temperature</p>
                                        <p className="text-xs text-slate-500 mt-1">Bed must cool below this temp before ejecting (°C)</p>
                                    </div>
                                    <div className="flex items-center gap-4">
                                        <input
                                            type="number"
                                            step="0.5"
                                            min="20"
                                            max="60"
                                            value={thermalReleaseTemp}
                                            onChange={(e) => setThermalReleaseTemp(parseFloat(e.target.value))}
                                            onBlur={() => saveConfig({ thermal_release_temp: thermalReleaseTemp })}
                                            className="w-24 px-4 py-2 bg-slate-900 border border-slate-700 rounded-xl text-white font-mono text-center focus:outline-none focus:border-blue-500 transition-colors"
                                        />
                                        <span className="text-sm text-slate-400 font-mono">°C</span>
                                        <div className="flex-1 h-2 bg-slate-900 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-blue-500 via-amber-500 to-red-500"
                                                style={{ width: `${((thermalReleaseTemp - 20) / 40) * 100}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Clearing Strategy Select */}
                                <div className="p-4 bg-slate-950/50 rounded-2xl border border-slate-800 space-y-3">
                                    <div>
                                        <p className="text-sm font-bold text-white">Clearing Strategy</p>
                                        <p className="text-xs text-slate-500 mt-1">Method used to eject prints from the bed</p>
                                    </div>
                                    <select
                                        value={clearingStrategy}
                                        onChange={(e) => {
                                            const value = e.target.value as ClearingStrategy;
                                            setClearingStrategy(value);
                                            saveConfig({ clearing_strategy: value });
                                        }}
                                        className="w-full px-4 py-3 bg-slate-900 border border-slate-700 rounded-xl text-white font-medium focus:outline-none focus:border-blue-500 transition-colors appearance-none cursor-pointer"
                                    >
                                        <option value="MANUAL">Manual (Operator Intervention)</option>
                                        <option value="A1_INERTIAL_FLING">A1 Inertial Fling (Shake-Off)</option>
                                        <option value="X1_MECHANICAL_SWEEP">X1 Mechanical Sweep (Bulldozer)</option>
                                    </select>
                                </div>
                            </div>

                            {/* Danger Zone Card */}
                            <div className="bg-red-950/20 border border-red-900/50 p-6 rounded-3xl space-y-4">
                                <h3 className="text-[10px] font-bold text-red-400 uppercase tracking-[0.3em] flex items-center gap-2">
                                    <AlertTriangle size={14} /> Danger Zone — Manual Override
                                </h3>
                                <p className="text-sm text-slate-400">
                                    Use this if the system is stuck in COOLDOWN or AWAITING_CLEARANCE, or if you manually removed a print but the status didn&apos;t update.
                                </p>
                                <button
                                    onClick={() => setShowForceClearConfirm(true)}
                                    disabled={!canForceClear}
                                    className={cnUtils(
                                        "w-full py-4 rounded-2xl font-bold uppercase tracking-widest text-sm transition-all flex items-center justify-center gap-3",
                                        canForceClear
                                            ? "bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/30 active:scale-[0.98]"
                                            : "bg-slate-800 text-slate-500 cursor-not-allowed"
                                    )}
                                >
                                    <Zap size={18} />
                                    Force Bed Clearing
                                </button>
                                {!canForceClear && (
                                    <p className="text-xs text-slate-500 text-center">
                                        Only available when printer is IDLE, COOLDOWN, or AWAITING_CLEARANCE
                                    </p>
                                )}
                            </div>

                        </div>
                    )}
                </div>
            </div>

            {/* Force Clear Confirmation Modal */}
            <ConfirmationModal
                isOpen={showForceClearConfirm}
                title="Force Bed Clearing"
                message="Warning: This will execute a mechanical sweep sequence. Ensure the print bed path is clear of obstructions before proceeding."
                confirmLabel="Execute Sweep"
                cancelLabel="Cancel"
                isDestructive={true}
                onConfirm={handleForceClear}
                onCancel={() => setShowForceClearConfirm(false)}
            />
        </div>
    );
};

// Tab Button Component
interface TabButtonProps {
    active: boolean;
    onClick: () => void;
    icon: React.ReactNode;
    children: React.ReactNode;
}

const TabButton = ({ active, onClick, icon, children }: TabButtonProps) => (
    <button
        onClick={onClick}
        className={cnUtils(
            "flex items-center gap-2 px-6 py-4 text-sm font-bold uppercase tracking-widest transition-all border-b-2",
            active
                ? "text-white border-blue-500 bg-blue-500/5"
                : "text-slate-500 border-transparent hover:text-slate-300 hover:bg-slate-800/50"
        )}
    >
        {icon}
        {children}
    </button>
);

// Switch Component (Custom, matches Shadcn/UI aesthetic)
interface SwitchProps {
    checked: boolean;
    onChange: (checked: boolean) => void;
}

const Switch = ({ checked, onChange }: SwitchProps) => (
    <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={cnUtils(
            "relative inline-flex h-7 w-12 shrink-0 cursor-pointer rounded-full border-2 transition-colors duration-200 ease-in-out focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
            checked ? "bg-emerald-500 border-emerald-500" : "bg-slate-700 border-slate-600"
        )}
    >
        <span
            className={cnUtils(
                "pointer-events-none inline-block h-6 w-6 transform rounded-full bg-white shadow-lg ring-0 transition duration-200 ease-in-out",
                checked ? "translate-x-5" : "translate-x-0"
            )}
        />
    </button>
);

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
