'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
    LayoutDashboard,
    ShoppingCart,
    Package,
    Settings,
    Workflow,
} from 'lucide-react';
import { BambuPrinterIcon } from '@/components/icons/BambuPrinterIcon';

export function Sidebar() {
    const pathname = usePathname();

    const navItems = [
        { label: 'Dashboard', href: '/', icon: LayoutDashboard },
        { label: 'Fleet', href: '/printers', icon: BambuPrinterIcon },
        { label: 'Print Jobs', href: '/jobs', icon: Workflow },
        { label: 'Products', href: '/products', icon: Package },
        { label: 'Live Order Feed', href: '/orders', icon: ShoppingCart },
        { label: 'Printing Operations', href: '/operations', icon: BambuPrinterIcon },
        { label: 'Logistics', href: '/logistics', icon: Package },
        { label: 'Settings', href: '/settings', icon: Settings },
    ];

    return (
        <aside className="fixed left-0 top-16 bottom-0 w-64 bg-slate-900 border-r border-slate-800 z-40 flex flex-col">
            <div className="flex-1 py-6 flex flex-col gap-1 w-full p-3">
                {navItems.map((item) => {
                    const isActive = item.href === '/'
                        ? pathname === '/'
                        : pathname.startsWith(item.href);

                    const Icon = item.icon;

                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 group relative
                                ${isActive
                                    ? 'bg-blue-600/10 text-blue-400 font-medium'
                                    : 'text-slate-400 hover:text-white hover:bg-slate-800'
                                }
                            `}
                        >
                            {/* Active Border Indicator (Left) */}
                            {isActive && (
                                <span className="absolute left-0 top-1/2 -translate-y-1/2 h-8 w-1 bg-blue-500 rounded-r-full" />
                            )}

                            <Icon
                                size={20}
                                strokeWidth={isActive ? 2.5 : 2}
                                className={`transition-transform duration-200 ${isActive ? 'text-blue-400' : 'group-hover:text-white'}`}
                            />

                            <span className="text-sm">
                                {item.label}
                            </span>
                        </Link>
                    );
                })}
            </div>
        </aside>
    );
}
