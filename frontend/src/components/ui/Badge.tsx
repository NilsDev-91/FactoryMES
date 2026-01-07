import React from 'react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'outline' | 'success' | 'warning' | 'destructive' | 'info';
}

export function Badge({ className, variant = 'default', ...props }: BadgeProps) {
    const variants = {
        default: 'bg-slate-800 text-slate-100 border-slate-700',
        outline: 'bg-transparent text-slate-300 border-slate-800',
        success: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/50',
        warning: 'bg-amber-500/20 text-amber-500 border-amber-500/50',
        destructive: 'bg-red-500/20 text-red-500 border-red-500/50',
        info: 'bg-blue-500/20 text-blue-400 border-blue-500/50',
    };

    return (
        <div
            className={cn(
                'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border transition-colors',
                variants[variant],
                className
            )}
            {...props}
        />
    );
}
