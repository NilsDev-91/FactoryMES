
'use client';

import React from 'react';
import useSWR from 'swr';
import { PrinterCard, Printer } from '@/components/dashboard/PrinterCard';
import { Loader2, Printer as PrinterIcon, AlertTriangle } from 'lucide-react';
import { PrinterDetailModal } from '@/components/modals/PrinterDetailModal';


import { AddPrinterCard } from '@/components/dashboard/AddPrinterCard';
import { AddPrinterDialog } from '@/components/dashboard/AddPrinterDialog';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function PrintersPage() {
    const { data: printers, error, isLoading } = useSWR<Printer[]>('http://127.0.0.1:8000/api/printers', fetcher, { refreshInterval: 5000 });

    const [selectedSerial, setSelectedSerial] = React.useState<string | null>(null);
    const [showAddDialog, setShowAddDialog] = React.useState(false);

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
                        <p className="text-slate-400 text-sm">Manage and monitor all connected devices</p>
                    </div>
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

            {/* Grid */}
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
