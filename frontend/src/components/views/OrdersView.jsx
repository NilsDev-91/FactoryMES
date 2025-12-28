import React, { useState, useEffect } from 'react';
import { ShoppingCart, Package, Link as LinkIcon } from 'lucide-react';
import { fetchConfigStatus } from '../../api';
import EbayConfigModal from '../ebay/EbayConfigModal';
import OrderCard from '../orders/OrderCard';

const OrdersView = ({ orders = [] }) => {
    const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
    const [configStatus, setConfigStatus] = useState({ ebay_configured: false });

    const refreshStatus = async () => {
        const status = await fetchConfigStatus();
        setConfigStatus(status);
    };

    useEffect(() => {
        refreshStatus();
    }, []);

    const handleSync = (order) => {
        console.log("Starting production for order:", order.ebay_order_id);
        // TODO: Implement actual production start API call if needed
    };

    // Safety check for orders prop
    const safeOrders = (Array.isArray(orders) ? orders : []).slice().reverse();

    return (
        <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 space-y-6">
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 backdrop-blur-sm">
                <div className="flex justify-between items-center mb-8">
                    <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                        <ShoppingCart size={20} className="text-blue-400" /> Live Order Feed
                    </h3>
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => setIsConfigModalOpen(true)}
                            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${!configStatus.ebay_configured
                                ? 'bg-red-500/10 text-red-400 border border-red-500/20 animate-pulse'
                                : 'bg-slate-700/50 text-slate-300 border border-slate-600/50 hover:bg-slate-700'
                                }`}
                        >
                            <LinkIcon size={14} />
                            {configStatus.ebay_configured ? 'eBay Connected' : 'Connect eBay'}
                        </button>
                        <div className="text-sm text-slate-400 border-l border-slate-700 pl-4">
                            Total Orders: <span className="text-white font-mono">{safeOrders.length}</span>
                        </div>
                    </div>
                </div>

                <EbayConfigModal
                    isOpen={isConfigModalOpen}
                    onClose={() => setIsConfigModalOpen(false)}
                    onSuccess={refreshStatus}
                />

                {safeOrders.length === 0 ? (
                    <div className="text-center py-20 text-slate-500 flex flex-col items-center">
                        <Package size={48} className="mb-4 opacity-20" />
                        <p>No active orders found.</p>
                    </div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
                        {safeOrders.map((order) => (
                            <OrderCard
                                key={order.id || order.ebay_order_id}
                                order={order}
                                onSync={handleSync}
                            />
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export default OrdersView;
