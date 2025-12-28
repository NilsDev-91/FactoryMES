import React, { useEffect, useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { X, Key, Globe, Layout, ShieldCheck, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { updateEbayConfig } from '../../api';

const ebayConfigSchema = z.object({
    ebay_app_id: z.string().min(1, 'App ID is required'),
    ebay_cert_id: z.string().min(1, 'Cert ID is required'),
    ebay_ru_name: z.string().min(1, 'RU Name is required'),
    ebay_env: z.enum(['SANDBOX', 'PRODUCTION']),
});

type EbayConfigForm = z.infer<typeof ebayConfigSchema>;

interface EbayConfigModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: () => void;
    initialData?: Partial<EbayConfigForm>;
}

const EbayConfigModal: React.FC<EbayConfigModalProps> = ({ isOpen, onClose, onSuccess, initialData }) => {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [showSuccess, setShowSuccess] = useState(false);

    const {
        register,
        handleSubmit,
        reset,
        watch,
        formState: { errors },
    } = useForm<EbayConfigForm>({
        resolver: zodResolver(ebayConfigSchema),
        defaultValues: {
            ebay_env: 'SANDBOX',
            ...initialData
        },
    });

    const watchEnv = watch('ebay_env');

    useEffect(() => {
        if (isOpen) {
            reset({
                ebay_env: 'SANDBOX',
                ...initialData
            });
            setShowSuccess(false);
            setError(null);
        }
    }, [isOpen, initialData, reset]);

    const onSubmit = async (data: EbayConfigForm) => {
        setIsSubmitting(true);
        setError(null);
        try {
            await updateEbayConfig(data);
            setShowSuccess(true);
            onSuccess();
            setTimeout(() => {
                onClose();
            }, 1500);
        } catch (err: any) {
            setError(err.message || 'Failed to update configuration');
        } finally {
            setIsSubmitting(false);
        }
    };

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            {/* Backdrop */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="absolute inset-0 bg-slate-950/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <motion.div
                initial={{ scale: 0.95, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                exit={{ scale: 0.95, opacity: 0 }}
                className="relative bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden"
            >
                <div className="flex items-center justify-between p-6 border-b border-slate-800 bg-slate-800/50">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-lg">
                            <ShieldCheck className="text-blue-500" size={20} />
                        </div>
                        <h3 className="text-xl font-bold text-white tracking-tight">eBay Connection</h3>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-slate-400 hover:text-white hover:bg-slate-800 rounded-xl transition-all"
                    >
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit(onSubmit)} className="p-6 space-y-5">
                    {error && (
                        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-4 flex items-center gap-3 text-red-400 text-sm">
                            <AlertCircle size={18} />
                            <p>{error}</p>
                        </div>
                    )}

                    {showSuccess && (
                        <div className="bg-green-500/10 border border-green-500/20 rounded-xl p-4 flex items-center gap-3 text-green-400 text-sm">
                            <CheckCircle2 size={18} />
                            <p>Configuration saved and reloaded!</p>
                        </div>
                    )}

                    {/* App ID */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            <Key size={12} /> App ID (Client ID)
                        </label>
                        <input
                            {...register('ebay_app_id')}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-mono text-sm"
                            placeholder="e.g., Company-AppName-SBX-..."
                        />
                        {errors.ebay_app_id && <p className="text-xs text-red-400">{errors.ebay_app_id.message}</p>}
                    </div>

                    {/* Cert ID */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            <ShieldCheck size={12} /> Cert ID (Client Secret)
                        </label>
                        <input
                            {...register('ebay_cert_id')}
                            type="password"
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-mono text-sm"
                            placeholder="••••••••••••••••"
                        />
                        {errors.ebay_cert_id && <p className="text-xs text-red-400">{errors.ebay_cert_id.message}</p>}
                    </div>

                    {/* RU Name */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            <Layout size={12} /> RU Name (Redirect Name)
                        </label>
                        <input
                            {...register('ebay_ru_name')}
                            className="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-white placeholder:text-slate-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500 transition-all font-mono text-sm"
                            placeholder="e.g., CompanyName-AppName-..."
                        />
                        {errors.ebay_ru_name && <p className="text-xs text-red-400">{errors.ebay_ru_name.message}</p>}
                    </div>

                    {/* Environment */}
                    <div className="space-y-2">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                            <Globe size={12} /> API Environment
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            {['SANDBOX', 'PRODUCTION'].map((env) => (
                                <label
                                    key={env}
                                    className={`flex items-center justify-center gap-2 px-4 py-3 rounded-xl border cursor-pointer transition-all ${watchEnv === env
                                        ? 'bg-blue-600/10 border-blue-500 text-blue-400'
                                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:bg-slate-800/50'
                                        }`}
                                >
                                    <input
                                        {...register('ebay_env')}
                                        type="radio"
                                        value={env}
                                        className="hidden"
                                    />
                                    <span className="text-sm font-semibold">{env}</span>
                                </label>
                            ))}
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
                            disabled={isSubmitting}
                            className="flex-1 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-3 rounded-xl transition-all shadow-lg shadow-blue-500/20 active:scale-95 flex items-center justify-center gap-2"
                        >
                            {isSubmitting ? (
                                <>
                                    <Loader2 className="animate-spin" size={18} />
                                    Saving...
                                </>
                            ) : (
                                'Save Config'
                            )}
                        </button>
                    </div>
                </form>
            </motion.div>
        </div>
    );
};

export default EbayConfigModal;
