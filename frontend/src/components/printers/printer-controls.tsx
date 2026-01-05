'use client';

import React, { useState } from 'react';
import { Eraser, Loader2 } from 'lucide-react';
import { Printer } from '@/types/printer';
import { mutate } from 'swr';

interface PrinterControlsProps {
    printer: Printer;
}

export function PrinterControls({ printer }: PrinterControlsProps) {
    const [isActionPending, setIsActionPending] = useState(false);

    const status = (printer.current_status || 'IDLE').toUpperCase();
    const isAwaitingClearance = status === 'AWAITING_CLEARANCE';

    if (isAwaitingClearance) return null;

    const handleAction = async (endpoint: string, method: string = 'POST', body?: any) => {
        setIsActionPending(true);
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/printers/${printer.serial}${endpoint}`, {
                method,
                headers: body ? { 'Content-Type': 'application/json' } : {},
                body: body ? JSON.stringify(body) : undefined
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || 'Action failed');
            }

            mutate('http://127.0.0.1:8000/api/printers');
        } catch (error: any) {
            console.error(error);
            alert(error.message || 'Action failed');
        } finally {
            setIsActionPending(false);
        }
    };

    const isPlateNeedsRelease = printer.is_plate_cleared === false && status === 'IDLE';

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden w-full max-w-[140px]">
            <div className="p-3">
                <div className="space-y-3">
                    {isPlateNeedsRelease ? (
                        <button
                            onClick={() => handleAction('/action/clear-plate')}
                            disabled={isActionPending}
                            className="w-full flex items-center justify-center gap-2 py-2 bg-emerald-500/10 border border-emerald-500/50 text-emerald-500 hover:bg-emerald-500 hover:text-white rounded text-xs font-bold uppercase tracking-wider transition-all"
                        >
                            {isActionPending ? <Loader2 className="animate-spin" size={14} /> : <Eraser size={14} />}
                            <span>Release Plate</span>
                        </button>
                    ) : (
                        <p className="text-[10px] text-slate-500 text-center py-2 italic font-mono uppercase tracking-tighter">No actions available</p>
                    )}
                </div>
            </div>
        </div>
    );
}

// Helper for Tailwind
function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}
