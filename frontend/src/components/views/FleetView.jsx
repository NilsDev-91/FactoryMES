import React from 'react';
import PrinterCard from '../PrinterCard';
import { Filter } from 'lucide-react';

const FleetView = ({ printers = [] }) => {
    // Logic moved from DashboardGrid
    // Note: printers are passed as props now to keep the View dumb if possible,
    // or we can consume them from SWR here too.
    // Plan said to move grid logic here.

    // To keep it simple and consistent with DashboardView sharing data, 
    // we'll assume 'printers' prop is the source of truth from App.jsx or active SWR in App.

    if (!printers.length) {
        return <div className="text-center text-slate-500 mt-20">No active printers found.</div>;
    }

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header / Controls */}
            <div className="flex justify-between items-center bg-slate-800/50 p-4 rounded-xl border border-slate-700/50 backdrop-blur-sm">
                <div>
                    <h2 className="text-xl font-bold text-white tracking-tight">Fleet Operations</h2>
                    <p className="text-sm text-slate-400">Real-time telemetry and control</p>
                </div>

                <button className="flex items-center gap-2 text-sm font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-2 rounded-lg border border-slate-600 transition-all hover:shadow-lg">
                    <Filter size={16} /> Filter Units
                </button>
            </div>

            {/* Grid */}
            <div className="grid gap-6" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
                {printers.map((printer) => (
                    <PrinterCard
                        key={printer.serial || printer.id}
                        printer={printer}
                    />
                ))}
            </div>
        </div>
    );
};

export default FleetView;
