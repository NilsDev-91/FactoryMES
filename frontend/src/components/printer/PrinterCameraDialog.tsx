"use client"

import React from 'react'
import { Camera, Check, Loader2, Info } from 'lucide-react'
import {
    Dialog,
    DialogContent,
    DialogHeader,
    DialogTitle,
} from "@/components/ui/dialog"
import { Printer } from '../../types/printer'
import { usePrinterAction } from '@/hooks/use-printer-action'
import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs))
}

interface PrinterCameraDialogProps {
    printer: Printer
    open: boolean
    onOpenChange: (open: boolean) => void
}

export function PrinterCameraDialog({ printer, open, onOpenChange }: PrinterCameraDialogProps) {
    const status = (printer.current_status || '').toUpperCase()
    const canVerify = status === 'AWAITING_CLEARANCE' || status === 'MANUAL_CLEARANCE'

    const { mutate: runAction, isPending: isActionPending } = usePrinterAction(printer.serial)

    const handleVerify = () => {
        runAction('CONFIRM_CLEARANCE')
    }

    const handleSnapshot = () => {
        console.log("Taking Snapshot for", printer.serial)
        // Placeholder for snapshot logic
    }

    const [streamUrl, setStreamUrl] = React.useState<string | null>(null)
    const [isLoading, setIsLoading] = React.useState(true)

    React.useEffect(() => {
        if (open && printer.serial) {
            setIsLoading(true)
            fetch(`http://127.0.0.1:8000/api/printers/${printer.serial}/stream`)
                .then(res => res.json())
                .then(data => {
                    // Backend now returns the full embedded player URL with media=video
                    if (data.stream_url) {
                        setStreamUrl(data.stream_url)
                    }
                })
                .catch(err => console.error("Stream fetch failed", err))
                .finally(() => setIsLoading(false))
        }
    }, [open, printer.serial])

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="sm:max-w-2xl bg-slate-900 border-slate-800 p-0 overflow-hidden">
                <DialogHeader className="p-4 border-b border-white/5 bg-slate-950/50">
                    <DialogTitle className="text-sm font-black uppercase tracking-widest flex items-center justify-between">
                        <span className="flex items-center gap-2">
                            <Camera size={14} className="text-amber-400" />
                            Monitoring: {printer.name}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono tracking-tighter">
                            SN: {printer.serial}
                        </span>
                    </DialogTitle>
                </DialogHeader>

                <div className="p-4 space-y-4">
                    {/* Video Container */}
                    <div className="relative aspect-video bg-black rounded-lg border border-white/5 overflow-hidden flex items-center justify-center group">
                        {isLoading ? (
                            <div className="flex flex-col items-center gap-3 text-slate-500">
                                <Loader2 size={32} className="animate-spin text-amber-500/50" />
                                <p className="text-[10px] uppercase font-black tracking-[0.2em]">Connecting to RTSPS Stream...</p>
                            </div>
                        ) : streamUrl ? (
                            <iframe
                                src={streamUrl}
                                className="w-full h-full border-none"
                                allow="autoplay; fullscreen"
                            />
                        ) : (
                            <div className="flex flex-col items-center gap-3 text-slate-500">
                                <Info size={32} className="text-slate-700" />
                                <p className="text-[10px] uppercase font-black tracking-[0.2em] text-red-500">Stream Unavailable</p>
                            </div>
                        )}

                        {/* LIVE Badge */}
                        <div className="absolute top-3 left-3 flex items-center gap-1.5 bg-black/60 backdrop-blur-md border border-white/10 px-2 py-1 rounded-md pointer-events-none">
                            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
                            <span className="text-[9px] font-black text-white uppercase tracking-wider">Live</span>
                        </div>
                    </div>

                    {/* Control Bar */}
                    <div className="flex items-center justify-between bg-slate-950/40 border border-white/5 p-3 rounded-lg">
                        {/* Left: Metadata */}
                        <div className="flex items-center gap-4 text-[9px] font-black uppercase tracking-widest text-slate-500">
                            <div className="flex items-center gap-1.5">
                                <Info size={10} className="text-blue-400" />
                                <span>Res: 1080p</span>
                            </div>
                            <div className="flex items-center gap-1.5 border-l border-white/10 pl-4">
                                <span className="text-emerald-500">●</span>
                                <span>FPS: 30</span>
                            </div>
                        </div>

                        {/* Right: Actions */}
                        <div className="flex items-center gap-2">
                            <button
                                onClick={handleSnapshot}
                                className="flex items-center gap-2 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-md text-[10px] font-bold transition-all active:scale-95 group"
                            >
                                <Camera size={12} className="group-hover:text-amber-400" />
                                <span>Take Snapshot</span>
                            </button>

                            {canVerify && (
                                <button
                                    onClick={handleVerify}
                                    disabled={isActionPending}
                                    className="flex items-center gap-2 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-md text-[10px] font-bold transition-all active:scale-95 shadow-lg shadow-emerald-900/20"
                                >
                                    {isActionPending ? <Loader2 size={12} className="animate-spin" /> : <Check size={12} />}
                                    <span>Verify Bed Empty</span>
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            </DialogContent>
        </Dialog>
    )
}
