'use client';

import React from 'react';
import { Clock, AlertTriangle, Snowflake, ArrowRightLeft, Loader2 } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Printer } from '../../types/printer';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export interface CompactPrinterCardProps {
    printer: Printer;
    onClick?: (printer: Printer) => void;
}

/**
 * CompactPrinterCard - High-Density Mini-Card for Factory Command Center
 * Design: ~40px height, minimal DOM, optimized for 200-500 printers
 */
export function CompactPrinterCard({ printer, onClick }: CompactPrinterCardProps) {
    const status = (printer.current_status || 'idle').toLowerCase();
    const progress = printer.current_progress || 0;

    // Status color mapping (matching PrinterCard)
    const statusColors: Record<string, { bar: string; dot: string; text: string }> = {
        idle: { bar: 'bg-purple-500', dot: 'bg-purple-500', text: 'text-purple-400' },
        printing: { bar: 'bg-yellow-500', dot: 'bg-yellow-500', text: 'text-yellow-400' },
        done: { bar: 'bg-green-500', dot: 'bg-green-500', text: 'text-green-400' },
        offline: { bar: 'bg-slate-600', dot: 'bg-slate-600', text: 'text-slate-500' },
        awaiting_clearance: { bar: 'bg-red-500', dot: 'bg-red-500', text: 'text-red-400' },
        cooldown: { bar: 'bg-blue-500', dot: 'bg-blue-500', text: 'text-blue-400' },
        clearing_bed: { bar: 'bg-amber-500', dot: 'bg-amber-500', text: 'text-amber-400' },
        error: { bar: 'bg-red-600', dot: 'bg-red-600', text: 'text-red-500' },
        paused: { bar: 'bg-orange-500', dot: 'bg-orange-500', text: 'text-orange-400' },
    };

    const colors = statusColors[status] || statusColors.idle;

    // Format remaining time
    const formatTime = (minutes: number | undefined): string => {
        if (!minutes || minutes <= 0) return '--';
        if (minutes >= 60) {
            const h = Math.floor(minutes / 60);
            const m = minutes % 60;
            return `${h}:${m.toString().padStart(2, '0')}`;
        }
        return `${minutes}m`;
    };

    const isPrinting = status === 'printing';
    const isCooldown = status === 'cooldown';
    const isClearingBed = status === 'clearing_bed';
    const isError = status === 'error';
    const isAwaitingClearance = status === 'awaiting_clearance';

    // Status icon for special states
    const StatusIcon = () => {
        if (isError) return <AlertTriangle size={12} className="text-red-500 animate-pulse flex-shrink-0" />;
        if (isCooldown) return <Snowflake size={12} className="text-blue-400 animate-pulse flex-shrink-0" />;
        if (isClearingBed) return <ArrowRightLeft size={12} className="text-amber-400 flex-shrink-0" />;
        if (isAwaitingClearance) return <AlertTriangle size={12} className="text-red-400 flex-shrink-0" />;
        return null;
    };

    return (
        <div
            onClick={() => onClick?.(printer)}
            className={cn(
                "group relative flex items-center gap-3 bg-slate-900/80 border border-slate-800/60 rounded-lg px-3 py-2 cursor-pointer transition-all",
                "hover:bg-slate-800/80 hover:border-slate-700 active:scale-[0.995]",
                "min-w-0 h-10",
                isError && "border-red-600/40 animate-pulse",
                isAwaitingClearance && "border-red-500/30"
            )}
        >
            {/* Status Bar (Left) */}
            <div className={cn("absolute left-0 top-0 bottom-0 w-1 rounded-l-lg", colors.bar)} />

            {/* Status Dot */}
            <div className={cn("w-2 h-2 rounded-full flex-shrink-0 shadow-sm", colors.dot)} />

            {/* Name */}
            <span className="text-white text-xs font-semibold truncate w-[120px] flex-shrink-0">
                {printer.name}
            </span>

            {/* Status Icon (if applicable) */}
            <StatusIcon />

            {/* Progress Bar (Thin) */}
            <div className="flex-1 h-1.5 bg-slate-800 rounded-full overflow-hidden min-w-[60px]">
                <div
                    className={cn(
                        "h-full transition-all duration-500",
                        colors.bar,
                        isClearingBed && "animate-pulse"
                    )}
                    style={{
                        width: isCooldown || isClearingBed || isAwaitingClearance ? '100%' : `${progress}%`
                    }}
                />
            </div>

            {/* Progress % (only when printing) */}
            {isPrinting && progress > 0 && (
                <span className="text-[10px] font-mono text-slate-400 w-8 text-right flex-shrink-0">
                    {progress}%
                </span>
            )}

            {/* Time Remaining */}
            <div className="flex items-center gap-1 text-slate-500 flex-shrink-0 w-12 justify-end">
                <Clock size={10} />
                <span className="text-[10px] font-mono">{formatTime(printer.remaining_time)}</span>
            </div>
        </div>
    );
}
