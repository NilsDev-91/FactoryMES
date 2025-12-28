import React from 'react';
import { Settings } from 'lucide-react';

interface PrinterProps {
    name: string; // e.g. "Bambu A1 - Master"
    status: 'idle' | 'printing' | 'done' | 'error';
    progress: number; // 0 to 100
    timeLeft?: string; // e.g. "12m"
    thumbnailUrl?: string; // Optional image of the print
    onSettingsClick?: () => void;
}

const PrinterCard: React.FC<PrinterProps> = ({
    name,
    status,
    progress,
    timeLeft,
    thumbnailUrl,
    onSettingsClick
}) => {

    // Color mapping based on strict requirements
    const statusConfig = {
        idle: {
            color: 'border-purple-500',
            text: 'text-purple-500',
            bg: 'bg-purple-500/20',
            progress: 'bg-purple-500',
        },
        printing: {
            color: 'border-yellow-500',
            text: 'text-yellow-500',
            bg: 'bg-yellow-500/20',
            progress: 'bg-yellow-500',
        },
        done: {
            color: 'border-green-500',
            text: 'text-green-500',
            bg: 'bg-green-500/20',
            progress: 'bg-green-500',
        },
        error: {
            color: 'border-red-500',
            text: 'text-red-500',
            bg: 'bg-red-500/20',
            progress: 'bg-red-500',
        }
    };

    const config = statusConfig[status] || statusConfig.idle;

    return (
        <div className={`group relative bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-lg transition-all hover:border-slate-700`}>
            {/* 4px Colored Strip on Left */}
            <div className={`absolute left-0 top-0 bottom-0 w-1 ${config.progress} transition-all group-hover:w-1.5`} />

            <div className="p-4 pl-5">
                {/* Header */}
                <div className="flex justify-between items-center mb-4">
                    <div className="flex items-center gap-2 overflow-hidden">
                        {/* Colored Dot */}
                        <div className={`w-2 h-2 rounded-full ${config.progress} shadow-[0_0_8px_rgba(0,0,0,0.5)]`} />
                        <h3 className="font-bold text-white truncate uppercase tracking-tight" title={name}>
                            {name}
                        </h3>
                    </div>

                    <button
                        onClick={onSettingsClick}
                        className="p-1.5 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all active:scale-95"
                    >
                        <Settings size={18} />
                    </button>
                </div>

                {/* Optional Thumbnail / Main Area */}
                {thumbnailUrl && (
                    <div className="aspect-video bg-slate-950 rounded-lg mb-4 border border-slate-800 overflow-hidden">
                        <img src={thumbnailUrl} alt={name} className="w-full h-full object-cover opacity-80 group-hover:opacity-100 transition-opacity" />
                    </div>
                )}

                {/* Footer (Progress & Time) */}
                <div className="mt-auto space-y-2">
                    {status === 'printing' && (
                        <div className="flex justify-between items-end text-[10px] font-black uppercase tracking-widest leading-none">
                            <span className={config.text}>{progress}%</span>
                            {timeLeft && (
                                <span className="text-slate-500 flex items-center gap-1">
                                    {timeLeft} left
                                </span>
                            )}
                        </div>
                    )}

                    {/* Status Badge (fallback or secondary display) */}
                    {status !== 'printing' && (
                        <div className="flex justify-between items-center">
                            <span className={`text-[10px] font-black uppercase tracking-[0.2em] px-2 py-0.5 rounded ${config.bg} ${config.text}`}>
                                {status}
                            </span>
                        </div>
                    )}

                    {/* Progress Bar */}
                    <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className={`h-full ${config.progress} transition-all duration-1000 shadow-[0_0_10px_rgba(0,0,0,0.5)]`}
                            style={{ width: `${progress}%` }}
                        />
                    </div>
                </div>
            </div>
        </div>
    );
};

export default PrinterCard;
