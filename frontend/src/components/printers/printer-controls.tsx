'use client';

import React, { useState } from 'react';
import { Eraser, Zap, Loader2 } from 'lucide-react';
import { Printer } from '@/types/printer';
import { mutate } from 'swr';

interface PrinterControlsProps {
    printer: Printer;
}

export function PrinterControls({ printer }: PrinterControlsProps) {
    const [activeTab, setActiveTab] = useState<'actions' | 'calibration'>('actions');
    const [isActionPending, setIsActionPending] = useState(false);

    // Live Z from telemetry (if available)
    const currentZ = printer.telemetry?.z_height ?? 0;
    const isZSafe = currentZ >= 2.0;

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

            // Revalidate fleet state
            mutate('http://127.0.0.1:8000/api/printers');
        } catch (error: any) {
            console.error(error);
            alert(error.message || 'Action failed');
        } finally {
            setIsActionPending(false);
        }
    };

    const handleJog = (axis: string, distance: number) => {
        const params = new URLSearchParams({ axis, distance: distance.toString() });
        handleAction(`/control/jog?${params.toString()}`);
    };

    return (
        <div className="bg-slate-900 border border-slate-800 rounded-lg overflow-hidden w-full max-w-sm">
            {/* Tabs */}
            <div className="flex border-b border-slate-800 bg-slate-950/50">
                <button
                    onClick={() => setActiveTab('actions')}
                    className={cn(
                        "flex-1 px-4 py-2 text-[10px] font-bold uppercase tracking-wider transition-all",
                        activeTab === 'actions' ? "text-blue-400 border-b border-blue-400 bg-blue-400/5" : "text-slate-500 hover:text-slate-300"
                    )}
                >
                    Actions
                </button>
                <button
                    onClick={() => setActiveTab('calibration')}
                    className={cn(
                        "flex-1 px-4 py-2 text-[10px] font-bold uppercase tracking-wider transition-all",
                        activeTab === 'calibration' ? "text-amber-400 border-b border-amber-400 bg-amber-400/5" : "text-slate-500 hover:text-slate-300"
                    )}
                >
                    Calibration
                </button>
            </div>

            <div className="p-3">
                {activeTab === 'actions' ? (
                    <div className="space-y-3">
                        {printer.is_plate_cleared === false && (printer.current_status || 'IDLE') === 'IDLE' ? (
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
                ) : (
                    <div className="space-y-4">
                        {/* Z-Height Status */}
                        <div className="flex items-center justify-between px-2 py-1.5 bg-slate-950 rounded border border-slate-800">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Current Z</span>
                            <span className={cn(
                                "text-xs font-mono font-bold",
                                isZSafe ? "text-blue-400" : "text-red-500 animate-pulse"
                            )}>
                                {currentZ.toFixed(2)}mm
                            </span>
                        </div>

                        {/* Jog Controls */}
                        <div className="space-y-2">
                            <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-1">Teach-In (Z-Axis)</span>
                            <div className="grid grid-cols-2 gap-2">
                                <div className="flex flex-col gap-1">
                                    {[10, 1, 0.1].map(val => (
                                        <button
                                            key={`up-${val}`}
                                            onClick={() => handleJog('Z', val)}
                                            disabled={isActionPending}
                                            className="py-1 bg-slate-800 hover:bg-blue-600 text-white rounded text-[10px] font-bold transition-all disabled:opacity-50"
                                        >
                                            +{val}
                                        </button>
                                    ))}
                                </div>
                                <div className="flex flex-col gap-1">
                                    {[-10, -1, -0.1].map(val => (
                                        <button
                                            key={`down-${val}`}
                                            onClick={() => handleJog('Z', val)}
                                            disabled={isActionPending}
                                            className="py-1 bg-slate-800 hover:bg-red-600 text-white rounded text-[10px] font-bold transition-all disabled:opacity-50"
                                        >
                                            {val}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Test Sweep */}
                        <button
                            onClick={() => handleAction('/control/test-sweep')}
                            disabled={isActionPending || !isZSafe}
                            className="w-full flex items-center justify-center gap-2 py-2 bg-amber-500/10 border border-amber-500/50 text-amber-400 hover:bg-amber-500 hover:text-white rounded text-[10px] font-bold uppercase tracking-wider transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {isActionPending ? <Loader2 className="animate-spin" size={14} /> : <Zap size={14} />}
                            <span>Test Sweep (Safe Mode)</span>
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
}

// Helper for Tailwind
function cn(...inputs: any[]) {
    return inputs.filter(Boolean).join(' ');
}


