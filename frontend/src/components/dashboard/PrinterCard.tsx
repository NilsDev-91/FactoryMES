
import React, { useState } from 'react';
import { Settings, Clock, Trash2, AlertTriangle, Loader2, AlertCircle } from 'lucide-react';
import { mutate } from 'swr';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Printer, AmsSlot } from '../../types/printer';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

export interface PrinterCardProps {
    printer: Printer;
    onSettingsClick?: (printer: Printer) => void;
}

/**
 * High-Density PrinterCard
 * Design: Dark Mode / Industrial / High Scalability (500+ units)
 */
export function PrinterCard({ printer, onSettingsClick }: PrinterCardProps) {
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);

    const handleDelete = async (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsDeleting(true);
        try {
            const res = await fetch(`http://localhost:8000/api/printers/${printer.serial}`, {
                method: 'DELETE'
            });
            if (!res.ok) throw new Error('Failed to delete');
            mutate('http://localhost:8000/api/printers');
        } catch (error) {
            alert('Failed to delete printer');
            setIsDeleting(false);
        }
    };
    // Standardize status
    const status = (printer.current_status || 'idle').toLowerCase();
    const progress = printer.current_progress || 0;
    const timeLeft = printer.remaining_time ? `${printer.remaining_time}m` : null;

    // Strict color mapping per requirements
    const statusConfig: Record<string, { border: string; text: string; bg: string; progress: string }> = {
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
        },
        offline: {
            border: 'border-slate-700',
            text: 'text-slate-500',
            bg: 'bg-slate-800',
            progress: 'bg-slate-700',
        }
    };

    const config = statusConfig[status] || statusConfig.idle;

    // Clean Alpha from Hex if present (e.g. FF0000FF -> #FF0000)
    const formatColor = (color: string | undefined) => {
        if (!color) return undefined;
        let hex = color.startsWith('#') ? color : `#${color}`;
        if (hex.length > 7) hex = hex.substring(0, 7);
        return hex;
    };

    // Prepare AMS Slots (Guarantee 4 slots for visualization)
    // Backend might return [], [slot0, slot2], etc.
    // We map purely by visual index 0-3
    const slots = printer.ams_slots || printer.ams_inventory || [];
    const amsDisplay = [0, 1, 2, 3].map(idx => {
        // Find slot with this matching index
        // Prioritize slot matching global index logic if needed, 
        // but simple 0-3 match is safer for single AMS.
        return slots.find(s => s.slot_index === idx) || null;
    });

    return (
        <div className={cn(
            "group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg transition-all hover:border-slate-700 h-[140px]",
            "flex flex-col select-none"
        )}>
            {/* Delete Confirmation Overlay */}
            {showDeleteConfirm && (
                <div className="absolute inset-0 z-50 bg-slate-950/95 flex flex-col items-center justify-center text-center p-4 animate-in fade-in duration-200">
                    <AlertTriangle className="text-red-500 mb-2" size={24} />
                    <p className="text-white font-bold text-sm mb-1">Delete {printer.name}?</p>
                    <p className="text-[10px] text-slate-500 mb-4">This action cannot be undone.</p>
                    <div className="flex gap-2 w-full">
                        <button
                            onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(false); }}
                            className="flex-1 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-bold rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleDelete}
                            disabled={isDeleting}
                            className="flex-1 py-1.5 bg-red-600 hover:bg-red-500 text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center"
                        >
                            {isDeleting ? <Loader2 size={12} className="animate-spin" /> : 'Delete'}
                        </button>
                    </div>
                </div>
            )}

            {/* 4px Colored Strip on Left */}
            <div className={cn("absolute left-0 top-0 bottom-0 w-1 transition-all group-hover:w-1.5", config.progress)} />

            <div className="flex-1 p-3 pl-4 flex flex-col justify-between">
                {/* Header */}
                <div className="flex justify-between items-start">
                    <div className="flex flex-col gap-1 overflow-hidden">
                        <div className="flex items-center gap-2">
                            {/* Colored Dot Status */}
                            <div className={cn("w-2 h-2 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)]", config.progress)} />
                            <h3 className="font-bold text-white truncate uppercase tracking-tight text-sm" title={printer.name}>
                                {printer.name}
                            </h3>
                        </div>
                    </div>

                    <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                setShowDeleteConfirm(true);
                            }}
                            className="p-1.5 text-slate-600 hover:text-red-500 hover:bg-red-500/10 rounded-lg transition-all active:scale-95"
                            title="Delete Printer"
                        >
                            <Trash2 size={14} />
                        </button>
                        <button
                            onClick={(e) => {
                                e.stopPropagation();
                                onSettingsClick?.(printer);
                            }}
                            className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all active:scale-95"
                        >
                            <Settings size={14} />
                        </button>
                    </div>
                </div>

                {/* AMS Slots Visual - Centerpiece */}
                <div className="flex items-center gap-2 my-1">
                    <span className="text-[9px] text-slate-600 font-bold tracking-wider">AMS</span>
                    <div className="flex items-center gap-1.5 bg-slate-950/50 px-2 py-1 rounded-full border border-slate-800">
                        {amsDisplay.map((slot, idx) => {
                            const color = formatColor(slot?.tray_color);
                            const isEmpty = !slot || !color;
                            const isLow = (slot?.remaining_percent || 0) < 10 && !isEmpty;

                            return (
                                <div key={idx} className="relative group/slot">
                                    {/* Spool Circle */}
                                    <div
                                        className={cn(
                                            "w-5 h-5 rounded-full border shadow-sm flex items-center justify-center transition-transform hover:scale-110",
                                            isEmpty
                                                ? "bg-slate-800 border-slate-700 border-dashed"
                                                : "border-slate-600/50"
                                        )}
                                        style={!isEmpty ? {
                                            backgroundColor: color,
                                            boxShadow: `inset 0 2px 4px rgba(255,255,255,0.3), inset 0 -2px 4px rgba(0,0,0,0.4)` // Glossy effect
                                        } : {}}
                                        title={slot ? `${slot.tray_type} | ${slot.tray_color} | ${slot.remaining_percent}%` : "Empty Slot"}
                                    >
                                        {/* LowWarning or Type */}
                                        {isLow && (
                                            <AlertCircle size={10} className="text-white drop-shadow-md stroke-[3]" />
                                        )}
                                        {!isLow && !isEmpty && (
                                            <span className="text-[6px] font-black text-white/90 drop-shadow-md uppercase truncate max-w-[16px]">
                                                {slot?.tray_type?.substring(0, 3)}
                                            </span>
                                        )}
                                        {isEmpty && (
                                            <span className="text-[6px] text-slate-600 font-bold">
                                                {idx + 1}
                                            </span>
                                        )}
                                    </div>

                                    {/* Tooltip for % */}
                                    {!isEmpty && (
                                        <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 bg-black/90 text-white text-[9px] px-1.5 py-0.5 rounded opacity-0 group-hover/slot:opacity-100 whitespace-nowrap z-10 pointer-events-none">
                                            {slot?.remaining_percent}%
                                        </div>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                </div>

                {/* Footer (Progress & Time) */}
                <div className="space-y-1">
                    <div className="flex justify-between items-end text-[10px] font-black uppercase tracking-widest leading-none mb-1">
                        <span className={config.text}>{progress}%</span>
                        {status === 'printing' && timeLeft && (
                            <span className="text-slate-500 flex items-center gap-1 font-mono">
                                <Clock size={10} /> {timeLeft}
                            </span>
                        )}
                        {status !== 'printing' && (
                            <span className={cn("px-1.5 py-0.5 rounded-[4px] text-[8px]", config.bg, config.text)}>
                                {status.toUpperCase()}
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
;
