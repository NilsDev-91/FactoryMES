'use client';

import React, { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { Package, Upload, FileText, CheckCircle2, AlertTriangle, ArrowLeft, Loader2, Save } from 'lucide-react';
import Link from 'next/link';
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

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
    const [material, setMaterial] = useState('PLA');
    const [colorHex, setColorHex] = useState('#ffffff');
    const [formReady, setFormReady] = useState(false);

    // File State (Optional for Edit)
    const [file, setFile] = useState<File | null>(null);
    const [dragActive, setDragActive] = useState(false);

    // Submission State
    const [status, setStatus] = useState<'idle' | 'uploading' | 'saving' | 'success' | 'error'>('idle');
    const [errorMessage, setErrorMessage] = useState('');

    // Pre-fill form when data loads
    useEffect(() => {
        if (product && !formReady) {
            setName(product.name);
            setSku(product.sku);
            setDescription(product.description || '');
            setMaterial(product.required_filament_type || 'PLA');
            setColorHex(product.required_filament_color || '#ffffff');
            setFormReady(true);
        }
    }, [product, formReady]);

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

        try {
            let filePath = product.file_path_3mf;

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
                filePath = uploadData.file_path;
            }

            // Step 2: Update Product
            setStatus('saving');
            const productPayload = {
                name,
                sku, // SKU might be readonly in some systems, but allowing edit for now
                description,
                required_filament_type: material,
                required_filament_color: colorHex,
                file_path_3mf: filePath
            };

            const updateRes = await fetch(`http://127.0.0.1:8000/api/products/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(productPayload),
            });

            if (!updateRes.ok) throw new Error('Failed to update product');

            setStatus('success');

            // Redirect after delay
            setTimeout(() => {
                router.push('/products');
            }, 1500);

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
                        <p className="text-slate-400 text-sm">Update SKU details and print files</p>
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

                        {/* Material Requirements */}
                        <div className="grid grid-cols-2 gap-6">
                            <div className="space-y-2">
                                <label className="text-xs uppercase font-bold text-slate-500 tracking-wider">Material</label>
                                <select
                                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:border-purple-500 focus:outline-none transition-colors appearance-none"
                                    value={material}
                                    onChange={(e) => setMaterial(e.target.value)}
                                >
                                    <option value="PLA">PLA</option>
                                    <option value="PETG">PETG</option>
                                    <option value="ABS">ABS</option>
                                    <option value="ASA">ASA</option>
                                    <option value="TPU">TPU</option>
                                </select>
                            </div>
                            <div className="space-y-2">
                                <label className="text-xs uppercase font-bold text-slate-500 tracking-wider">Color</label>
                                <div className="flex gap-3">
                                    <div className="relative w-12 h-[46px] rounded-lg overflow-hidden border border-slate-800 shrink-0">
                                        <input
                                            type="color"
                                            className="absolute -top-2 -left-2 w-16 h-16 cursor-pointer"
                                            value={colorHex}
                                            onChange={(e) => setColorHex(e.target.value)}
                                        />
                                    </div>
                                    <input
                                        type="text"
                                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white font-mono focus:border-purple-500 focus:outline-none transition-colors uppercase"
                                        value={colorHex}
                                        onChange={(e) => setColorHex(e.target.value)}
                                        maxLength={7}
                                    />
                                </div>
                            </div>
                        </div>

                        {/* File Upload (Optional) */}
                        <div className="space-y-2">
                            <label className="text-xs uppercase font-bold text-slate-500 tracking-wider flex justify-between">
                                <span>Print File (.3mf)</span>
                                {product?.file_path_3mf && <span className="text-green-400 normal-case font-normal text-xs">Current file exists</span>}
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
