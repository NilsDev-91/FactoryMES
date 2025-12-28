import React from 'react';
import { Settings, Clock } from 'lucide-react';

const CompactPrinterCard = ({ printer, onSettingsClick }) => {
    const isPrinting = printer.current_status === 'PRINTING';
    const isError = printer.current_status === 'FAILED' || printer.current_status === 'ERROR';

    // Status strip colors
    const statusColor = isPrinting ? 'bg-emerald-500' : isError ? 'bg-rose-500' : 'bg-slate-500';
    const statusBadgeColor = isPrinting ? 'bg-emerald-500/10 text-emerald-400' : isError ? 'bg-rose-500/10 text-rose-400' : 'bg-slate-800 text-slate-400';

    return (
        <div className="flex h-20 items-center bg-slate-900 border border-slate-800 rounded-xl overflow-hidden hover:border-slate-700 transition-all group">
            {/* Status Strip */}
            <div className={`w-1 self-stretch ${statusColor} group-hover:w-1.5 transition-all`} />

            <div className="flex flex-1 items-center px-4 gap-4">
                {/* Identity */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <h3 className="font-bold text-white truncate">{printer.name || "Unknown Printer"}</h3>
                        <span className="text-[10px] uppercase tracking-wider text-slate-500 font-mono bg-slate-800 px-1.5 py-0.5 rounded leading-none">
                            {printer.type || "P1S"}
                        </span>
                    </div>
                    <p className="text-[10px] text-slate-600 font-mono truncate">{printer.serial}</p>
                </div>

                {/* Progress Center */}
                {isPrinting && (
                    <div className="flex-[1.5] flex flex-col gap-1.5 px-4 border-x border-slate-800/50">
                        <div className="flex justify-between items-center text-[10px] font-mono">
                            <span className="text-emerald-400">{printer.current_progress}%</span>
                            <div className="flex items-center gap-1 text-slate-400">
                                <Clock size={10} />
                                <span>{printer.remaining_time}m left</span>
                            </div>
                        </div>
                        <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-emerald-500 transition-all duration-1000"
                                style={{ width: `${printer.current_progress}%` }}
                            />
                        </div>
                    </div>
                )}

                {/* Status & Actions */}
                <div className="flex items-center gap-3">
                    <span className={`text-[10px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full ${statusBadgeColor}`}>
                        {printer.current_status}
                    </span>

                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            onSettingsClick(printer);
                        }}
                        className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all active:scale-90"
                    >
                        <Settings size={18} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default CompactPrinterCard;
