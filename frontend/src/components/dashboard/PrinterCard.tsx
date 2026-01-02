
import React, { useState } from 'react';
import { Settings, Clock, Trash2, AlertTriangle, Loader2, Snowflake, ArrowRightLeft, CheckCircle2 } from 'lucide-react';
import { mutate } from 'swr';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Printer } from '../../types/printer';
import { PrinterControls } from '../printers/printer-controls';

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
    const [isClearing, setIsClearing] = useState(false);

    const handleDelete = async (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsDeleting(true);
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/printers/${printer.serial}`, {
                method: 'DELETE'
            });
            if (!res.ok) throw new Error('Failed to delete');
            mutate('http://127.0.0.1:8000/api/printers');
        } catch (error) {
            alert('Failed to delete printer');
            setIsDeleting(false);
        }
    };

    const handleClearance = async (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsClearing(true);
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/printers/${printer.serial}/confirm-clearance`, {
                method: 'POST'
            });
            if (!res.ok) throw new Error('Failed to confirm clearance');
            mutate('http://127.0.0.1:8000/api/printers');
        } catch (error) {
            alert('Failed to confirm clearance');
        } finally {
            setIsClearing(false);
        }
    };

    // Phase 7: Clear error handler
    const handleClearError = async (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsClearing(true);
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/printers/${printer.serial}/clear-error`, {
                method: 'POST'
            });
            if (!res.ok) throw new Error('Failed to clear error');
            mutate('http://127.0.0.1:8000/api/printers');
        } catch (error) {
            alert('Failed to clear error');
        } finally {
            setIsClearing(false);
        }
    };

    // Standardize status
    const status = (printer.current_status || 'idle').toLowerCase();
    const isPrinting = status === 'printing';
    const isAwaitingClearance = status === 'awaiting_clearance';
    const isCooldown = status === 'cooldown';
    const isClearingBed = status === 'clearing_bed';
    // Phase 7: HMS Watchdog States
    const isError = status === 'error';
    const isPaused = status === 'paused';

    // Progress logic: Printing uses actual, Automation states show indeterminate
    const progress = isAwaitingClearance ? 100 : (printer.current_progress || 0);
    const showProgressBar = isPrinting || isAwaitingClearance || isCooldown || isClearingBed;

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
        },
        awaiting_clearance: {
            border: 'border-red-500',
            text: 'text-red-400',
            bg: 'bg-red-500/10',
            progress: 'bg-red-500',
        },
        // Phase 6: New Automation States
        cooldown: {
            border: 'border-blue-500',
            text: 'text-blue-400',
            bg: 'bg-blue-500/20',
            progress: 'bg-blue-500',
        },
        clearing_bed: {
            border: 'border-amber-500',
            text: 'text-amber-400',
            bg: 'bg-amber-500/20',
            progress: 'bg-amber-500',
        },
        // Phase 7: HMS Watchdog Error States
        error: {
            border: 'border-red-600',
            text: 'text-red-500',
            bg: 'bg-red-500/20',
            progress: 'bg-red-600',
        },
        paused: {
            border: 'border-orange-500',
            text: 'text-orange-400',
            bg: 'bg-orange-500/20',
            progress: 'bg-orange-500',
        }
    };

    const config = statusConfig[status] || statusConfig.idle;

    // Clean Alpha from Hex if present (e.g. FF0000FF -> #FF0000)
    const formatColor = (color: string | undefined) => {
        if (!color) return '#334155'; // Fallback
        let hex = color.replace('#', '');
        if (hex.length === 8) hex = hex.substring(0, 6);
        return `#${hex}`;
    };

    // Prepare AMS Slots (Guarantee 4 slots for visualization)
    const slots = printer.ams_slots || [];
    const amsDisplay = [0, 1, 2, 3].map(idx => {
        return slots.find(s => s.slot_index === idx) || { color_hex: undefined, material: 'Empty' };
    });

    return (
        <div className={cn(
            "group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg transition-all hover:border-slate-700 h-[150px]",
            "flex flex-col select-none",
            isAwaitingClearance && "border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.15)] ring-1 ring-emerald-500/20"
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

                    {/* Action Buttons - Always Visible (no opacity classes) */}
                    <div className="flex gap-1">
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

                {/* AMS Slots Visual - Simple Circular Divs */}
                <div className="flex items-center gap-2 my-1">
                    <span className="text-[9px] text-slate-600 font-bold tracking-wider">AMS</span>
                    <div className="flex items-center gap-1.5 bg-slate-950/50 px-2 py-1 rounded-full border border-slate-800">
                        {amsDisplay.map((slot, idx) => (
                            <div
                                key={idx}
                                className="h-4 w-4 rounded-full border border-slate-600/50 shadow-sm"
                                style={{ backgroundColor: formatColor(slot.color_hex) }}
                                title={`${slot.material || 'Unknown'} (${slot.color_hex || 'No Color'})`}
                            />
                        ))}
                    </div>

                    {/* Controls Integration */}
                    <div className="ml-auto">
                        <PrinterControls printer={printer} />
                    </div>
                </div>

                {/* Footer: Progress Bar, Status Text, and Clearance Action */}
                <div className="space-y-1">
                    <div className="flex justify-between items-end text-[10px] font-black uppercase tracking-widest leading-none mb-1">
                        {/* Status Text & CLEAR PLATE Action */}
                        <div className={cn("flex items-center gap-2", config.text)}>
                            {isPrinting && `${progress}%`}

                            {/* Phase 6: Automation States */}
                            {isCooldown && (
                                <div className="flex items-center gap-1.5 text-blue-400">
                                    <Snowflake size={12} className="animate-pulse" />
                                    <span>COOLING (Thermal Release)...</span>
                                </div>
                            )}
                            {isClearingBed && (
                                <div className="flex items-center gap-1.5 text-amber-400 animate-pulse">
                                    <ArrowRightLeft size={12} />
                                    <span>AUTO-EJECTING...</span>
                                </div>
                            )}

                            {/* Manual Clearance Required */}
                            {isAwaitingClearance && (
                                <div className="flex items-center gap-1.5 text-red-400">
                                    <AlertTriangle size={12} />
                                    <span>
                                        {printer.last_job?.job_metadata?.is_auto_eject_enabled === false
                                            ? "MANUAL CLEAR: HEIGHT SAFETY (<38mm)"
                                            : "MANUAL CLEARANCE REQUIRED"}
                                    </span>
                                </div>
                            )}

                            {/* Phase 7: HMS Watchdog Error States */}
                            {isError && (
                                <div className="flex items-center gap-1.5 text-red-500 animate-pulse">
                                    <AlertTriangle size={12} />
                                    <span className="truncate max-w-[180px]" title={printer.last_error_description}>
                                        ⚠️ {printer.last_error_description || 'Hardware Error'}
                                    </span>
                                </div>
                            )}
                            {isPaused && (
                                <div className="flex items-center gap-1.5 text-orange-400">
                                    <AlertTriangle size={12} />
                                    <span className="truncate max-w-[180px]" title={printer.last_error_description}>
                                        {printer.last_error_description || 'Paused - Intervention Required'}
                                    </span>
                                </div>
                            )}

                            {/* Default status display */}
                            {!isPrinting && !isAwaitingClearance && !isCooldown && !isClearingBed && !isError && !isPaused && status.toUpperCase().replace('_', ' ')}
                        </div>

                        {/* Time Remaining */}
                        {isPrinting && timeLeft && (
                            <span className="text-slate-500 flex items-center gap-1 font-mono">
                                <Clock size={10} /> {timeLeft}
                            </span>
                        )}
                    </div>

                    {/* Progress Bar - Visible if Printing OR Awaiting Clearance */}
                    {showProgressBar && (
                        <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden border border-slate-950/50">
                            <div
                                className={cn("h-full transition-all duration-1000 shadow-[0_0_10px_rgba(0,0,0,0.3)]", config.progress, isClearingBed && "animate-pulse")}
                                style={{ width: isCooldown || isClearingBed ? '100%' : `${progress}%` }}
                            />
                        </div>
                    )}

                    {/* Phase 6: Manual Intervention Button for AWAITING_CLEARANCE */}
                    {isAwaitingClearance && (
                        <button
                            onClick={handleClearance}
                            disabled={isClearing}
                            className="w-full mt-1 py-1.5 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-500 hover:to-emerald-500 text-white text-[10px] font-black uppercase tracking-widest rounded-lg transition-all active:scale-[0.98] flex items-center justify-center gap-2 shadow-lg shadow-green-900/30"
                        >
                            {isClearing ? (
                                <>
                                    <Loader2 size={12} className="animate-spin" />
                                    <span>Confirming...</span>
                                </>
                            ) : (
                                <>
                                    <CheckCircle2 size={12} />
                                    <span>Confirm Bed Empty</span>
                                </>
                            )}
                        </button>
                    )}

                    {/* Phase 7: Error/Paused Clear Button */}
                    {(isError || isPaused) && (
                        <button
                            onClick={handleClearError}
                            disabled={isClearing}
                            className="w-full mt-1 py-1.5 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-500 hover:to-orange-500 text-white text-[10px] font-black uppercase tracking-widest rounded-lg transition-all active:scale-[0.98] flex items-center justify-center gap-2 shadow-lg shadow-red-900/30 animate-pulse"
                        >
                            {isClearing ? (
                                <>
                                    <Loader2 size={12} className="animate-spin" />
                                    <span>Clearing...</span>
                                </>
                            ) : (
                                <>
                                    <AlertTriangle size={12} />
                                    <span>Clear Error & Reset</span>
                                </>
                            )}
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
};
