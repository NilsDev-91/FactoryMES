'use client';

import React, { useState } from 'react';
import { Eraser } from 'lucide-react';
import { Printer } from '@/types/printer';
import { mutate } from 'swr';
import { Loader2 } from 'lucide-react';

interface PrinterControlsProps {
    printer: Printer;
}

export function PrinterControls({ printer }: PrinterControlsProps) {
    const [isClearing, setIsClearing] = useState(false);

    // Show ONLY if printer.status === 'IDLE' AND printer.is_plate_cleared === false
    const shouldShowReleasePlate =
        (printer.current_status || 'IDLE') === 'IDLE' &&
        printer.is_plate_cleared === false;

    if (!shouldShowReleasePlate) {
        return null; // Don't render anything if conditions aren't met
    }

    const handleReleasePlate = async () => {
        setIsClearing(true);
        try {
            const res = await fetch(`http://127.0.0.1:8000/api/printers/${printer.serial}/action/clear-plate`, {
                method: 'POST'
            });

            if (!res.ok) {
                const errorData = await res.json();
                throw new Error(errorData.detail || 'Failed to release plate');
            }

            // Optimistic / Revalidation
            mutate('http://127.0.0.1:8000/api/printers');
        } catch (error) {
            console.error(error);
            alert('Failed to release plate');
        } finally {
            setIsClearing(false);
        }
    };

    return (
        <div className="">
            <button
                onClick={(e) => {
                    e.stopPropagation();
                    handleReleasePlate();
                }}
                disabled={isClearing}
                className="flex items-center justify-center gap-1.5 px-3 py-1 bg-emerald-500/10 border border-emerald-500/50 text-emerald-500 hover:bg-emerald-500 hover:text-white rounded text-[10px] font-bold uppercase tracking-wider transition-all"
            >
                {isClearing ? (
                    <Loader2 className="animate-spin" size={12} />
                ) : (
                    <Eraser size={12} />
                )}
                <span>Clear Plate</span>
            </button>
        </div>
    );
}
