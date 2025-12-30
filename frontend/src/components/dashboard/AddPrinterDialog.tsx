
import React, { useState } from 'react';
import { X, Printer, Router, Lock, Type, CheckCircle2, Loader2, AlertTriangle } from 'lucide-react';
import { mutate } from 'swr';

interface AddPrinterDialogProps {
    isOpen: boolean;
    onClose: () => void;
}

export const AddPrinterDialog: React.FC<AddPrinterDialogProps> = ({ isOpen, onClose }) => {
    const [formData, setFormData] = useState({
        serial: '',
        name: '',
        ip_address: '',
        access_code: '',
        type: 'P1S'
    });
    const [status, setStatus] = useState<'idle' | 'submitting' | 'success' | 'error'>('idle');
    const [errorMsg, setErrorMsg] = useState('');

    if (!isOpen) return null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setStatus('submitting');
        setErrorMsg('');

        try {
            const res = await fetch('http://127.0.0.1:8000/api/printers', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!res.ok) throw new Error('Failed to add printer');

            setStatus('success');
            mutate('http://127.0.0.1:8000/api/printers'); // Refresh list

            setTimeout(() => {
                onClose();
                setStatus('idle');
                setFormData({ serial: '', name: '', ip_address: '', access_code: '', type: 'P1S' });
            }, 1000);

        } catch (error: any) {
            setStatus('error');
            setErrorMsg(error.message);
        }
    };

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <div className="absolute inset-0 bg-slate-950/80 backdrop-blur-sm animate-in fade-in" onClick={onClose} />

            <div className="relative w-full max-w-md bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden animate-in zoom-in-95">
                <div className="flex justify-between items-center p-6 border-b border-slate-700 bg-slate-800/50">
                    <h3 className="text-xl font-bold text-white flex items-center gap-2">
                        <Printer className="text-blue-500" /> Add New Printer
                    </h3>
                    <button onClick={onClose} className="text-slate-400 hover:text-white"><X size={20} /></button>
                </div>

                {status === 'success' ? (
                    <div className="p-12 flex flex-col items-center text-center">
                        <div className="w-16 h-16 bg-green-500 rounded-full flex items-center justify-center mb-4 shadow-lg shadow-green-500/30">
                            <CheckCircle2 className="text-white" size={32} />
                        </div>
                        <h3 className="text-xl font-bold text-white">Printer Added!</h3>
                        <p className="text-slate-400 mt-2">Connecting to device...</p>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="p-6 space-y-4">
                        <div>
                            <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Friendly Name</label>
                            <input
                                required
                                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-blue-500"
                                placeholder="e.g. Lab Printer 1"
                                value={formData.name}
                                onChange={e => setFormData({ ...formData, name: e.target.value })}
                            />
                        </div>

                        <div>
                            <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Serial Number</label>
                            <div className="relative">
                                <span className="absolute left-3 top-2.5 text-slate-600"><Printer size={16} /></span>
                                <input
                                    required
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-white font-mono focus:outline-none focus:border-blue-500"
                                    placeholder="01S00C..."
                                    value={formData.serial}
                                    onChange={e => setFormData({ ...formData, serial: e.target.value })}
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase mb-1">IP Address</label>
                                <div className="relative">
                                    <span className="absolute left-3 top-2.5 text-slate-600"><Router size={16} /></span>
                                    <input
                                        required
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-white font-mono focus:outline-none focus:border-blue-500"
                                        placeholder="192.168.x.x"
                                        value={formData.ip_address}
                                        onChange={e => setFormData({ ...formData, ip_address: e.target.value })}
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Access Code</label>
                                <div className="relative">
                                    <span className="absolute left-3 top-2.5 text-slate-600"><Lock size={16} /></span>
                                    <input
                                        required
                                        className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-white font-mono focus:outline-none focus:border-blue-500"
                                        placeholder="Access Code"
                                        value={formData.access_code}
                                        onChange={e => setFormData({ ...formData, access_code: e.target.value })}
                                    />
                                </div>
                            </div>
                        </div>

                        <div>
                            <label className="block text-xs font-bold text-slate-400 uppercase mb-1">Model Type</label>
                            <div className="relative">
                                <span className="absolute left-3 top-2.5 text-slate-600"><Type size={16} /></span>
                                <select
                                    className="w-full bg-slate-950 border border-slate-700 rounded-lg pl-9 pr-3 py-2 text-white focus:outline-none focus:border-blue-500 appearance-none"
                                    value={formData.type}
                                    onChange={e => setFormData({ ...formData, type: e.target.value })}
                                >
                                    <option value="P1S">Bambu Lab P1S</option>
                                    <option value="A1">Bambu Lab A1</option>
                                    <option value="X1C">Bambu Lab X1C</option>
                                    <option value="P1P">Bambu Lab P1P</option>
                                    <option value="A1 Mini">Bambu Lab A1 Mini</option>
                                </select>
                            </div>
                        </div>

                        {status === 'error' && (
                            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg flex items-center gap-2 text-red-400 text-sm">
                                <AlertTriangle size={16} /> {errorMsg || 'Failed to add printer'}
                            </div>
                        )}

                        <div className="pt-2 flex gap-3">
                            <button type="button" onClick={onClose} className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 rounded-lg text-slate-300 font-bold transition-colors">
                                Cancel
                            </button>
                            <button
                                type="submit"
                                disabled={status === 'submitting'}
                                className="flex-1 px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-white font-bold transition-colors shadow-lg shadow-blue-900/20 active:scale-95 flex items-center justify-center gap-2"
                            >
                                {status === 'submitting' ? <Loader2 className="animate-spin" /> : 'Connect Device'}
                            </button>
                        </div>
                    </form>
                )}
            </div>
        </div>
    );
};
