'use client';

import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
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

/**
 * Form Schema for Product Creation
 * Updated for Master-Variant architecture: Link to PrintFile ID and Procedural Variants.
 */
const productFormSchema = z.object({
    name: z.string().min(3, "Product name must be at least 3 characters"),
    sku: z.string().optional(),
    description: z.string().optional(),
    print_file_id: z.number({ required_error: "Print file is required" }),
    generate_variants_for_profile_ids: z.array(z.string()).optional().default([]),
});

type ProductFormValues = z.infer<typeof productFormSchema>;

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
            // Ensure payload matches: { name, sku, print_file_id, generate_variants_for_profile_ids }
            const payload = {
                name: data.name,
                sku: data.sku || undefined, // Send undefined if empty string to let backend auto-generate or handle it
                print_file_id: data.print_file_id,
                generate_variants_for_profile_ids: data.generate_variants_for_profile_ids || []
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
