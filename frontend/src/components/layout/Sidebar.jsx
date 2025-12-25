import React, { useState } from 'react';
import {
    LayoutDashboard,
    ShoppingCart,
    Printer,
    Package,
    Settings,
    ChevronRight,
    ChevronLeft
} from 'lucide-react';

export const Sidebar = ({ activeView, onNavigate, onExpandChange }) => {
    const [isExpanded, setIsExpanded] = useState(false);

    // Notify parent of expansion change for layout adjustment
    React.useEffect(() => {
        if (onExpandChange) onExpandChange(isExpanded);
    }, [isExpanded, onExpandChange]);

    // Map labels to view identifiers or just use labels directly
    const navItems = [
        { label: 'Dashboard', id: 'Dashboard', icon: LayoutDashboard },
        { label: 'Fleet', id: 'Fleet', icon: Printer },
        { label: 'Products', id: 'Products', icon: Package },
        { label: 'Live Order Feed', id: 'Orders', icon: ShoppingCart },
        { label: 'Printing Operations', id: 'Operations', icon: Printer },
        { label: 'Logistics', id: 'Logistics', icon: Package },
        { label: 'Settings', id: 'Settings', icon: Settings },
    ];

    return (
        <aside
            className={`fixed left-0 top-16 bottom-0 bg-slate-900 border-r border-slate-800 z-40 flex flex-col transition-[width] duration-300 ease-in-out shadow-2xl shadow-black/50
                ${isExpanded ? 'w-[260px]' : 'w-[85px]'}`
            }
            onMouseEnter={() => setIsExpanded(true)}
            onMouseLeave={() => setIsExpanded(false)}
        >
            <div className="flex-1 py-6 flex flex-col gap-2">
                {navItems.map((item) => {
                    const isActive = activeView === item.id;
                    const Icon = item.icon;

                    return (
                        <button
                            key={item.id}
                            onClick={() => onNavigate(item.id)}
                            className={`relative flex items-center h-14 px-0 transition-all duration-200 group w-full overflow-hidden
                                ${isActive
                                    ? 'text-blue-400 bg-blue-500/5 shadow-[inset_4px_0_0_0_#3b82f6]'
                                    : 'text-slate-400 hover:text-slate-100 hover:bg-slate-800/50'
                                }
                            `}
                        >
                            {/* Icon Container - Fixed Width 85px to prevent shifting */}
                            <div className="min-w-[85px] h-full flex items-center justify-center z-10">
                                <Icon
                                    size={22}
                                    className={`transition-transform duration-300 ${isActive ? 'scale-110 drop-shadow-[0_0_8px_rgba(59,130,246,0.5)]' : 'group-hover:scale-110'}`}
                                />
                            </div>

                            {/* Label - Reveals on expand */}
                            <span
                                className={`whitespace-nowrap font-medium text-sm transition-all duration-300 transform origin-left
                                    ${isExpanded
                                        ? 'opacity-100 translate-x-0'
                                        : 'opacity-0 -translate-x-4 pointer-events-none'
                                    }
                                `}
                            >
                                {item.label}
                            </span>
                        </button>
                    );
                })}
            </div>
        </aside>
    );
};
