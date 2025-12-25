import React, { useState } from 'react';
import useSWR, { mutate } from 'swr';
import { fetchProducts, createProduct, uploadProductFile, deleteProduct } from '../../api';
import { Package, Plus, Upload, Trash2, FileText, X } from 'lucide-react';

const ProductView = () => {
    const { data: products, error } = useSWR('products', fetchProducts);
    const [isModalOpen, setIsModalOpen] = useState(false);

    const handleDelete = async (id) => {
        if (confirm('Are you sure you want to delete this product?')) {
            try {
                await deleteProduct(id);
                mutate('products'); // Refresh list
            } catch (e) {
                alert(e.message);
            }
        }
    };

    return (
        <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
            {/* Header */}
            <div className="flex justify-between items-center bg-slate-800/50 p-4 rounded-xl border border-slate-700/50 backdrop-blur-sm">
                <div>
                    <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
                        <Package className="text-purple-400" /> Product Management
                    </h2>
                    <p className="text-sm text-slate-400">Manage your catalog and 3MF files</p>
                </div>

                <button
                    onClick={() => setIsModalOpen(true)}
                    className="flex items-center gap-2 text-sm font-medium bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg transition-all shadow-lg shadow-purple-900/20"
                >
                    <Plus size={16} /> Add Product
                </button>
            </div>

            {/* Product Table */}
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden backdrop-blur-sm">
                <table className="w-full text-left border-collapse">
                    <thead>
                        <tr className="bg-slate-800 border-b border-slate-700 text-xs uppercase text-slate-400">
                            <th className="p-4 font-semibold w-16">#</th>
                            <th className="p-4 font-semibold">Product</th>
                            <th className="p-4 font-semibold">SKU</th>
                            <th className="p-4 font-semibold">3MF Status</th>
                            <th className="p-4 font-semibold text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                        {!products || products.length === 0 ? (
                            <tr><td colSpan="5" className="p-8 text-center text-slate-500">No products found. Add one to get started.</td></tr>
                        ) : (
                            products.map((p) => (
                                <tr key={p.id} className="hover:bg-slate-700/30 transition-colors group">
                                    <td className="p-4 text-slate-500">{p.id}</td>
                                    <td className="p-4">
                                        <div className="font-medium text-white">{p.name}</div>
                                        <div className="text-xs text-slate-500 truncate max-w-[200px]">{p.description}</div>
                                    </td>
                                    <td className="p-4 font-mono text-sm text-blue-300">{p.sku}</td>
                                    <td className="p-4">
                                        <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium bg-green-500/10 text-green-400 border border-green-500/20">
                                            <FileText size={12} /> Present
                                        </span>
                                    </td>
                                    <td className="p-4 text-right">
                                        <button
                                            onClick={() => handleDelete(p.id)}
                                            className="p-2 text-slate-500 hover:text-red-400 transition-colors"
                                            title="Delete"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Add Product Modal */}
            {isModalOpen && <AddProductModal onClose={() => setIsModalOpen(false)} />}
        </div>
    );
};

const AddProductModal = ({ onClose }) => {
    const [name, setName] = useState('');
    const [sku, setSku] = useState('');
    const [desc, setDesc] = useState('');
    const [file, setFile] = useState(null);
    const [isUploading, setIsUploading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!file) {
            alert("Please upload a .3mf file");
            return;
        }

        setIsUploading(true);
        try {
            // 1. Upload File
            const uploadRes = await uploadProductFile(file);
            const filePath = uploadRes.file_path;

            // 2. Create Product
            await createProduct({
                name,
                sku,
                description: desc,
                file_path_3mf: filePath
            });

            mutate('products'); // Refresh list
            onClose();
        } catch (error) {
            alert(error.message);
        } finally {
            setIsUploading(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl p-6">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold text-white">Add New Product</h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={20} /></button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">Product Name</label>
                        <input
                            required
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                            value={name} onChange={e => setName(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">SKU (Unique)</label>
                        <input
                            required
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-purple-500"
                            value={sku} onChange={e => setSku(e.target.value)}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">Description</label>
                        <textarea
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500 min-h-[80px]"
                            value={desc} onChange={e => setDesc(e.target.value)}
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">3MF File</label>
                        <div className="border-2 border-dashed border-slate-700 rounded-lg p-6 flex flex-col items-center justify-center bg-slate-900/50 hover:bg-slate-900 hover:border-purple-500/50 transition-all cursor-pointer relative">
                            <input
                                type="file"
                                accept=".3mf"
                                required
                                className="absolute inset-0 opacity-0 cursor-pointer"
                                onChange={e => setFile(e.target.files[0])}
                            />
                            {file ? (
                                <div className="text-center">
                                    <FileText size={24} className="mx-auto text-purple-400 mb-2" />
                                    <p className="text-sm text-white font-medium">{file.name}</p>
                                    <p className="text-xs text-slate-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                                </div>
                            ) : (
                                <div className="text-center">
                                    <Upload size={24} className="mx-auto text-slate-500 mb-2" />
                                    <p className="text-sm text-slate-300">Drag & Drop or Click to Upload</p>
                                    <p className="text-xs text-slate-500">Supports .3mf only</p>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="pt-4 flex gap-3">
                        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-200 font-medium transition-colors">Cancel</button>
                        <button
                            type="submit"
                            disabled={isUploading}
                            className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                        >
                            {isUploading && <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />}
                            {isUploading ? 'Uploading...' : 'Create Product'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ProductView;
