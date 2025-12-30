
'use client';

import React from 'react';
import useSWR from 'swr';
import { OrderTable, Order } from '@/components/orders/OrderTable';
import { RefreshCw, ShoppingCart } from 'lucide-react';

// Fetcher function for SWR
const fetcher = (url: string) => fetch(url).then((res) => res.json());

export default function OrdersPage() {
    // Poll every 5 seconds

    const { data: orders, error, isLoading, mutate } = useSWR<Order[]>(
        'http://127.0.0.1:8000/api/orders',
        fetcher,
        { refreshInterval: 5000 }
    );

    return (
        <div className="space-y-6 max-w-[1400px] mx-auto">
            {/* Header */}
            <header className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 bg-blue-500/10 rounded-xl text-blue-500">
                        <ShoppingCart size={32} />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold text-white tracking-tight">Incoming Orders</h1>
                        <p className="text-slate-400 text-sm">Monitor eBay sales and production queue</p>
                    </div>
                </div>

                <button
                    onClick={() => mutate()}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition-colors border border-slate-700 font-medium text-sm"
                >
                    <RefreshCw size={16} className={isLoading ? "animate-spin" : ""} />
                    Refresh
                </button>
            </header>

            {/* Error State */}
            {error && (
                <div className="p-4 bg-red-500/10 border border-red-500/20 text-red-400 rounded-lg">
                    Failed to load orders. Is the backend running?
                </div>
            )}

            {/* Loading State */}
            {isLoading && !orders && (
                <div className="flex items-center justify-center p-12 text-slate-500">
                    <RefreshCw size={32} className="animate-spin mb-2" />
                    <span className="sr-only">Loading...</span>
                </div>
            )}

            {/* Content */}
            {orders && (
                <OrderTable orders={orders} />
            )}
        </div>
    );
}
