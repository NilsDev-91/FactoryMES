import React, { useState } from 'react';
import { Settings, Clock, Trash2, AlertTriangle, Loader2, Snowflake, ArrowRightLeft, CheckCircle2, MoreVertical, Camera } from 'lucide-react';
import { PrinterCameraDialog } from '../printer/PrinterCameraDialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"
import { useQueryClient } from '@tanstack/react-query';
import { usePrinterAction } from '@/hooks/use-printer-action';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Printer } from '../../types/printer';

/**
 * Utility function to merge tailwind classes
 */
function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// ─────────────────────────────────────────────────────────────────────────────
// TYPES & HELPERS
// ─────────────────────────────────────────────────────────────────────────────

type PrinterStatus =
    | 'idle' | 'printing' | 'done' | 'offline'
    | 'awaiting_clearance' | 'cooldown' | 'clearing_bed'
    | 'error' | 'paused';

/**
 * Normalizes hex colors and handles transparency
 */
const formatColor = (color: string | undefined) => {
    if (!color) return undefined;
    let hex = color.replace('#', '');
    if (hex.length === 8) hex = hex.substring(0, 6);
    return `#${hex}`;
};

export interface PrinterCardProps {
    printer: Printer;
    onSettingsClick?: (printer: Printer) => void;
}

/**
 * Professional PrinterCard - Integrated Dashboard Aesthetic
 * 
 * Hierarchy:
 * 1. [Header] Identity & Connectivity
 * 2. [Body] Filament Tray (Subtle Dashboard Widgets)
 * 3. [Footer] Progress Terminal / Action Interface
 */
