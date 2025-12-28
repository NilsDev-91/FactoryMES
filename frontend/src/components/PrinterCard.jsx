import React, { memo } from 'react';
import { Settings, Clock } from 'lucide-react';
import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs) {
    return twMerge(clsx(inputs));
}

/**
 * High-Density PrinterCard
 * Design: Dark Mode / Industrial / High Scalability (500+ units)
 * Status Color Logic: 
 * - idle: Purple
 * - printing: Yellow
 * - done: Green
 * - error: Red
 */
const PrinterCard = ({ printer, onSettingsClick }) => {
    // Standardize status
    const status = (printer.current_status || 'idle').toLowerCase();
    const progress = printer.current_progress || 0;
    const timeLeft = printer.remaining_time ? `${printer.remaining_time}m` : null;

    // Strict color mapping per requirements
    const statusConfig = {
        idle: {
            border: 'border-purple-500',
            text: 'text-purple-500',
            bg: 'bg-purple-500/20',
            progress: 'bg-purple-500',
        },
        printing: {
            border: 'border-yellow-500',
            text: 'text-yellow-500',
            bg: 'bg-yellow-500/20',
            progress: 'bg-yellow-500',
        },
        done: {
            border: 'border-green-500',
            text: 'text-green-500',
            bg: 'bg-green-500/20',
            progress: 'bg-green-500',
        },
        error: {
            border: 'border-red-500',
            text: 'text-red-500',
            bg: 'bg-red-500/20',
            progress: 'bg-red-500',
        }
    };

    const config = statusConfig[status] || statusConfig.idle;

    return (
        <div className={cn(
            "group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg transition-all hover:border-slate-700 h-[100px]",
            "flex flex-col"
        )}>
            {/* 4px Colored Strip on Left */}
            <div className={cn("absolute left-0 top-0 bottom-0 w-1 transition-all group-hover:w-1.5", config.progress)} />

            <div className="flex-1 p-4 pl-5 flex flex-col justify-between">
                {/* Header */}
                <div className="flex justify-between items-center">
                    <div className="flex items-center gap-2 overflow-hidden">
                        {/* Colored Dot */}
                        <div className={cn("w-2 h-2 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)]", config.progress)} />
                        <h3 className="font-bold text-white truncate uppercase tracking-tight text-sm" title={printer.name}>
                            {printer.name}
                        </h3>
                    </div>

                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            onSettingsClick?.(printer);
                        }}
                        className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all active:scale-95"
                    >
                        <Settings size={16} />
                    </button>
                </div>

                {/* Footer (Progress & Time) */}
                <div className="space-y-1.5">
                    <div className="flex justify-between items-end text-[10px] font-black uppercase tracking-widest leading-none">
                        <span className={config.text}>{progress}%</span>
                        {status === 'printing' && timeLeft && (
                            <span className="text-slate-500 flex items-center gap-1 font-mono">
                                <Clock size={10} /> {timeLeft} left
                            </span>
                        )}
                        {status !== 'printing' && (
                            <span className={cn("px-1.5 py-0.5 rounded-[4px] text-[8px]", config.bg, config.text)}>
                                {status}
                            </span>
                        )}
                    </div>

                    {/* Highly Visible Progress Bar */}
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden border border-slate-950/50">
                        <div
                            className={cn("h-full transition-all duration-1000 shadow-[0_0_10px_rgba(0,0,0,0.3)]", config.progress)}
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

// Custom Comparison for React.memo
const arePropsEqual = (prevProps, nextProps) => {
    const prev = prevProps.printer;
    const next = nextProps.printer;

    return (
        prev.current_status === next.current_status &&
        prev.current_progress === next.current_progress &&
        prev.remaining_time === next.remaining_time &&
        prev.name === next.name
    );
};

export default memo(PrinterCard, arePropsEqual);
