
import React from 'react';
import { Plus } from 'lucide-react';

interface AddPrinterCardProps {
    onClick: () => void;
}

export const AddPrinterCard: React.FC<AddPrinterCardProps> = ({ onClick }) => {
    return (
        <div
            onClick={onClick}
            className="group relative flex flex-col items-center justify-center p-6 h-full min-h-[150px] rounded-xl border border-dashed border-slate-700 hover:border-blue-500 bg-slate-900/20 hover:bg-slate-900/50 cursor-pointer transition-all duration-300"
        >
            <div className="flex flex-col items-center gap-2">
                <div className="p-2 rounded-full bg-slate-800 group-hover:bg-blue-600 transition-colors shadow-lg group-hover:shadow-blue-500/30">
                    <Plus className="text-slate-400 group-hover:text-white transition-colors" size={20} />
                </div>
                <div className="text-center">
                    <h3 className="text-slate-400 group-hover:text-white font-bold text-sm transition-colors uppercase tracking-wide">Add Device</h3>
                    <p className="text-[10px] text-slate-600 group-hover:text-slate-400">Connect new hardware</p>
                </div>
            </div>
        </div>
    );
};
