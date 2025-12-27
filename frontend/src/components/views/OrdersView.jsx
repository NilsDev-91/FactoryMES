import React from 'react';
import { ShoppingCart, Clock, CheckCircle, Package, AlertCircle } from 'lucide-react';

const OrdersView = ({ orders = [] }) => {
    // Safety check for orders prop
    const safeOrders = Array.isArray(orders) ? orders : [];

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm">
                <div className="flex justify-between items-center mb-6">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <ShoppingCart size={20} className="text-blue-400" /> Live Order Feed
                    </h3>
                    <div className="text-sm text-slate-400">
                        Total Orders: <span className="text-white font-mono">{safeOrders.length}</span>
                    </div>
                </div>

                {safeOrders.length === 0 ? (
                    <div className="text-center py-20 text-slate-500 flex flex-col items-center">
                        <Package size={48} className="mb-4 opacity-20" />
                        <p>No active orders found.</p>
                    </div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="text-slate-400 border-b border-slate-700/50 text-sm uppercase tracking-wider">
                                    <th className="py-4 px-4 font-medium">Order ID</th>
                                    <th className="py-4 px-4 font-medium">Platform</th>
                                    <th className="py-4 px-4 font-medium">Product / SKU</th>
                                    <th className="py-4 px-4 font-medium">Status</th>
                                    <th className="py-4 px-4 font-medium text-right">Created At</th>
                                </tr>
                            </thead>
                            <tbody className="text-sm">
                                {safeOrders.slice().reverse().map((order) => {
                                    if (!order) return null;
                                    // Handle missing internal_order_id or platform_order_id
                                    const displayId = order.platform_order_id || order.internal_order_id || (order.id ? String(order.id) : '???');

                                    return (
                                        <tr key={order.id || Math.random()} className="border-b border-slate-700/30 hover:bg-slate-700/20 transition-colors">
                                            <td className="py-4 px-4 text-slate-300 font-mono">
                                                #{displayId.slice(-8)}
                                            </td>
                                            <td className="py-4 px-4">
                                                <div className="text-xs text-slate-500 uppercase font-bold">{order.platform || 'Unknown'}</div>
                                            </td>
                                            <td className="py-4 px-4">
                                                {/* Handle both new 'items' list and legacy flat structure */}
                                                <div className="space-y-1">
                                                    {Array.isArray(order.items) && order.items.length > 0 ? (
                                                        order.items.map((item, idx) => (
                                                            <div key={idx} className="flex items-center gap-2 text-slate-200">
                                                                <span className="text-xs bg-slate-700 px-1.5 rounded text-slate-300">x{item.quantity}</span>
                                                                <span>{item.sku || item.product_id}</span>
                                                            </div>
                                                        ))
                                                    ) : (
                                                        <div className="flex items-center gap-2 text-slate-200">
                                                            <span className="text-xs bg-slate-700 px-1.5 rounded text-slate-300">x{order.quantity || 1}</span>
                                                            <span>{order.sku || 'Unknown Global SKU'}</span>
                                                        </div>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="py-4 px-4">
                                                <div className="flex flex-col gap-1.5 items-start">
                                                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${order.status === 'DONE' ? 'bg-green-500/10 text-green-400 border-green-500/20' :
                                                        order.status === 'OPEN' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                                                            order.status === 'QUEUED' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' :
                                                                order.status === 'PRINTING' ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20' :
                                                                    order.status === 'FAILED' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                                                                        order.status === 'IN_PROGRESS' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' :
                                                                            'bg-slate-700/50 text-slate-400 border-slate-600/50'
                                                        }`}>
                                                        {order.status === 'OPEN' && <CheckCircle size={12} />}
                                                        {order.status === 'QUEUED' && <Clock size={12} />}
                                                        {order.status === 'PRINTING' && <Package size={12} className="animate-pulse" />}
                                                        {order.status === 'FAILED' && <AlertCircle size={12} />}
                                                        {order.status === 'IN_PROGRESS' && <Clock size={12} />}
                                                        {order.status === 'DONE' ? 'COMPLETED' : order.status}
                                                    </span>
                                                    {order.status === 'FAILED' && order.error_message && (
                                                        <span className="text-[10px] text-red-400 max-w-[200px] leading-tight opacity-80">
                                                            {order.error_message}
                                                        </span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="py-4 px-4 text-right text-slate-400 font-mono">
                                                {order.purchase_date ? new Date(order.purchase_date).toLocaleString() : '-'}
                                            </td>
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
};

export default OrdersView;
