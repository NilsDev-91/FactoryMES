import React from 'react';
import { ShoppingCart, User, Tag, Clock, Package, AlertCircle, CheckCircle, Play } from 'lucide-react';

const OrderCard = ({ order, onSync }) => {
    const statusColors = {
        OPEN: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
        QUEUED: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
        PRINTING: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20',
        DONE: 'bg-green-500/10 text-green-400 border-green-500/20',
        FAILED: 'bg-red-500/10 text-red-400 border-red-500/20',
        IN_PROGRESS: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
    };

    const StatusIcon = {
        OPEN: CheckCircle,
        QUEUED: Clock,
        PRINTING: Package,
        DONE: CheckCircle,
        FAILED: AlertCircle,
        IN_PROGRESS: Clock,
    }[order.status] || AlertCircle;

    return (
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl overflow-hidden backdrop-blur-sm hover:border-slate-600/50 transition-all group">
            {/* Header */}
            <div className="p-4 border-b border-slate-700/50 flex justify-between items-start bg-slate-800/20">
                <div className="space-y-1">
                    <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-slate-500 uppercase tracking-wider">#{order.ebay_order_id?.slice(-8)}</span>
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${statusColors[order.status]}`}>
                            {order.status}
                        </span>
                    </div>
                    <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                        <User size={14} className="text-slate-400" /> {order.buyer_username}
                    </h4>
                </div>
                <div className="text-right">
                    <div className="text-sm font-bold text-white">{order.total_price} {order.currency}</div>
                    <div className="text-[10px] text-slate-500 font-mono">{new Date(order.created_at).toLocaleDateString()}</div>
                </div>
            </div>

            {/* Body - Items */}
            <div className="p-4 space-y-3">
                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center gap-2">
                    <Package size={12} /> Order Items
                </div>
                <div className="space-y-2">
                    {order.items?.map((item, idx) => (
                        <div key={item.id || idx} className="bg-slate-900/40 border border-slate-800/50 p-2.5 rounded-lg space-y-1">
                            <div className="flex justify-between items-start">
                                <div className="text-xs font-semibold text-slate-200">
                                    <span className="text-blue-400 mr-1.5">{item.quantity}x</span>
                                    {item.sku}
                                </div>
                            </div>
                            <div className="text-[11px] text-slate-400 line-clamp-1">{item.title}</div>
                            {item.variation_details && (
                                <div className="pt-1 flex flex-wrap gap-1">
                                    <span className="px-1.5 py-0.5 bg-slate-800 text-slate-400 text-[9px] rounded border border-slate-700/50">
                                        {item.variation_details}
                                    </span>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Footer - Actions */}
            {order.status === 'OPEN' && (
                <div className="px-4 pb-4">
                    <button
                        onClick={() => onSync && onSync(order)}
                        className="w-full py-2 bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold rounded-lg transition-colors flex items-center justify-center gap-2 shadow-lg shadow-blue-900/20"
                    >
                        <Play size={12} fill="currentColor" /> Start Production
                    </button>
                </div>
            )}

            {order.status === 'FAILED' && order.error_message && (
                <div className="px-4 pb-4">
                    <div className="p-2 bg-red-500/10 border border-red-500/20 rounded-lg flex items-start gap-2">
                        <AlertCircle size={12} className="text-red-400 mt-0.5 shrink-0" />
                        <span className="text-[10px] text-red-400 leading-tight">{order.error_message}</span>
                    </div>
                </div>
            )}
        </div>
    );
};

export default OrderCard;
