
import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { RefreshCw, Box, AlertCircle } from 'lucide-react';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

// Interfaces matching Backend OrderRead
export interface FilamentReq {
    material: string;
    hex_color: string;
    virtual_id: number;
}

export interface Job {
    id: number;
    status: string;
    filament_requirements: FilamentReq[];
}

export interface OrderItem {
    sku: string;
    quantity: number;
    title: string;
    variation_details?: string;
}

export interface Order {
    id: number;
    ebay_order_id: string; // Mapping to platform_order_id concept
    buyer_username: string;
    total_price: number;
    currency: string;
    status: string; // OPEN, QUEUED, PRINTING, DONE, FAILED
    created_at: string;
    items: OrderItem[];
    jobs: Job[];
}

interface OrderTableProps {
    orders: Order[];
}

export function OrderTable({ orders }: OrderTableProps) {
    if (!orders || orders.length === 0) {
        return (
            <div className="flex flex-col items-center justify-center p-12 text-slate-500 border border-slate-800 rounded-xl bg-slate-900/50 border-dashed">
                <Box size={48} className="mb-4 opacity-50" />
                <p className="text-lg font-medium">No active orders</p>
                <p className="text-sm">Waiting for eBay synchronization...</p>
            </div>
        );
    }

    const getStatusStyle = (status: string) => {
        const s = status.toUpperCase();
        switch (s) {
            case 'OPEN':
                return 'bg-blue-500/20 text-blue-400 border-blue-500/50';
            case 'QUEUED':
                return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/50';
            case 'PRINTING':
                return 'bg-green-500/20 text-green-400 border-green-500/50 animate-pulse';
            case 'DONE':
                return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
            case 'FAILED':
                return 'bg-red-500/20 text-red-400 border-red-500/50';
            default:
                return 'bg-slate-500/20 text-slate-400 border-slate-500/50';
        }
    };

    const formatDate = (dateStr: string) => {
        return new Date(dateStr).toLocaleString();
    };

    return (
        <div className="w-full overflow-hidden rounded-xl border border-slate-800 bg-slate-900 shadow-xl">
            <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-400">
                    <thead className="bg-slate-950 text-slate-200 uppercase tracking-wider text-xs font-semibold">
                        <tr>
                            <th className="px-6 py-4">Order ID</th>
                            <th className="px-6 py-4">Date</th>
                            <th className="px-6 py-4">Items</th>
                            <th className="px-6 py-4">Filament</th>
                            <th className="px-6 py-4 text-right">Total</th>
                            <th className="px-6 py-4 text-center">Status</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800">
                        {orders.map((order) => (
                            <tr key={order.id} className="hover:bg-slate-800/50 transition-colors">
                                <td className="px-6 py-4 font-mono text-slate-300">
                                    {order.ebay_order_id}
                                    <div className="text-xs text-slate-500 mt-1">{order.buyer_username}</div>
                                </td>
                                <td className="px-6 py-4 text-xs">
                                    {formatDate(order.created_at)}
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex flex-col gap-1">
                                        {order.items.map((item, idx) => (
                                            <div key={idx} className="flex items-center gap-2">
                                                <span className="font-bold text-slate-200">{item.quantity}x</span>
                                                <span className="text-slate-300" title={item.title}>{item.sku}</span>
                                                {item.variation_details && (
                                                    <span className="text-[10px] bg-slate-800 px-1 rounded text-slate-400">{item.variation_details}</span>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                </td>
                                <td className="px-6 py-4">
                                    <div className="flex flex-col gap-1">
                                        {order.jobs && order.jobs.length > 0 ? (
                                            order.jobs.map((job) => (
                                                <div key={job.id} className="flex items-center gap-2">
                                                    {/* Job Status Indicator */}
                                                    <div className={cn(
                                                        "w-1 h-3 rounded-full",
                                                        job.status === 'PENDING' ? "bg-yellow-500" :
                                                            job.status === 'PRINTING' ? "bg-green-500 animate-pulse" :
                                                                job.status === 'FAILED' ? "bg-red-500" : "bg-slate-500"
                                                    )} title={`Job Status: ${job.status}`} />

                                                    {/* Filament Dots */}
                                                    <div className="flex -space-x-1 hover:space-x-1 transition-all">
                                                        {job.filament_requirements?.map((req, i) => (
                                                            <div
                                                                key={i}
                                                                className="w-4 h-4 rounded-full border border-slate-800 shadow-sm"
                                                                style={{ backgroundColor: req.hex_color }}
                                                                title={`${req.material} - ${req.hex_color}`}
                                                            />
                                                        ))}
                                                        {(!job.filament_requirements || job.filament_requirements.length === 0) && (
                                                            <span className="text-xs text-slate-600 italic">No Reqs</span>
                                                        )}
                                                    </div>
                                                </div>
                                            ))
                                        ) : (
                                            <span className="text-xs text-slate-600">-</span>
                                        )}
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-right font-mono text-slate-300">
                                    {order.total_price.toFixed(2)} {order.currency}
                                </td>
                                <td className="px-6 py-4 text-center">
                                    <span className={cn(
                                        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
                                        getStatusStyle(order.status)
                                    )}>
                                        {order.status}
                                    </span>
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
