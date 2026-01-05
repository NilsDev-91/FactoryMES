
'use client';

import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { getPrinters } from '@/lib/api/printer-commands';
import { PrinterCard } from '@/components/dashboard/PrinterCard';
import { CompactPrinterCard } from '@/components/dashboard/CompactPrinterCard';
import { Printer } from '@/types/printer';
import { Loader2, Printer as PrinterIcon, AlertTriangle, LayoutGrid, List } from 'lucide-react';
import { PrinterDetailModal } from '@/components/modals/PrinterDetailModal';


import { AddPrinterCard } from '@/components/dashboard/AddPrinterCard';
import { AddPrinterDialog } from '@/components/dashboard/AddPrinterDialog';

type ViewMode = 'grid' | 'compact';

export default function PrintersPage() {
    const { data: printers, error, isLoading } = useQuery<Printer[]>({
        queryKey: ['printers'],
        queryFn: getPrinters,
    });

    const [selectedSerial, setSelectedSerial] = React.useState<string | null>(null);
    const [showAddDialog, setShowAddDialog] = React.useState(false);

    // View mode state with localStorage persistence
    const [viewMode, setViewMode] = React.useState<ViewMode>(() => {
        if (typeof window !== 'undefined') {
            return (localStorage.getItem('printerViewMode') as ViewMode) || 'grid';
        }
        return 'grid';
    });

    // Persist view mode to localStorage
    const handleViewModeChange = (mode: ViewMode) => {
        setViewMode(mode);
        localStorage.setItem('printerViewMode', mode);
    };

    // Derived state for live updates
    const activePrinter = React.useMemo(() =>
        printers?.find(p => p.serial === selectedSerial) || null,
        [printers, selectedSerial]);

    return (
        <div className="space-y-6 max-w-[1600px] mx-auto">
            <header className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-500">
                        <PrinterIcon size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Printer Fleet</h1>
                        <p className="text-slate-400 text-sm">
                            {printers?.length || 0} devices • {viewMode === 'compact' ? 'Compact View' : 'Grid View'}
                        </p>
                    </div>
                </div>

                {/* View Mode Toggle */}
                <div className="flex items-center gap-1 bg-slate-800/50 p-1 rounded-lg border border-slate-700/50">
                    <button
                        onClick={() => handleViewModeChange('grid')}
                        className={`p-2 rounded-md transition-all ${viewMode === 'grid'
                            ? 'bg-indigo-500 text-white shadow-lg'
                            : 'text-slate-400 hover:text-white hover:bg-slate-700'
                            }`}
                        title="Grid View"
                    >
                        <LayoutGrid size={18} />
                    </button>
                    <button
                        onClick={() => handleViewModeChange('compact')}
                        className={`p-2 rounded-md transition-all ${viewMode === 'compact'
                            ? 'bg-indigo-500 text-white shadow-lg'
                            : 'text-slate-400 hover:text-white hover:bg-slate-700'
                            }`}
                        title="Compact View (High Density)"
                    >
                        <List size={18} />
                    </button>
                </div>
            </header>

            {/* Error State */}
            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg flex items-center gap-2">
                    <AlertTriangle size={20} />
                    <span>Failed to load printers. Is the backend running?</span>
                </div>
            )}

            {/* Loading State */}
            {isLoading && !printers && (
                <div className="flex items-center justify-center p-20 text-slate-500">
                    <Loader2 size={48} className="animate-spin mb-2" />
                </div>
            )}

            {/* Empty State */}
            {printers && printers.length === 0 && (
                <div className="text-center p-20 border border-dashed border-slate-800 rounded-2xl bg-slate-900/50">
                    <p className="text-slate-500 text-lg">No printers found in the database.</p>
                </div>
            )}

            {/* Grid View */}
            {viewMode === 'grid' && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-6 items-stretch">
                    {printers?.map((printer) => (
                        <div key={printer.serial} onClick={() => setSelectedSerial(printer.serial)} className="cursor-pointer">
                            <PrinterCard
                                printer={printer}
                                onSettingsClick={(p) => setSelectedSerial(p.serial)}
                            />
                        </div>
                    ))}

                    {/* Add Printer Card */}
                    <AddPrinterCard onClick={() => setShowAddDialog(true)} />
                </div>
            )}

            {/* Compact View (High Density) */}
            {viewMode === 'compact' && (
                <div className="space-y-1.5">
                    {/* Compact Header Row */}
                    <div className="flex items-center gap-3 px-4 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500 border-b border-slate-800">
                        <span className="w-2"></span>
                        <span className="w-2"></span>
                        <span className="w-[120px]">Name</span>
                        <span className="flex-1 min-w-[60px]">Progress</span>
                        <span className="w-8 text-right">%</span>
                        <span className="w-12 text-right">Time</span>
                    </div>

                    {/* Compact Printer Rows */}
                    {printers?.map((printer) => (
                        <CompactPrinterCard
                            key={printer.serial}
                            printer={printer}
                            onClick={(p) => setSelectedSerial(p.serial)}
                        />
                    ))}

                    {/* Add Printer Row */}
                    <button
                        onClick={() => setShowAddDialog(true)}
                        className="w-full flex items-center justify-center gap-2 py-2 border border-dashed border-slate-700 rounded-lg text-slate-500 hover:text-indigo-400 hover:border-indigo-500/50 transition-all"
                    >
                        <span className="text-lg">+</span>
                        <span className="text-xs font-medium">Add Printer</span>
                    </button>
                </div>
            )}

            {/* Add Dialog */}
            <AddPrinterDialog
                isOpen={showAddDialog}
                onClose={() => setShowAddDialog(false)}
            />

            {/* Detail Modal */}
            <PrinterDetailModal
                isOpen={!!activePrinter}
                printer={activePrinter}
                onClose={() => setSelectedSerial(null)}
            />
        </div>
    );
}
