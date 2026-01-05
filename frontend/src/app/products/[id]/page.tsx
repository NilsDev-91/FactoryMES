'use client';

import React, { useState, useEffect, useMemo } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Package, Upload, FileText, CheckCircle2, AlertTriangle, ArrowLeft, Loader2, Save } from 'lucide-react';
import Link from 'next/link';
import useSWR from 'swr';
import { ProfileMultiSelect } from '@/components/products/profile-multi-select';
import { fetchFilamentProfiles, fetchAvailableMaterials, createFilamentProfile, type MaterialAvailability } from '@/lib/api/fms';
import { FilamentProfile } from '@/types/api/filament';
import { cn } from '@/lib/utils';

const fetcher = async (url: string) => {
    const res = await fetch(url);
    if (!res.ok) {
        const error = new Error('An error occurred while fetching the data.');
        // @ts-ignore
        error.info = await res.json();
        // @ts-ignore
        error.status = res.status;
        throw error;
    }
    return res.json();
};

export default function EditProductPage() {
    const router = useRouter();
    const params = useParams();
    const id = params?.id;

    // Fetch existing data
    const { data: product, error, isLoading } = useSWR(id ? `http://127.0.0.1:8000/api/products/${id}` : null, fetcher);

    // Form State
    const [name, setName] = useState('');
    const [sku, setSku] = useState('');
    const [description, setDescription] = useState('');
    const [printFileId, setPrintFileId] = useState<number | null>(null);
    const [partHeightMm, setPartHeightMm] = useState<number | null>(null);
    const [isContinuousPrinting, setIsContinuousPrinting] = useState(false);
    const [selectedProfileIds, setSelectedProfileIds] = useState<string[]>([]);
    const [formReady, setFormReady] = useState(false);

    // FMS State
    const [profiles, setProfiles] = useState<FilamentProfile[]>([]);
    const [availableMaterials, setAvailableMaterials] = useState<MaterialAvailability[]>([]);

    // File State (Optional for Edit)
    const [file, setFile] = useState<File | null>(null);
    const [dragActive, setDragActive] = useState(false);

    // Submission State
    const [status, setStatus] = useState<'idle' | 'uploading' | 'saving' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    // Load profiles and available materials
    useEffect(() => {
        Promise.all([
            fetchFilamentProfiles(),
            fetchAvailableMaterials()
        ]).then(([loadedProfiles, loadedMaterials]) => {
            setProfiles(loadedProfiles);
            setAvailableMaterials(loadedMaterials);
        }).catch(err => {
            console.error("Failed to load FMS data:", err);
            setErrorMessage("Failed to load filament data. Please refresh.");
        });
    }, []);

    // Pre-fill form when data loads
    useEffect(() => {
        if (product && !formReady) {
            setName(product.name || '');
            setSku(product.sku || '');
            setDescription(product.description || '');
            setPrintFileId(product.print_file_id || null);
            setPartHeightMm(product.part_height_mm || null);
            setIsContinuousPrinting(product.is_continuous_printing || false);

            // Extract existing profiles from variants
            const existingIds: string[] = [];
            if (product.variants) {
                product.variants.forEach((v: any) => {
                    // Assuming each variant has one requirement -> profile
                    if (v.requirements && v.requirements.length > 0) {
                        existingIds.push(v.requirements[0].filament_profile_id);
                    }
                });
            }
            setSelectedProfileIds(existingIds);

            setFormReady(true);
        }
    }, [product, formReady]);

    // Computed: Merge Saved Profiles with Live AMS Materials
    const selectableProfiles = useMemo(() => {
        const virtualProfiles: FilamentProfile[] = [];

        availableMaterials.forEach(amsMat => {
            // Check if this material/color already exists in saved profiles
            const exists = profiles.some(p =>
                p.material.toLowerCase() === amsMat.material.toLowerCase() &&
                p.color_hex.toLowerCase() === amsMat.hex_code.toLowerCase()
            );

            if (!exists) {
                // Create a Virtual Profile
                virtualProfiles.push({
                    id: `temp:${amsMat.hex_code}:${amsMat.material}`,
                    brand: "Generic",
                    material: amsMat.material,
                    color_hex: amsMat.hex_code.startsWith('#') ? amsMat.hex_code : `#${amsMat.hex_code}`,
                    density: 1.24,
                    spool_weight: 1000,
                });
            }
        });

        // Filter duplicates within virtuals
        const uniqueVirtuals = virtualProfiles.filter((v, i, self) =>
            i === self.findIndex(t => t.id === v.id)
        );

        return [...uniqueVirtuals, ...profiles];
    }, [profiles, availableMaterials]);

    const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setFile(e.target.files[0]);
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
            setFile(e.dataTransfer.files[0]);
        }
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        e.stopPropagation();

        try {
            let activePrintFileId = printFileId;

            // Step 1: Upload File (If new file selected)
            if (file) {
                setStatus('uploading');
                const formData = new FormData();
                formData.append('file', file);

                const uploadRes = await fetch('http://127.0.0.1:8000/api/products/upload', {
                    method: 'POST',
                    body: formData,
                });

                if (!uploadRes.ok) throw new Error('File upload failed');
                const uploadData = await uploadRes.json();
                activePrintFileId = uploadData.id;
            }

            // Step 2: Auto-Create Virtual Profiles
            const finalProfileIds: string[] = [];
            for (const id of selectedProfileIds) {
                if (id.startsWith('temp:')) {
                    const parts = id.split(':'); // temp, hex, material
                    try {
                        const newProfile = await createFilamentProfile({
                            brand: "Generic",
                            material: parts[2],
                            color_hex: parts[1],
                            density: 1.24,
                            spool_weight: 1000
                        });
                        finalProfileIds.push(newProfile.id);
                    } catch (e) {
                        console.error(`Failed to auto-create profile for ${id}`, e);
                    }
                } else {
                    finalProfileIds.push(id);
                }
            }

            // Step 3: Update Product
            setStatus('saving');
            const productPayload = {
                name,
                sku,
                description,
                print_file_id: activePrintFileId,
                part_height_mm: partHeightMm,
                is_continuous_printing: isContinuousPrinting,
                generate_variants_for_profile_ids: finalProfileIds
            };

            const updateRes = await fetch(`http://127.0.0.1:8000/api/products/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(productPayload),
            });

            if (!updateRes.ok) {
                const err = await updateRes.json();
                throw new Error(err.detail || 'Failed to update product');
            }

            setStatus('success');

            // Redirect after delay
            setTimeout(() => {
                router.push('/products');
            }, 1000);

        } catch (error: any) {
            setStatus('error');
            setErrorMessage(error.message || 'An unknown error occurred');
        }
    };

    if (isLoading) return <div className="flex justify-center p-20"><Loader2 className="animate-spin text-slate-500" /></div>;
    if (error) return <div className="text-red-400 p-10 text-center">Failed to load product.</div>;

    return (
        <div className="max-w-2xl mx-auto space-y-6">
            <Link href="/products" className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm font-medium mb-4">
                <ArrowLeft size={16} /> Back to Catalog
            </Link>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-2xl">
                <div className="flex items-center gap-4 mb-8">
                    <div className="p-4 bg-purple-500/10 rounded-2xl text-purple-500">
                        <Package size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Edit Product</h1>
                        <p className="text-slate-400 text-sm">Update SKU and Filament Configurations</p>
                    </div>
                </div>

                {status === 'success' ? (
                    <div className="flex flex-col items-center justify-center p-12 text-center animate-in zoom-in-95 duration-300">
                        <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mb-4 shadow-lg shadow-green-500/30">
                            <CheckCircle2 className="text-white" size={32} />
                        </div>
                        <h3 className="text-2xl font-bold text-white">Product Updated!</h3>
                        <p className="text-slate-400 mt-2">Redirecting to catalog...</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-6">
                        {/* SKU & Name */}
                        <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-xs uppercase font-bold text-slate-500 tracking-wider">SKU</label>
                                <input
                                    required
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white font-mono focus:border-purple-500 focus:outline-none transition-colors"
                                    value={sku}
                                    onChange={(e) => setSku(e.target.value.toUpperCase())}
                                />
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs uppercase font-bold text-slate-500 tracking-wider">Product Name</label>
                                <input
                                    required
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:border-purple-500 focus:outline-none transition-colors"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                />
                            </div>
                        </div>

                        {/* Description */}
                        <div className="space-y-2">
                            <label className="text-xs uppercase font-bold text-slate-500 tracking-wider">Description</label>
                            <textarea
                                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white min-h-[80px] focus:border-purple-500 focus:outline-none transition-colors"
                                value={description}
                                onChange={(e) => setDescription(e.target.value)}
                            />
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
                                        value={partHeightMm ?? ''}
                                        onChange={(e) => setPartHeightMm(e.target.value === '' ? null : parseFloat(e.target.value))}
                                        placeholder="z.B. 75.0"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-amber-500 transition-all"
                                    />
                                    <p className="text-[10px] text-slate-500 ml-1">
                                        Höhe des gedruckten Teils für automatische Auswerfer-Berechnung.
                                        Physical Limit: Parts &lt; 38mm cannot be auto-ejected by the A1 Gantry.
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
                                            (partHeightMm ?? 0) >= 38 ? "text-slate-500" : "text-amber-400"
                                        )}>
                                            {(partHeightMm ?? 0) >= 38
                                                ? "Automatisches Auswerfen nach Druckende aktivieren."
                                                : "⚠️ Erfordert Bauteilhöhe ≥ 38mm (Gantry Sweep Sicherheit)"
                                            }
                                        </p>
                                    </div>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            if ((partHeightMm ?? 0) >= 38 || isContinuousPrinting) {
                                                setIsContinuousPrinting(!isContinuousPrinting);
                                            }
                                        }}
                                        disabled={(partHeightMm ?? 0) < 38 && !isContinuousPrinting}
                                        className={cn(
                                            "relative w-12 h-6 rounded-full transition-all duration-200",
                                            isContinuousPrinting
                                                ? "bg-amber-500 shadow-lg shadow-amber-500/30"
                                                : "bg-slate-700",
                                            (partHeightMm ?? 0) < 38 && "opacity-50 cursor-not-allowed"
                                        )}
                                    >
                                        <div className={cn(
                                            "absolute top-1 w-4 h-4 bg-white rounded-full transition-all duration-200 shadow-md",
                                            isContinuousPrinting ? "left-7" : "left-1"
                                        )} />
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Filament Selection */}
                        <div className="space-y-2">
                            <ProfileMultiSelect
                                profiles={selectableProfiles}
                                selectedIds={selectedProfileIds}
                                onChange={setSelectedProfileIds}
                            />
                            <p className="text-xs text-slate-500 mt-1">
                                Check/Uncheck to Add/Remove Variants. "Live" items will be auto-saved.
                            </p>
                        </div>

                        {/* Print File */}
                        <div className="space-y-2">
                            <label className="text-xs uppercase font-bold text-slate-500 tracking-wider flex justify-between">
                                <span>Print File (.3mf)</span>
                                {product?.print_file_id && <span className="text-green-400 normal-case font-normal text-xs">Current file exists</span>}
                            </label>
                            <div
                                onDragEnter={handleDrag}
                                onDragLeave={handleDrag}
                                onDragOver={handleDrag}
                                onDrop={handleDrop}
                                className={`border-2 border-dashed rounded-xl p-8 transition-all duration-200 flex flex-col items-center justify-center text-center cursor-pointer relative group
                                    ${dragActive ? 'border-purple-500 bg-purple-500/10' : 'border-slate-800 bg-slate-950/50 hover:border-slate-700 hover:bg-slate-900'}
                                    ${file ? 'border-green-500/50 bg-green-500/5' : ''}
                                `}
                            >
                                <input
                                    type="file"
                                    accept=".3mf,.gcode"
                                    className="absolute inset-0 opacity-0 cursor-pointer"
                                    onChange={handleFileSelect}
                                />

                                {file ? (
                                    <>
                                        <div className="w-12 h-12 bg-green-500 rounded-full flex items-center justify-center mb-3 shadow-lg shadow-green-500/20">
                                            <FileText className="text-white" size={24} />
                                        </div>
                                        <p className="text-green-400 font-bold text-lg">{file.name}</p>
                                        <p className="text-slate-500 text-sm mt-1">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                        <p className="text-xs text-slate-600 mt-4 uppercase font-bold tracking-widest">Click to Change</p>
                                    </>
                                ) : (
                                    <>
                                        <div className="w-12 h-12 bg-slate-800 rounded-full flex items-center justify-center mb-3 group-hover:scale-110 transition-transform">
                                            <Upload className="text-slate-400 group-hover:text-white" size={24} />
                                        </div>
                                        <p className="text-slate-300 font-medium">Drag & Drop new file to replace</p>
                                        <p className="text-slate-500 text-sm mt-1">Leaves existing file if empty</p>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Error Message */}
                        {status === 'error' && (
                            <div className="p-4 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-3 text-red-400">
                                <AlertTriangle size={20} />
                                <span className="text-sm font-medium">{errorMessage}</span>
                            </div>
                        )}

                        {/* Submit Button */}
                        <div className="pt-4 flex gap-4">
                            <Link href="/products" className="px-6 py-3 rounded-xl font-bold text-slate-400 hover:text-white hover:bg-slate-800 transition-colors">
                                Cancel
                            </Link>
                            <button
                                type="submit"
                                disabled={status === 'uploading' || status === 'saving'}
                                className="flex-1 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white rounded-xl py-3 font-bold shadow-lg shadow-purple-900/20 active:scale-95 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                            >
                                {status === 'uploading' && <Loader2 className="animate-spin" />}
                                {status === 'saving' && <Loader2 className="animate-spin" />}
                                {status === 'idle' && <> <Save size={20} /> Update Product </>}
                                {status === 'uploading' && 'Uploading File...'}
                                {status === 'saving' && 'Saving Changes...'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
}

