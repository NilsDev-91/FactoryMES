'use client';

import React from 'react';
import { Search, Bell, User, Hexagon } from 'lucide-react';

export function Header() {
    return (
        <header className="fixed top-0 left-0 right-0 h-16 bg-slate-950 border-b border-slate-800 flex items-center justify-between px-6 z-50">
            {/* Left: Brand / Logo */}
            <div className="flex items-center gap-3 w-64">
                <div className="flex items-center justify-center w-8 h-8 rounded bg-blue-600/10 border border-blue-500/20">
                    <Hexagon className="text-blue-500" size={20} strokeWidth={2.5} />
                </div>
                <span className="text-lg font-bold tracking-tight text-white">
                    Factory<span className="text-blue-500">OS</span>
                </span>
            </div>

            {/* Center: Global Search */}
            <div className="flex-1 max-w-md px-8">
                <div className="relative group">
                    <div className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
                        <Search className="text-slate-500 group-focus-within:text-blue-400 transition-colors" size={18} />
                    </div>
                    <input
                        type="text"
                        className="w-full h-10 bg-slate-900 border border-slate-800 rounded-lg pl-10 pr-4 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-blue-500 focus:border-blue-500/50 transition-all"
                        placeholder="Search printers, orders, SKUs..."
                    />
                </div>
            </div>

            {/* Right: Actions */}
            <div className="flex items-center gap-4">
                {/* Notifications */}
                <button className="relative p-2 text-slate-400 hover:text-slate-100 hover:bg-slate-800 rounded-full transition-colors">
                    <Bell size={20} />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-red-500 rounded-full ring-2 ring-slate-950" />
                </button>

                {/* User Profile */}
                <div className="flex items-center gap-3 pl-4 border-l border-slate-800/50">
                    <div className="flex flex-col items-end">
                        <span className="text-sm font-medium text-slate-200">Admin User</span>
                        <span className="text-xs text-slate-500">Factory Manager</span>
                    </div>
                    <button className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 hover:bg-slate-700 hover:text-white transition-all ring-2 ring-transparent hover:ring-slate-800">
                        <User size={18} />
                    </button>
                </div>
            </div>
        </header>
    );
}
