'use client';

import React, { useState } from 'react';
import { Upload, FileText, CheckCircle2, AlertTriangle, Loader2, X } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility for Tailwind class merging
 */
function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface FileUploadProps {
    onUploadSuccess: (id: number, filename: string) => void;
    onReset: () => void;
    className?: string;
    existingFilename?: string;
}

/**
 * Reusable FileUpload component that handles async upload to /api/products/upload
 * and returns the backend database ID of the created PrintFile.
 */
export function FileUpload({
    onUploadSuccess,
    onReset,
    className,
    existingFilename
}: FileUploadProps) {
    const [file, setFile] = useState<File | null>(null);
    const [dragActive, setDragActive] = useState(false);
    const [status, setStatus] = useState<'idle' | 'uploading' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');
    const [fileName, setFileName] = useState(existingFilename || '');

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            uploadFile(e.target.files[0]);
        }
    };

    const handleDrag = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            uploadFile(e.dataTransfer.files[0]);
        }
    };

    const uploadFile = async (selectedFile: File) => {
        // Validation
        if (!selectedFile.name.endsWith('.3mf') && !selectedFile.name.endsWith('.gcode')) {
            setStatus('error');
            setErrorMessage("Invalid file type. Please upload a .3mf or .gcode file.");
            return;
        }

        setFile(selectedFile);
        setStatus('uploading');
        setErrorMessage('');

        try {
            const formData = new FormData();
            formData.append('file', selectedFile);

            const uploadRes = await fetch('http://127.0.0.1:8000/api/products/upload', {
                method: 'POST',
                body: formData,
            });

            if (!uploadRes.ok) {
                const errData = await uploadRes.json();
                throw new Error(errData.detail || 'File upload failed');
            }

            const data = await uploadRes.json();

            // data.id is the PrintFile ID from backend
            setStatus('success');
            setFileName(selectedFile.name);
            onUploadSuccess(data.id, selectedFile.name);

        } catch (error: any) {
            setStatus('error');
            setErrorMessage(error.message || 'An unknown error occurred during upload');
        }
    };

    const reset = (e: React.MouseEvent) => {
        e.stopPropagation();
        setFile(null);
        setFileName('');
        setStatus('idle');
        setErrorMessage('');
        onReset();
    };

    return (
        <div className={cn("space-y-2", className)}>
            <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                className={cn(
                    "border-2 border-dashed rounded-2xl p-8 transition-all duration-200 flex flex-col items-center justify-center text-center cursor-pointer relative group min-h-[180px]",
                    dragActive ? "border-blue-500 bg-blue-500/10" : "border-slate-800 bg-slate-950/50 hover:border-slate-700 hover:bg-slate-900",
                    status === 'success' && "border-green-500/50 bg-green-500/5",
                    status === 'error' && "border-red-500/30 bg-red-500/5"
                )}
            >
                {status === 'idle' || status === 'uploading' ? (
                    <input
                        type="file"
                        accept=".3mf,.gcode"
                        className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
                        onChange={handleFileSelect}
                        disabled={status === 'uploading'}
                    />
                ) : null}

                {status === 'uploading' ? (
                    <div className="flex flex-col items-center animate-in fade-in duration-300">
                        <div className="w-12 h-12 bg-blue-500/10 rounded-full flex items-center justify-center mb-3">
                            <Loader2 className="text-blue-500 animate-spin" size={24} />
                        </div>
                        <p className="text-blue-400 font-medium tracking-tight">Uploading {file?.name}...</p>
                        <p className="text-slate-500 text-sm mt-1">Please wait while we process the asset</p>
                    </div>
                ) : status === 'success' ? (
                    <div className="flex flex-col items-center animate-in zoom-in-95 duration-300">
                        <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center mb-3 shadow-lg shadow-green-500/20">
                            <CheckCircle2 className="text-white" size={24} />
                        </div>
                        <p className="text-green-400 font-bold text-lg tracking-tight">{fileName}</p>
                        <p className="text-slate-500 text-sm mt-1">Asset linked successfully</p>

                        <button
                            onClick={reset}
                            className="mt-4 text-xs font-bold uppercase tracking-widest text-slate-500 hover:text-white transition-colors flex items-center gap-1.5"
                        >
                            <X size={12} /> Remove File
                        </button>
                    </div>
                ) : status === 'error' ? (
                    <div className="flex flex-col items-center animate-in shake duration-300">
                        <div className="w-12 h-12 bg-red-500/20 rounded-full flex items-center justify-center mb-3">
                            <AlertTriangle className="text-red-500" size={24} />
                        </div>
                        <p className="text-red-400 font-bold tracking-tight">Upload Error</p>
                        <p className="text-slate-500 text-sm mt-1 px-4 max-w-xs">{errorMessage}</p>

                        <button
                            onClick={reset}
                            className="mt-4 text-xs font-bold uppercase tracking-widest text-blue-400 hover:text-blue-300 transition-colors"
                        >
                            Try Again
                        </button>
                    </div>
                ) : (
                    <>
                        <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                            <Upload className="text-slate-400 group-hover:text-white" size={24} />
                        </div>
                        <p className="text-slate-300 font-medium">Drag & Drop or Click to Upload</p>
                        <p className="text-slate-500 text-sm mt-1">Supports .3mf and .gcode files</p>
                    </>
                )}
            </div>
        </div>
    );
}