export function PrinterCard({ printer, onSettingsClick }: PrinterCardProps) {
    const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [showDropdown, setShowDropdown] = useState(false);
    const [isCameraOpen, setIsCameraOpen] = useState(false);

    const queryClient = useQueryClient();
    const { mutate: runAction, isPending: isActionPending } = usePrinterAction(printer.serial);

    const status = (printer.status || 'idle').toLowerCase() as PrinterStatus;
    const isPrinting = status === 'printing';
    const isAwaitingClearance = status === 'awaiting_clearance';
    const isCooldown = status === 'cooldown';
    const isClearingBed = status === 'clearing_bed';
    const isError = status === 'error';
    const isPaused = status === 'paused';

    const isActionRequired = isAwaitingClearance || isError || isPaused;
    const progress = isAwaitingClearance ? 100 : (printer.progress || 0);

    const formatTime = (minutes: number | undefined): string | null => {
        if (!minutes || minutes <= 0) return null;
        if (minutes >= 60) {
            const h = Math.floor(minutes / 60);
            const m = minutes % 60;
            return `${h}h${m > 0 ? ` ${m}m` : ''}`;
        }
        return `${minutes}m`;
    };
    const timeLeft = formatTime(printer.remaining_time_min);

    const statusConfig: Record<PrinterStatus, { border: string; text: string; bg: string; progress: string }> = {
        idle: { border: 'border-purple-500', text: 'text-purple-500', bg: 'bg-purple-500/20', progress: 'bg-purple-500' },
        printing: { border: 'border-yellow-500', text: 'text-yellow-500', bg: 'bg-yellow-500/20', progress: 'bg-yellow-500' },
        done: { border: 'border-green-500', text: 'text-green-500', bg: 'bg-green-500/20', progress: 'bg-green-500' },
        offline: { border: 'border-slate-700', text: 'text-slate-500', bg: 'bg-slate-800', progress: 'bg-slate-700' },
        awaiting_clearance: { border: 'border-emerald-500', text: 'text-emerald-400', bg: 'bg-emerald-500/10', progress: 'bg-emerald-500' },
        cooldown: { border: 'border-blue-500', text: 'text-blue-400', bg: 'bg-blue-500/20', progress: 'bg-blue-500' },
        clearing_bed: { border: 'border-amber-500', text: 'text-amber-400', bg: 'bg-amber-500/20', progress: 'bg-amber-500' },
        error: { border: 'border-red-600', text: 'text-red-500', bg: 'bg-red-500/20', progress: 'bg-red-600' },
        paused: { border: 'border-orange-500', text: 'text-orange-400', bg: 'bg-orange-500/20', progress: 'bg-orange-500' }
    };

    const config = statusConfig[status] || statusConfig.idle;

    const handleDelete = async (e: React.MouseEvent) => {
        e.stopPropagation();
        setIsDeleting(true);
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/printers/${printer.serial}`, { method: 'DELETE' });
            if (!res.ok) throw new Error('Failed to delete');
            queryClient.invalidateQueries({ queryKey: ['printers'] });
        } catch (error) {
            alert('Failed to delete printer');
            setIsDeleting(false);
        }
    };

    const handleClearance = (e: React.MouseEvent) => {
        e.stopPropagation();
        runAction('CONFIRM_CLEARANCE');
    };

    const handleClearError = (e: React.MouseEvent) => {
        e.stopPropagation();
        runAction('CLEAR_ERROR');
    };

    const slots = printer.ams_slots || [];
    const amsDisplay = [0, 1, 2, 3].map(idx => {
        return slots.find(s => s.slot_index === idx) || { color_hex: undefined, material: 'Empty' };
    });

    const renderStatusText = () => {
        if (isPrinting) return `${progress}%`;
        if (isCooldown) return (
            <div className="flex items-center gap-1.5 text-blue-400 min-w-0">
                <Snowflake size={12} className="animate-pulse flex-shrink-0" />
                <span className="truncate">COOLING...</span>
            </div>
        );
        if (isClearingBed) return (
            <div className="flex items-center gap-1.5 text-amber-400 animate-pulse min-w-0">
                <ArrowRightLeft size={12} className="flex-shrink-0" />
                <span className="truncate">EJECTING...</span>
            </div>
        );
        return <span className="truncate text-slate-400 font-bold">{status.toUpperCase().replace('_', ' ')}</span>;
    };

    return (
        <div className={cn(
            "group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg transition-all hover:border-slate-700 min-h-[175px]",
            "flex flex-col select-none p-4",
            isActionRequired && "ring-1 ring-inset ring-white/10"
        )}>
            {/* Delete Confirmation Overlay */}
            {showDeleteConfirm && (
                <div className="absolute inset-0 z-50 bg-slate-950/95 flex flex-col items-center justify-center text-center p-4">
                    <AlertTriangle className="text-red-500 mb-2" size={24} />
                    <p className="text-white font-bold text-sm mb-1">Delete Printer?</p>
                    <p className="text-slate-400 text-[10px] mb-4 uppercase tracking-tighter">{printer.name}</p>
                    <div className="flex gap-2 w-full">
                        <button onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(false); }} className="flex-1 py-1.5 bg-slate-800 text-slate-300 text-xs font-bold rounded-lg hover:bg-slate-700">Cancel</button>
                        <button onClick={handleDelete} className="flex-1 py-1.5 bg-red-600 text-white text-xs font-bold rounded-lg hover:bg-red-500 transition-colors uppercase">
                            {isDeleting ? <Loader2 size={12} className="animate-spin" /> : 'Delete'}
                        </button>
                    </div>
                </div>
            )}

            {/* ═══════════════════════════════════════════════════════════════ */}
            {/* ZONE 1: HEADER (Identity) */}
            {/* ═══════════════════════════════════════════════════════════════ */}
            <div className="flex justify-between items-center gap-3 mb-4">
                <TooltipProvider>
                    <Tooltip>
                        <TooltipTrigger asChild>
                            <div className="flex items-center gap-2.5 overflow-hidden min-w-0 flex-1 cursor-default">
                                <div className={cn(
                                    "w-2 h-2 rounded-full shadow-[0_0_8px_rgba(0,0,0,0.5)] flex-shrink-0",
                                    config.progress,
                                    isActionRequired && "animate-pulse"
                                )} />
                                <h3 className="font-bold text-white uppercase tracking-tight text-[13px] truncate leading-none">
                                    {printer.name}
                                </h3>
                            </div>
                        </TooltipTrigger>
                        <TooltipContent side="top" className="max-w-[300px] break-all">
                            <p>{printer.name}</p>
                        </TooltipContent>
                    </Tooltip>
                </TooltipProvider>

                <div className="flex items-center gap-1 flex-shrink-0">
                    <TooltipProvider>
                        <Tooltip>
                            <TooltipTrigger asChild>
                                <button
                                    onClick={(e) => { e.stopPropagation(); setIsCameraOpen(true); }}
                                    disabled={status === 'offline'}
                                    className={cn(
                                        "p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all active:scale-95 disabled:opacity-30 disabled:cursor-not-allowed",
                                        status !== 'offline' && "hover:text-amber-400"
                                    )}
                                >
                                    <Camera size={14} />
                                </button>
                            </TooltipTrigger>
                            <TooltipContent side="top">
                                <p>View Live Stream</p>
                            </TooltipContent>
                        </Tooltip>
                    </TooltipProvider>

                    <div className="relative">
                        <button
                            onClick={(e) => { e.stopPropagation(); setShowDropdown(!showDropdown); }}
                            className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all active:scale-95"
                        >
                            <MoreVertical size={14} />
                        </button>

                        {showDropdown && (
                            <>
                                <div className="fixed inset-0 z-40" onClick={() => setShowDropdown(false)} />
                                <div className="absolute right-0 top-full mt-1 z-50 bg-slate-800 border border-slate-700 rounded-lg shadow-xl py-1 min-w-[140px] animate-in fade-in slide-in-from-top-1">
                                    <button onClick={(e) => { e.stopPropagation(); onSettingsClick?.(printer); setShowDropdown(false); }} className="w-full px-3 py-2 text-left text-xs text-slate-300 hover:bg-slate-700 hover:text-white flex items-center gap-2 transition-colors">
                                        <Settings size={12} /> Settings
                                    </button>
                                    <div className="h-px bg-slate-700 my-1" />
                                    <button onClick={(e) => { e.stopPropagation(); setShowDeleteConfirm(true); setShowDropdown(false); }} className="w-full px-3 py-2 text-left text-xs text-red-400 hover:bg-red-500/10 hover:text-red-300 flex items-center gap-2 transition-colors">
                                        <Trash2 size={12} /> Delete Printer
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                </div>
            </div>

            {/* ═══════════════════════════════════════════════════════════════ */}
            {/* ZONE 2: BODY (Integrated Filament Tray) */}
            {/* ═══════════════════════════════════════════════════════════════ */}
            <div className="grid grid-cols-4 gap-2 mb-4">
                {amsDisplay.map((slot, idx) => {
                    const isEmpty = !slot.color_hex;
                    const bgColor = formatColor(slot.color_hex);

                    return (
                        <div
                            key={idx}
                            className={cn(
                                "h-12 rounded-lg bg-zinc-900 border border-white/5 flex flex-col items-center justify-between p-1.5 relative group/slot transition-all",
                                isEmpty ? "opacity-40 grayscale" : "hover:border-white/10"
                            )}
                            title={`Slot A${idx + 1}: ${slot.material || 'Empty'}`}
                        >
                            <span className="absolute top-1 left-1.5 text-[8px] font-black text-muted-foreground uppercase opacity-40">
                                A{idx + 1}
                            </span>

                            <div className="flex-1 flex items-end justify-center w-full pb-1">
                                {!isEmpty ? (
                                    <div
                                        className="h-1.5 w-6 rounded-full shadow-sm"
                                        style={{ backgroundColor: bgColor }}
                                    />
                                ) : (
                                    <div className="h-1.5 w-6 rounded-full bg-slate-700/30 dashed border border-slate-700/50" />
                                )}
                            </div>
                        </div>
                    );
                })}
            </div>

            {/* ═══════════════════════════════════════════════════════════════ */}
            {/* ZONE 3: FOOTER (Progress & Action) */}
            {/* ═══════════════════════════════════════════════════════════════ */}
            <div className="mt-auto">
                {isActionRequired ? (
                    <button
                        onClick={isAwaitingClearance ? handleClearance : handleClearError}
                        disabled={isActionPending}
                        className={cn(
                            "w-full h-11 rounded-lg font-black text-xs uppercase tracking-widest flex items-center justify-center gap-2 transition-all active:scale-[0.98] border border-white/10 animate-pulse",
                            isAwaitingClearance
                                ? "bg-emerald-500 hover:bg-emerald-400 text-white shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                                : "bg-orange-600 hover:bg-orange-500 text-white shadow-[0_0_15px_rgba(234,88,12,0.3)]"
                        )}
                    >
                        {isActionPending ? <Loader2 size={16} className="animate-spin" /> : (
                            <>
                                {isAwaitingClearance ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
                                <span>{isAwaitingClearance ? 'CONFIRM BED EMPTY' : 'RESOLVE ERROR'}</span>
                            </>
                        )}
                    </button>
                ) : (
                    <div className="space-y-2">
                        <div className="flex justify-between items-center text-[9px] font-black uppercase tracking-widest h-3 px-0.5">
                            <div className={cn("flex items-center gap-2", config.text)}>
                                {renderStatusText()}
                            </div>
                            {timeLeft && (
                                <span className="text-slate-500 flex items-center gap-1 font-mono">
                                    <Clock size={9} /> {timeLeft}
                                </span>
                            )}
                        </div>
                        <div className="h-2.5 w-full bg-slate-800/80 rounded-full overflow-hidden border border-slate-700/20">
                            <div
                                className={cn("h-full transition-all duration-1000 rounded-full", config.progress, (isClearingBed || isCooldown) && "animate-pulse")}
                                style={{ width: (isCooldown || isClearingBed) ? '100%' : `${progress}%` }}
                            />
                        </div>
                    </div>
                )}
            </div>
            {/* ═══════════════════════════════════════════════════════════════ */}
            {/* DIALOGS */}
            {/* ═══════════════════════════════════════════════════════════════ */}
            <PrinterCameraDialog
                printer={printer}
                open={isCameraOpen}
                onOpenChange={setIsCameraOpen}
            />
        </div>
    );
}
