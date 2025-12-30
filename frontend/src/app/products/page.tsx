
'use client';

import { useState } from 'react';
import useSWR from 'swr';
import Link from 'next/link';
import { Package, Plus, AlertTriangle, Loader2 } from 'lucide-react';
import { ConfirmationModal } from '@/components/modals/ConfirmationModal';
import { ProductCatalogItem } from '@/types/api/catalog';
import { DataTable } from '@/components/ui/DataTable';
import { getColumns } from './columns';

const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function ProductsPage() {
    const { data: products, error, isLoading, mutate } = useSWR<ProductCatalogItem[]>('http://127.0.0.1:8000/api/products', fetcher);

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
            const res = await fetch(`http://127.0.0.1:8000/api/products/${deleteId}`, {
                method: 'DELETE',
            });

            if (!res.ok) throw new Error('Failed to delete product');

            // Optimistic update
            mutate(products?.filter(p => p.id !== deleteId), false);
            mutate(); // Re-fetch

            setIsDeleteModalOpen(false);
        } catch (err) {
            alert('Error deleting product');
            console.error(err);
        }
    };

    const handleEdit = (id: number) => {
        window.location.href = `/products/${id}`;
    };

    const columns = getColumns(handleEdit, promptDelete);

    return (
        <div className="space-y-6 max-w-[1600px] mx-auto pb-20">
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
                    <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400 border border-indigo-500/20">
                        <Package size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Product Catalog</h1>
                        <p className="text-slate-400 text-sm">Manage hierarchical SKUs and print requirements</p>
                    </div>
                </div>

                <Link
                    href="/products/new"
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-5 py-2.5 rounded-xl font-medium transition-all shadow-lg shadow-indigo-900/20 active:scale-95"
                >
                    <Plus size={20} />
                    Add Product
                </Link>
            </div>

            {/* Error State */}
            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg flex items-center gap-2">
                    <AlertTriangle size={20} />
                    <span>Failed to load products. Ensure the backend is running correctly.</span>
                </div>
            )}

            {/* Loading */}
            {isLoading && (
                <div className="flex justify-center p-20">
                    <Loader2 size={40} className="text-indigo-500 animate-spin" />
                </div>
            )}

            {/* Content */}
            {products && (
                products.length > 0 ? (
                    <DataTable columns={columns} data={products} />
                ) : (
                    <div className="text-center p-20 border border-dashed border-slate-800 rounded-2xl bg-slate-900/50">
                        <Package size={48} className="mx-auto text-slate-700 mb-4" />
                        <h3 className="text-lg font-medium text-slate-300">Catalog is Empty</h3>
                        <p className="text-slate-500 mt-2">Create your first product master to see it here.</p>
                    </div>
                )
            )}
        </div>
    );
}
