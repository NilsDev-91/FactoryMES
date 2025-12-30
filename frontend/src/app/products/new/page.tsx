'use client';

import React from 'react';
import { Package, ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { CreateProductForm } from '@/components/products/create-product-form';

/**
 * Page component for creating a new product.
 * Now utilizes the modular CreateProductForm for better maintainability and asset linking.
 */
export default function CreateProductPage() {
    return (
        <div className="max-w-3xl mx-auto space-y-6">
            {/* Navigation Header */}
            <div className="flex items-center justify-between">
                <Link
                    href="/products"
                    className="flex items-center gap-2 text-slate-400 hover:text-white transition-colors text-sm font-medium group"
                >
                    <div className="w-8 h-8 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center group-hover:border-slate-700 transition-all">
                        <ArrowLeft size={16} />
                    </div>
                    Back to Catalog
                </Link>
            </div>

            {/* Form Container */}
            <div className="bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
                {/* Visual Accent */}
                <div className="absolute top-0 right-0 w-64 h-64 bg-blue-500/5 blur-[100px] -mr-32 -mt-32" />

                {/* Page Header */}
                <div className="flex items-center gap-5 mb-10 relative">
                    <div className="p-4 bg-gradient-to-br from-blue-500/20 to-indigo-500/20 rounded-2xl text-blue-500 border border-blue-500/20 shadow-inner">
                        <Package size={32} />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-white tracking-tight">Create New Product</h1>
                        <p className="text-slate-400 text-sm mt-1">Define SKU requirements and link print-ready assets</p>
                    </div>
                </div>

                {/* Modular Form Component */}
                <CreateProductForm />
            </div>

            {/* Footer Tip */}
            <div className="flex items-center justify-center gap-2 text-[10px] uppercase tracking-[0.2em] font-bold text-slate-600">
                <div className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-pulse" />
                FactoryOS Product Management System
            </div>
        </div>
    );
}
