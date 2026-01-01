'use client';

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { productFormSchema, type ProductFormValues } from '@/lib/validations/product';
import { Package, FileText, AlertTriangle, Loader2, CheckCircle2 } from 'lucide-react';
import { useRouter } from 'next/navigation';

import { FileUpload } from '@/components/files/file-upload';
import { ProfileMultiSelect } from '@/components/products/profile-multi-select';
import { fetchFilamentProfiles } from '@/lib/api/fms';
import { FilamentProfile } from '@/types/api/filament';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// Schema moved to @/lib/validations/product

export function CreateProductForm() {
    const router = useRouter();
    const [profiles, setProfiles] = useState<FilamentProfile[]>([]);
    const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');
    const [uploadedFileName, setUploadedFileName] = useState('');

    const form = useForm<ProductFormValues>({
        resolver: zodResolver(productFormSchema),
        defaultValues: {
            name: '',
            sku: '',
            description: '',
            print_file_id: undefined,
            generate_variants_for_profile_ids: [],
            // Phase 6: Use empty string for number inputs to keep them "controlled" from mount
            part_height_mm: '',
            is_continuous_printing: false,
        }
    });

    // Load profiles for the multi-select
    useEffect(() => {
        fetchFilamentProfiles()
            .then(setProfiles)
            .catch(err => {
                console.error("Failed to load filament profiles:", err);
                setErrorMessage("Failed to load filament profiles. Please refresh.");
            });
    }, []);

    // Register custom form fields
    useEffect(() => {
        form.register('print_file_id');
        form.register('generate_variants_for_profile_ids');
    }, [form.register]);

    const onSubmit = async (data: ProductFormValues) => {
        setStatus('submitting');
        setErrorMessage('');

        try {
            // Strict DTO Construction for Backend
            // Ensure payload matches ProductCreate schema
            const payload = {
                name: data.name,
                sku: data.sku || undefined, // Send undefined if empty string to let backend auto-generate or handle it
                print_file_id: data.print_file_id,
                generate_variants_for_profile_ids: data.generate_variants_for_profile_ids || [],
                // Phase 6: Continuous Printing fields
                // Normalize empty string back to null for Backend
                part_height_mm: (typeof data.part_height_mm === 'number') ? data.part_height_mm : null,
                is_continuous_printing: data.is_continuous_printing || false,
            };

            // Debug Logging
            console.log("Submitting Payload:", payload);

            const response = await fetch('http://127.0.0.1:8000/api/products', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to create product');
            }

            setStatus('success');
            setTimeout(() => {
                router.push('/products');
            }, 1000); // Faster redirect

        } catch (error: any) {
            console.error("Submission Error:", error);
            setStatus('error');
            setErrorMessage(error.message || 'An unknown error occurred');
        }
    };

    if (status === 'success') {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-center animate-in zoom-in-95 duration-300">
                <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mb-4 shadow-lg shadow-green-500/30">
                    <CheckCircle2 className="text-white" size={32} />
                </div>
                <h3 className="text-2xl font-bold text-white tracking-tight">Product Created!</h3>
                <p className="text-slate-400 mt-2">Redirecting to catalog...</p>
            </div>
        );
    }

    // Debug: Log form errors to console
    console.log("Form State Errors:", form.formState.errors);

    return (
        <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
            {/* Header Info */}
            <div className="space-y-6 bg-slate-950/30 p-6 rounded-2xl border border-slate-800/50">
                <div className="space-y-2">
                    <label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest ml-1">Product Name</label>
                    <input
                        {...form.register('name')}
                        placeholder="e.g. Geometric Vase 2.0"
                        className={cn(
                            "w-full bg-slate-950 border rounded-xl px-4 py-3 text-white focus:outline-none transition-all",
                            form.formState.errors.name ? "border-red-500/50 focus:border-red-500" : "border-slate-800 focus:border-blue-500"
                        )}
                    />
                    {form.formState.errors.name && (
                        <p className="text-xs text-red-500 ml-1">{form.formState.errors.name.message}</p>
                    )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="space-y-2">
                        <label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest ml-1 text-nowrap">Internal SKU (Optional)</label>
                        <input
                            {...form.register('sku')}
                            placeholder="AUTO-GENERATE"
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:border-blue-500 focus:outline-none transition-all uppercase placeholder:normal-case mt-0.5"
                        />
                    </div>
                </div>

                <div className="space-y-2">
                    <label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest ml-1">Description</label>
                    <textarea
                        {...form.register('description')}
                        placeholder="Optional details for identification..."
                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white min-h-[100px] focus:border-blue-500 focus:outline-none transition-all"
                    />
                </div>
            </div>

            {/* Phase 6: Continuous Printing (Automation Safety) */}
            <div className="space-y-4">
                <div className="flex items-center gap-2 mb-2">
                    <div className="w-1 h-4 bg-amber-500 rounded-full" />
                    <label className="text-xs uppercase font-bold text-slate-300 tracking-widest">Continuous Printing (Automation)</label>
                </div>

                <div className="bg-slate-950/30 p-4 rounded-xl border border-slate-800/50 space-y-4">
                    {/* Part Height Input */}
                    <div className="space-y-2">
                        <label className="text-[10px] uppercase font-bold text-slate-500 tracking-widest ml-1">
                            Bauteilhöhe (mm)
                        </label>
                        <input
                            type="number"
                            step="0.1"
                            min="0"
                            {...form.register('part_height_mm', {
                                valueAsNumber: true,
                                setValueAs: (v) => v === "" ? null : parseFloat(v)
                            })}
                            placeholder="z.B. 75.0"
                            className={cn(
                                "w-full bg-slate-950 border rounded-xl px-4 py-3 text-white focus:outline-none transition-all",
                                form.formState.errors.part_height_mm ? "border-red-500/50 focus:border-red-500" : "border-slate-800 focus:border-amber-500"
                            )}
                        />
                        <p className="text-[10px] text-slate-500 ml-1">
                            Höhe des gedruckten Teils für automatische Auswerfer-Berechnung.
                        </p>
                    </div>

                    {/* Continuous Printing Toggle with Smart Interlock */}
                    <div className="flex items-center justify-between p-3 bg-slate-900 rounded-lg border border-slate-800">
                        <div className="space-y-1">
                            <label className="text-sm font-bold text-white cursor-pointer">
                                Continuous Printing (Auto-Sweep)
                            </label>
                            <p className={cn(
                                "text-[10px]",
                                (form.watch('part_height_mm') ?? 0) >= 50 ? "text-slate-500" : "text-amber-400"
                            )}>
                                {(form.watch('part_height_mm') ?? 0) >= 50
                                    ? "Automatisches Auswerfen nach Druckende aktivieren."
                                    : "⚠️ Erfordert Bauteilhöhe ≥ 50mm (Gantry Sweep Sicherheit)"
                                }
                            </p>
                        </div>
                        <button
                            type="button"
                            onClick={() => {
                                const current = form.watch('is_continuous_printing');
                                const height = form.watch('part_height_mm') ?? 0;
                                if (height >= 50 || current) {
                                    form.setValue('is_continuous_printing', !current, { shouldValidate: true });
                                }
                            }}
                            disabled={(form.watch('part_height_mm') ?? 0) < 50 && !form.watch('is_continuous_printing')}
                            className={cn(
                                "relative w-12 h-6 rounded-full transition-all duration-200",
                                form.watch('is_continuous_printing')
                                    ? "bg-amber-500 shadow-lg shadow-amber-500/30"
                                    : "bg-slate-700",
                                (form.watch('part_height_mm') ?? 0) < 50 && "opacity-50 cursor-not-allowed"
                            )}
                        >
                            <div className={cn(
                                "absolute top-1 w-4 h-4 bg-white rounded-full transition-all duration-200 shadow-md",
                                form.watch('is_continuous_printing') ? "left-7" : "left-1"
                            )} />
                        </button>
                    </div>

                    {form.formState.errors.is_continuous_printing && (
                        <div className="flex items-center gap-2 text-xs text-red-500 ml-1 animate-in slide-in-from-left-2 duration-200">
                            <AlertTriangle size={12} />
                            <span>{form.formState.errors.is_continuous_printing.message}</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Auto-Variants Section */}
            <div className="space-y-4">
                <div className="flex items-center gap-2 mb-2">
                    <div className="w-1 h-4 bg-blue-500 rounded-full" />
                    <label className="text-xs uppercase font-bold text-slate-300 tracking-widest">Auto-Generate Color Variants</label>
                </div>

                <ProfileMultiSelect
                    profiles={profiles}
                    selectedIds={form.watch('generate_variants_for_profile_ids')}
                    onChange={(ids) => form.setValue('generate_variants_for_profile_ids', ids)}
                />
                <p className="text-[10px] text-slate-500 italic ml-1">
                    Selected profiles will automatically generate child SKUs and mapping requirements.
                </p>
            </div>

            {/* Asset Section */}
            <div className="space-y-4">
                <div className="flex items-center gap-2 mb-2">
                    <div className="w-1 h-4 bg-indigo-500 rounded-full" />
                    <label className="text-xs uppercase font-bold text-slate-300 tracking-widest">Print Asset (.3mf)</label>
                </div>

                <FileUpload
                    onUploadSuccess={(id, name) => {
                        console.log("File Uploaded. Setting ID:", id);
                        form.setValue('print_file_id', id, { shouldValidate: true, shouldDirty: true });
                        setUploadedFileName(name);
                    }}
                    onReset={() => {
                        // @ts-ignore - manual reset of a number field
                        form.setValue('print_file_id', undefined, { shouldValidate: true });
                        setUploadedFileName('');
                    }}
                    existingFilename={uploadedFileName}
                />

                {form.formState.errors.print_file_id && (
                    <div className="flex items-center gap-2 text-xs text-red-500 ml-1 animate-in slide-in-from-left-2 duration-200">
                        <AlertTriangle size={12} />
                        <span>{form.formState.errors.print_file_id.message}</span>
                    </div>
                )}
            </div>

            {/* Error Message */}
            {status === 'error' && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-xl flex items-center gap-3 text-red-400 animate-in fade-in duration-300">
                    <AlertTriangle size={20} />
                    <span className="text-sm font-medium">{errorMessage}</span>
                </div>
            )}

            {/* Action Buttons */}
            <div className="pt-6 flex gap-4">
                <button
                    type="button"
                    onClick={() => router.push('/products')}
                    className="px-8 py-3 rounded-xl font-bold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
                >
                    Cancel
                </button>
                <button
                    type="submit"
                    disabled={status === 'submitting'}
                    className="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl py-3 font-bold shadow-lg shadow-blue-900/40 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                    {status === 'submitting' ? (
                        <>
                            <Loader2 className="animate-spin" size={20} />
                            <span>Processing...</span>
                        </>
                    ) : (
                        'Create Product Definition'
                    )}
                </button>
            </div>
        </form>
    );
}
