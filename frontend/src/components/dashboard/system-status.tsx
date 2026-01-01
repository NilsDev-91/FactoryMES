
import React from 'react';
import { Radio, Database, Printer as PrinterIcon, Box } from 'lucide-react';

interface SystemStatusProps {
    isDispatcherActive: boolean;
    queueCount: number;
    activePrinterInfo?: {
        serial: string;
        productName: string;
    };
}

export function SystemStatus({ isDispatcherActive, queueCount, activePrinterInfo }: SystemStatusProps) {
    return (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-col gap-4">
            <h3 className="text-xs font-black uppercase tracking-[0.2em] text-slate-500 mb-2 flex items-center gap-2">
                <Radio size={14} className={isDispatcherActive ? "text-green-500 animate-pulse" : "text-red-500"} />
                System Health
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Dispatcher Status */}
                <div className="flex items-center gap-3 px-3 py-2 bg-slate-950/50 rounded-lg border border-slate-800">
                    <div className={`p-2 rounded-md ${isDispatcherActive ? "bg-green-500/10 text-green-500" : "bg-red-500/10 text-red-500"}`}>
                        <Radio size={18} />
                    </div>
                    <div>
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Dispatcher</div>
                        <div className="text-sm font-bold text-white flex items-center gap-1.5">
                            {isDispatcherActive ? 'Active' : 'Offline'}
                            {isDispatcherActive && <span className="h-2 w-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />}
                        </div>
                    </div>
                </div>

                {/* Queue Metrics */}
                <div className="flex items-center gap-3 px-3 py-2 bg-slate-950/50 rounded-lg border border-slate-800">
                    <div className="p-2 rounded-md bg-blue-500/10 text-blue-500">
                        <Database size={18} />
                    </div>
                    <div>
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Queue</div>
                        <div className="text-sm font-bold text-white">{queueCount} Pending Jobs</div>
                    </div>
                </div>

                {/* Active Production */}
                <div className="flex items-center gap-3 px-3 py-2 bg-slate-950/50 rounded-lg border border-slate-800">
                    <div className="p-2 rounded-md bg-purple-500/10 text-purple-500">
                        <PrinterIcon size={18} />
                    </div>
                    <div>
                        <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Active Printer</div>
                        <div className="text-sm font-bold text-white truncate max-w-[150px]">
                            {activePrinterInfo ? (
                                <span title={`${activePrinterInfo.serial} - ${activePrinterInfo.productName}`}>
                                    [{activePrinterInfo.serial.slice(-4)}] {activePrinterInfo.productName}
                                </span>
                            ) : (
                                <span className="text-slate-600 italic">None</span>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
