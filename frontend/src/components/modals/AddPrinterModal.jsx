import React, { useState } from 'react';
import { X, Plus, Monitor, Hash, Globe, Key, ChevronDown } from 'lucide-react';

const AddPrinterModal = ({ isOpen, onClose, onAdd }) => {
    const [formData, setFormData] = useState({
        name: '',
        serial: '',
        ip: '',
        access_code: '',
        type: 'A1'
    });

    if (!isOpen) return null;

    const handleSubmit = (e) => {
        e.preventDefault();
        onAdd({
            ...formData,
            current_status: 'IDLE',
            current_temp_nozzle: 0,
            current_temp_bed: 0,
            current_progress: 0,
            remaining_time: 0,
            ams_data: []
        });
        onClose();
        // Reset form
        setFormData({ name: '', serial: '', ip: '', access_code: '', type: 'A1' });
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm transition-opacity"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden animate-in zoom-in-95 duration-200">
                <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-800/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-lg">
                            <Plus className="text-blue-500" size={20} />
                        </div>
                        <h3 className="text-xl font-bold text-white tracking-tight">Add New Device</h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-all"
                    >
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-5">
                    {/* Printer Name */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            <Monitor size={12} /> Printer Name
                        </label>
                        <input
                            required
                            type="text"
                            placeholder='e.g., "Bambu-01"'
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                        />
                    </div>

                    {/* Serial & Model */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                <Hash size={12} /> Serial Number
                            </label>
                            <input
                                required
                                type="text"
                                placeholder="Unique ID"
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-mono text-sm"
                                value={formData.serial}
                                onChange={(e) => setFormData({ ...formData, serial: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                Model
                            </label>
                            <div className="relative">
                                <select
                                    className="w-full appearance-none bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                                    value={formData.type}
                                    onChange={(e) => setFormData({ ...formData, type: e.target.value })}
                                >
                                    <option value="A1">A1</option>
                                    <option value="A1 Mini">A1 Mini</option>
                                    <option value="P1S">P1S</option>
                                    <option value="X1C">X1C</option>
                                </select>
                                <ChevronDown className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" size={16} />
                            </div>
                        </div>
                    </div>

                    {/* IP & Access Code */}
                    <div className="grid grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                <Globe size={12} /> IP Address
                            </label>
                            <input
                                required
                                type="text"
                                placeholder="192.168.x.x"
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                                value={formData.ip}
                                onChange={(e) => setFormData({ ...formData, ip: e.target.value })}
                            />
                        </div>
                        <div className="space-y-2">
                            <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                <Key size={12} /> Access Code
                            </label>
                            <input
                                required
                                type="password"
                                placeholder="********"
                                className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all"
                                value={formData.access_code}
                                onChange={(e) => setFormData({ ...formData, access_code: e.target.value })}
                            />
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 rounded-xl transition-all active:scale-95"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl transition-all shadow-lg shadow-blue-500/20 active:scale-95"
                        >
                            Connect
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default AddPrinterModal;
