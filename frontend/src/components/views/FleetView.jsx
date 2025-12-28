import React, { useState } from 'react';
import PrinterCard from '../PrinterCard';
import PrinterDetailModal from '../modals/PrinterDetailModal';
import { Filter, Plus } from 'lucide-react';

const FleetView = ({ printers = [], onAddClick }) => {
    const [selectedPrinter, setSelectedPrinter] = useState(null);

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500 pb-20">
            {/* Header / Controls */}
            <div className="flex justify-between items-center bg-slate-800/50 p-4 rounded-xl border border-slate-700/50 backdrop-blur-sm">
                <div>
                    <h2 className="text-xl font-bold text-white tracking-tight">Fleet Operations</h2>
                    <p className="text-sm text-slate-400">High-density farm orchestration</p>
                </div>

                <div className="flex gap-3">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900/50 rounded-lg border border-slate-700/50">
                        <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{printers.filter(p => p.current_status?.toLowerCase() === 'printing').length} Printing</span>
                    </div>
                    <button className="flex items-center gap-2 text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg border border-slate-600 transition-all hover:shadow-lg">
                        <Filter size={16} /> Filter
                    </button>
                </div>
            </div>

            {/* High-Density Grid */}
            <div className="grid gap-4 sm:grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5">
                {/* Compact Ghost Card */}
                <button
                    onClick={onAddClick}
                    className="group flex h-[100px] items-center justify-center gap-3 bg-slate-900/40 border-2 border-dashed border-slate-800 hover:border-blue-500/50 hover:bg-slate-800/40 rounded-xl transition-all duration-300 overflow-hidden"
                >
                    <div className="p-2 bg-slate-800 group-hover:bg-blue-600/20 rounded-lg border border-slate-700 group-hover:border-blue-500/50 transition-all">
                        <Plus className="text-slate-500 group-hover:text-blue-400 transition-colors" size={20} />
                    </div>
                    <div className="text-left font-bold text-slate-400 group-hover:text-white transition-colors uppercase tracking-widest text-xs">
                        Add Device
                    </div>
                </button>

                {/* Refined Printer Cards */}
                {printers.map((printer) => (
                    <PrinterCard
                        key={printer.serial || printer.id}
                        printer={printer}
                        onSettingsClick={(p) => setSelectedPrinter(p)}
                    />
                ))}
            </div>

            {/* Drill-down Detail Modal */}
            <PrinterDetailModal
                printer={selectedPrinter}
                isOpen={!!selectedPrinter}
                onClose={() => setSelectedPrinter(null)}
            />
        </div>
    );
};

export default FleetView;
