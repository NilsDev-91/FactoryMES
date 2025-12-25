import React, { memo } from 'react';
import { Thermometer, Wind, Waves, Package, AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
    return twMerge(clsx(inputs));
}

const PrinterCard = ({ printer }) => {
    // Use raw snake_case fields from backend
    const status = (printer.current_status || 'offline').toLowerCase();
    const isOffline = status === 'offline';

    // Determine styles based on status
    const getStatusStyles = () => {
        switch (status) {
            case 'printing':
                return {
                    border: 'border-l-green-500',
                    badge: 'bg-green-500/10 text-green-400',
                    progress: 'bg-green-500'
                };
            case 'idle':
            case 'waiting':
                return {
                    border: 'border-l-purple-500',
                    badge: 'bg-purple-500/10 text-purple-400',
                    progress: 'bg-slate-600'
                };
            case 'ready':
                return {
                    border: 'border-l-blue-500',
                    badge: 'bg-blue-500/10 text-blue-400',
                    progress: 'bg-slate-600'
                };
            case 'warning':
                return {
                    border: 'border-l-yellow-500',
                    badge: 'bg-yellow-500/10 text-yellow-400',
                    progress: 'bg-yellow-500'
                };
            case 'offline':
            default:
                return {
                    border: 'border-l-slate-600',
                    badge: 'bg-slate-700 text-slate-400',
                    progress: 'bg-slate-700'
                };
        }
    };

    const styles = getStatusStyles();

    return (
        <div
            className={cn(
                "bg-slate-800 rounded-lg p-4 border border-slate-700/50 shadow-sm hover:shadow-md transition-shadow",
                "border-l-4",
                styles.border,
                // Opacity for offline printers to visually de-emphasize them
                isOffline && "opacity-60 grayscale-[0.5] hover:opacity-100 hover:grayscale-0 transition-all duration-300"
            )}
        >

            {/* Header */}
            <div className="flex justify-between items-start mb-3">
                <div>
                    <h3 className="font-bold text-slate-100 text-lg truncate max-w-[150px]" title={printer.name}>
                        {printer.name}
                    </h3>
                    <span className="text-xs text-slate-500 font-mono">{printer.model || 'Bambu Lab P1S'}</span>
                </div>
                <span className={cn(
                    "px-2 py-0.5 rounded-full text-xs font-medium uppercase tracking-wide border border-transparent",
                    styles.badge
                )}>
                    {status}
                </span>
            </div>

            {/* Thumbnail Area */}
            <div className="aspect-video bg-slate-900/50 rounded-md mb-4 flex items-center justify-center border border-slate-700/50 relative overflow-hidden group">
                {status === 'printing' ? (
                    // Show mock print progress or image
                    <div className="flex flex-col items-center justify-center text-slate-500">
                        <Package className="animate-pulse text-green-500/50 mb-2" size={32} />
                        <span className="text-xs">Printing Layer {printer.layer || 45}/{printer.totalLayers || 240}</span>
                    </div>
                ) : (
                    <div className="text-slate-600">
                        <PrinterIcon status={status} />
                    </div>
                )}
            </div>

            {/* Progress Section */}
            <div className="mb-4">
                <div className="flex justify-between text-xs text-slate-400 mb-1.5">
                    <span className="flex items-center gap-1"><Clock size={12} /> {printer.time_left || '--:--'}</span>
                    <span className="font-medium text-slate-200">{printer.progress || 0}%</span>
                </div>
                <div className="h-2 w-full bg-slate-700/50 rounded-full overflow-hidden">
                    <div
                        className={cn("h-full rounded-full transition-all duration-1000", styles.progress)}
                        style={{ width: `${printer.progress || 0}%` }}
                    />
                </div>
            </div>

            {/* Telemetry Grid */}
            <div className="grid grid-cols-3 gap-2 mb-4 bg-slate-900/30 p-2 rounded border border-slate-700/30">
                <TelemetryItem icon={Thermometer} label="Nozzle" value={`${printer.current_temp_nozzle?.toFixed(0) || 0}°C`} />
                <TelemetryItem icon={Waves} label="Bed" value={`${printer.current_temp_bed?.toFixed(0) || 0}°C`} />
                <TelemetryItem icon={Wind} label="Fan" value={`${printer.fan_speed || 0}%`} />
            </div>

            {/* AMS Slots (Mock for now as backend doesn't send ams) */}
            <div className="flex gap-2 justify-center">
                {(printer.ams_colors || ['#ef4444', '#3b82f6', '#eab308', '#22c55e']).map((color, i) => (
                    <div
                        key={i}
                        className="w-4 h-4 rounded-full border border-slate-600 shadow-sm"
                        style={{ backgroundColor: color || '#334155' }}
                        title={`Slot ${i + 1}`}
                    />
                ))}
            </div>
        </div>
    );
};

// Helper Components
const TelemetryItem = ({ icon: Icon, label, value }) => (
    <div className="flex flex-col items-center justify-center text-center">
        <Icon size={14} className="text-slate-500 mb-1" />
        <span className="text-xs font-bold text-slate-200">{value}</span>
        <span className="text-[10px] text-slate-600 uppercase">{label}</span>
    </div>
);

const PrinterIcon = ({ status }) => {
    if (status === 'offline') return <AlertTriangle size={32} />;
    if (status === 'ready') return <CheckCircle size={32} />;
    return <Package size={32} />;
};

// Custom Comparison for React.memo
const arePropsEqual = (prevProps, nextProps) => {
    const prev = prevProps.printer;
    const next = nextProps.printer;

    // Render only if these specific visual fields change (Strict check per request)
    return (
        prev.current_status === next.current_status &&
        // Round to integer to avoid re-render on micro-fluctuations (e.g. 210.1 -> 210.2)
        Math.round(prev.current_temp_nozzle) === Math.round(next.current_temp_nozzle) &&
        Math.round(prev.current_temp_bed) === Math.round(next.current_temp_bed) &&
        prev.progress === next.progress &&
        prev.time_left === next.time_left
    );
};

export default memo(PrinterCard, arePropsEqual);
