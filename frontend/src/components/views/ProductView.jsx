import React, { useState, useEffect } from 'react';
import useSWR, { mutate } from 'swr';
import { fetchProducts, createProduct, uploadProductFile, deleteProduct, updateProduct } from '../../api';
import { Package, Plus, Upload, Trash2, FileText, X, Settings } from 'lucide-react';

const ProductView = () => {
    const { data: products, error } = useSWR('products', fetchProducts);
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [editingProduct, setEditingProduct] = useState(null);

    const handleDelete = async (id) => {
        if (confirm('Are you sure you want to delete this product?')) {
            try {
                // Optimistic update: Filter out the deleted item immediately
                mutate('products', products.filter(p => p.id !== id), false);
                await deleteProduct(id);
                mutate('products'); // Re-validate to be sure
            } catch (e) {
                alert(e.message);
                mutate('products'); // Revert on error
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
                            <th className="p-4 font-semibold">Requirements</th>
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
                                        <div className="flex flex-col gap-1">
                                            {p.file_path_3mf && (
                                                <span className="inline-flex items-center gap-1 text-[10px] text-green-400">
                                                    <FileText size={10} /> 3MF Ready
                                                </span>
                                            )}
                                            <span className="text-[10px] text-slate-400">
                                                {p.required_filament_type || 'PLA'}
                                                {p.required_filament_color && <span className="ml-1 px-1 rounded bg-slate-700 border border-slate-600" style={{ color: p.required_filament_color }}>Color</span>}
                                            </span>
                                        </div>
                                    </td>
                                    <td className="p-4 text-right">
                                        <div className="flex justify-end gap-2">
                                            <button
                                                onClick={() => setEditingProduct(p)}
                                                className="p-2 text-slate-500 hover:text-blue-400 transition-colors bg-slate-800/50 hover:bg-slate-700 rounded-lg border border-transparent hover:border-blue-500/30"
                                                title="Edit Settings"
                                            >
                                                <Settings size={16} />
                                            </button>
                                            <button
                                                onClick={() => handleDelete(p.id)}
                                                className="p-2 text-slate-500 hover:text-red-400 transition-colors bg-slate-800/50 hover:bg-slate-700 rounded-lg border border-transparent hover:border-red-500/30"
                                                title="Delete"
                                            >
                                                <Trash2 size={16} />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Add Product Modal */}
            {isModalOpen && <AddProductModal onClose={() => setIsModalOpen(false)} />}

            {/* Edit Product Modal */}
            {editingProduct && (
                <EditProductModal
                    product={editingProduct}
                    onClose={() => setEditingProduct(null)}
                />
            )}
        </div>
    );
};

const EditProductModal = ({ product, onClose }) => {
    const [formData, setFormData] = useState({
        name: '',
        sku: '',
        description: '',
        required_filament_type: 'PLA',
        required_filament_color: ''
    });
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (product) {
            setFormData({
                name: product.name || '',
                sku: product.sku || '',
                description: product.description || '',
                required_filament_type: product.required_filament_type || 'PLA',
                required_filament_color: product.required_filament_color || ''
            });
        }
    }, [product]);

    const handleChange = (e) => {
        setFormData(prev => ({ ...prev, [e.target.name]: e.target.value }));
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        try {
            await updateProduct(product.id, formData);
            mutate('products'); // Refresh list
            onClose();
        } catch (error) {
            alert(error.message);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
            <div className="bg-slate-800 border border-slate-700 rounded-2xl w-full max-w-md shadow-2xl p-6">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Settings size={20} className="text-blue-400" /> Edit Product
                    </h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={20} /></button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">Product Name</label>
                        <input
                            name="name"
                            required
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                            value={formData.name} onChange={handleChange}
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">SKU</label>
                        <input
                            name="sku"
                            required
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-blue-500"
                            value={formData.sku} onChange={handleChange}
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-xs font-medium text-slate-400 uppercase mb-1">Material Type</label>
                            <select
                                name="required_filament_type"
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                                value={formData.required_filament_type} onChange={handleChange}
                            >
                                <option value="PLA">PLA</option>
                                <option value="PETG">PETG</option>
                                <option value="ABS">ABS</option>
                                <option value="ASA">ASA</option>
                                <option value="TPU">TPU</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-xs font-medium text-slate-400 uppercase mb-1">Color (Hex/Name)</label>
                            <input
                                name="required_filament_color"
                                className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                                value={formData.required_filament_color} onChange={handleChange}
                                placeholder="#FF0000"
                            />
                        </div>
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">Description</label>
                        <textarea
                            name="description"
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500 min-h-[80px]"
                            value={formData.description} onChange={handleChange}
                        />
                    </div>

                    <div className="pt-4 flex gap-3">
                        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-200 font-medium transition-colors">Cancel</button>
                        <button
                            type="submit"
                            disabled={isSubmitting}
                            className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white font-medium transition-colors disabled:opacity-50 flex items-center justify-center gap-2 shadow-lg shadow-blue-900/20"
                        >
                            {isSubmitting ? 'Saving...' : 'Save Changes'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

const AddProductModal = ({ onClose }) => {
    const [name, setName] = useState('');
    const [sku, setSku] = useState('');
    const [desc, setDesc] = useState('');
    const [uploadedPath, setUploadedPath] = useState(null);
    const [uploadStatus, setUploadStatus] = useState('idle'); // idle, uploading, success, error
    const [uploadError, setUploadError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [dragActive, setDragActive] = useState(false);

    const handleFileSelect = async (file) => {
        if (!file) return;

        // Validation
        const ext = file.name.split('.').pop().toLowerCase();
        if (ext !== '3mf' && ext !== 'gcode') {
            setUploadStatus('error');
            setUploadError('Only .3mf and .gcode files are allowed');
            return;
        }

        setUploadStatus('uploading');
        setUploadError('');

        try {
            // Immediate Upload
            const uploadRes = await uploadProductFile(file);
            setUploadedPath(uploadRes.file_path);
            setUploadStatus('success');
        } catch (error) {
            setUploadStatus('error');
            setUploadError(error.message || 'Upload failed');
        }
    };

    const handleDrag = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (e.type === "dragenter" || e.type === "dragover") {
            setDragActive(true);
        } else if (e.type === "dragleave") {
            setDragActive(false);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        e.stopPropagation();
        setDragActive(false);
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            handleFileSelect(e.dataTransfer.files[0]);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!uploadedPath) {
            alert("Please upload a file first");
            return;
        }

        setIsSubmitting(true);
        try {
            await createProduct({
                name,
                sku,
                description: desc,
                file_path_3mf: uploadedPath
            });
            mutate('products');
            onClose();
        } catch (error) {
            alert(error.message);
        } finally {
            setIsSubmitting(false);
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
                            placeholder="e.g. Benchy Boat"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">SKU (Unique)</label>
                        <input
                            required
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white font-mono focus:outline-none focus:border-purple-500"
                            value={sku} onChange={e => setSku(e.target.value)}
                            placeholder="e.g. BENCHY_V1"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">Description</label>
                        <textarea
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500 min-h-[80px]"
                            value={desc} onChange={e => setDesc(e.target.value)}
                            placeholder="Optional details..."
                        />
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-slate-400 uppercase mb-1">3MF File Upload</label>
                        <div
                            className={`border-2 border-dashed rounded-lg p-6 flex flex-col items-center justify-center transition-all relative
                                ${dragActive ? 'border-purple-500 bg-purple-500/10' : 'border-slate-700 bg-slate-900/50'}
                                ${uploadStatus === 'error' ? 'border-red-500/50 bg-red-500/10' : ''}
                                ${uploadStatus === 'success' ? 'border-green-500/50 bg-green-500/10' : ''}
                            `}
                            onDragEnter={handleDrag}
                            onDragLeave={handleDrag}
                            onDragOver={handleDrag}
                            onDrop={handleDrop}
                        >
                            <input
                                type="file"
                                accept=".3mf,.gcode"
                                className="absolute inset-0 opacity-0 cursor-pointer disabled:cursor-not-allowed"
                                onChange={e => handleFileSelect(e.target.files[0])}
                                disabled={uploadStatus === 'success' || uploadStatus === 'uploading'}
                            />

                            {uploadStatus === 'idle' && (
                                <div className="text-center pointer-events-none">
                                    <Upload size={24} className="mx-auto text-slate-500 mb-2" />
                                    <p className="text-sm text-slate-300 font-medium">Drag & Drop or Click</p>
                                    <p className="text-xs text-slate-500 mt-1">Supports .3mf, .gcode</p>
                                </div>
                            )}

                            {uploadStatus === 'uploading' && (
                                <div className="text-center pointer-events-none">
                                    <div className="w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
                                    <p className="text-sm text-purple-300 animate-pulse">Uploading to Factory...</p>
                                </div>
                            )}

                            {uploadStatus === 'success' && (
                                <div className="text-center pointer-events-none">
                                    <div className="w-8 h-8 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-2 shadow-lg shadow-green-500/20">
                                        <FileText className="text-white" size={16} />
                                    </div>
                                    <p className="text-sm text-green-400 font-bold">File Uploaded!</p>
                                    <p className="text-xs text-slate-500 mt-1 break-all max-w-[200px]">{uploadedPath?.split('/').pop()}</p>
                                </div>
                            )}

                            {uploadStatus === 'error' && (
                                <div className="text-center pointer-events-none">
                                    <div className="w-8 h-8 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-2">
                                        <X className="text-red-400" size={16} />
                                    </div>
                                    <p className="text-sm text-red-400 font-medium">Upload Failed</p>
                                    <p className="text-xs text-red-300/70 mt-1">{uploadError}</p>
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="pt-4 flex gap-3">
                        <button type="button" onClick={onClose} className="flex-1 px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-slate-200 font-medium transition-colors">Cancel</button>
                        <button
                            type="submit"
                            disabled={isSubmitting || uploadStatus !== 'success'}
                            className="flex-1 px-4 py-2 bg-purple-600 hover:bg-purple-500 rounded-lg text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2 shadow-lg shadow-purple-900/20"
                        >
                            {isSubmitting ? 'Creating...' : 'Create Product'}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default ProductView;
