
'use client';

import { useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { Package, Plus, AlertTriangle, Loader2, FileText, Settings, Trash2 } from 'lucide-react';
import { ConfirmationModal } from '@/components/modals/ConfirmationModal';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

interface Product {
    id: number;
    name: string;
    description: string | null;
    sku: string;
    created_at: string;
    updated_at: string;
    file_path_3mf: string | null;
    required_filament_type: string | null;
    required_filament_color: string | null;
}

export default function ProductsPage() {
    const { data: products, error, isLoading, mutate } = useSWR<Product[]>('http://localhost:8000/api/products', fetcher);

    // Modal State
    const [deleteId, setDeleteId] = useState<number | null>(null);
    const [deleteName, setDeleteName] = useState<string>('');
    const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

    const promptDelete = (id: number, name: string) => {
        setDeleteId(id);
        setDeleteName(name);
        setIsDeleteModalOpen(true);
    };

    const handleConfirmDelete = async () => {
        if (!deleteId) return;

        try {
            const res = await fetch(`http://localhost:8000/api/products/${deleteId}`, {
                method: 'DELETE',
            });

            if (!res.ok) throw new Error('Failed to delete product');

            // Optimistic update
            mutate(products?.filter(p => p.id !== deleteId), false);
            mutate(); // Re-fetch

            setIsDeleteModalOpen(false);
        } catch (err) {
            alert('Error deleting product'); // Fallback alert for error is fine for now
            console.error(err);
        }
    };

    return (
        <div className="space-y-6 max-w-[1600px] mx-auto">
            <ConfirmationModal
                isOpen={isDeleteModalOpen}
                title="Delete Product?"
                message={`Are you sure you want to delete "${deleteName}"? This action cannot be undone and will prevent future orders for this SKU.`}
                confirmLabel="Delete Product"
                isDestructive={true}
                onConfirm={handleConfirmDelete}
                onCancel={() => setIsDeleteModalOpen(false)}
            />

            {/* Header */}
            <div className="flex justify-between items-center bg-slate-900/50 p-6 rounded-2xl border border-slate-800">
                <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-500/10 rounded-xl text-purple-500">
                        <Package size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Product Catalog</h1>
                        <p className="text-slate-400 text-sm">Manage SKU definitions and 3MF print files</p>
                    </div>
                </div>

                <Link
                    href="/products/new"
                    className="flex items-center gap-2 bg-purple-600 hover:bg-purple-500 text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-lg shadow-purple-900/20 active:scale-95"
                >
                    <Plus size={20} />
                    Add Product
                </Link>
            </div>

            {/* Error State */}
            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg flex items-center gap-2">
                    <AlertTriangle size={20} />
                    <span>Failed to load products. Is the backend running?</span>
                </div>
            )}

            {/* Loading */}
            {isLoading && (
                <div className="flex justify-center p-20">
                    <Loader2 size={40} className="text-slate-600 animate-spin" />
                </div>
            )}

            {/* Empty State */}
            {products && products.length === 0 && (
                <div className="text-center p-20 border border-dashed border-slate-800 rounded-2xl bg-slate-900/50">
                    <Package size={48} className="mx-auto text-slate-600 mb-4" />
                    <h3 className="text-lg font-medium text-slate-300">No Products Found</h3>
                    <p className="text-slate-500 mt-2">Get started by adding your first print file.</p>
                </div>
            )}

            {/* Product Table */}
            {products && products.length > 0 && (
                <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
                    <table className="w-full text-left">
                        <thead className="bg-slate-950 text-slate-400 text-xs uppercase font-bold tracking-wider">
                            <tr>
                                <th className="p-6 w-20">ID</th>
                                <th className="p-6">Product</th>
                                <th className="p-6">Requirements</th>
                                <th className="p-6">File</th>
                                <th className="p-6 text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-800">
                            {products.map((product) => (
                                <tr key={product.id} className="hover:bg-slate-800/40 transition-colors group">
                                    <td className="p-6 font-mono text-slate-500">#{product.id}</td>
                                    <td className="p-6">
                                        <div className="font-bold text-white text-lg">{product.name}</div>
                                        <div className="text-sm font-mono text-blue-400 mt-1">{product.sku}</div>
                                        {product.description && (
                                            <p className="text-xs text-slate-500 mt-1 max-w-sm truncate">{product.description}</p>
                                        )}
                                    </td>
                                    <td className="p-6">
                                        <div className="flex gap-2">
                                            <span className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-300 font-mono">
                                                {product.required_filament_type || 'PLA'}
                                            </span>
                                            {product.required_filament_color && (
                                                <span
                                                    className="px-2 py-1 rounded bg-slate-800 border border-slate-700 text-xs text-slate-300 font-mono flex items-center gap-2"
                                                >
                                                    <span
                                                        className="w-2.5 h-2.5 rounded-full border border-slate-600"
                                                        style={{ backgroundColor: product.required_filament_color }}
                                                    />
                                                    {product.required_filament_color}
                                                </span>
                                            )}
                                        </div>
                                    </td>
                                    <td className="p-6">
                                        {product.file_path_3mf ? (
                                            <div className="flex items-center gap-2 text-green-400 text-xs font-mono bg-green-500/10 px-3 py-1.5 rounded-full w-fit">
                                                <FileText size={12} />
                                                Possible
                                            </div>
                                        ) : (
                                            <span className="text-slate-600 text-xs italic">Missing File</span>
                                        )}
                                    </td>
                                    <td className="p-6 text-right">
                                        <div className="flex justify-end gap-2 transition-opacity">
                                            <Link href={`/products/${product.id}`} className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition-all">
                                                <Settings size={18} />
                                            </Link>
                                            <button
                                                onClick={() => promptDelete(product.id, product.name)}
                                                className="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                                            >
                                                <Trash2 size={18} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
}
