'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Check, ChevronsUpDown, X, Search } from 'lucide-react';
import { FilamentProfile } from '@/types/api/filament';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Utility for Tailwind class merging
 */
function cn(...inputs: ClassValue[]) {
    return twMerge(clsx(inputs));
}

interface ProfileMultiSelectProps {
    selectedIds: string[];
    onChange: (ids: string[]) => void;
    profiles: FilamentProfile[];
    className?: string;
}

/**
 * A multi-select component designed for selecting Filament Profiles.
 * Implements a Popover + Search pattern for a premium user experience.
 */
export function ProfileMultiSelect({
    selectedIds,
    onChange,
    profiles,
    className,
}: ProfileMultiSelectProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const containerRef = useRef<HTMLDivElement>(null);

    // Close on click outside
    useEffect(() => {
        function handleClickOutside(event: MouseEvent) {
            if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        }
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const toggleProfile = (id: string) => {
        if (selectedIds.includes(id)) {
            onChange(selectedIds.filter((i) => i !== id));
        } else {
            onChange([...selectedIds, id]);
        }
    };

    const removeProfile = (e: React.MouseEvent, id: string) => {
        e.stopPropagation();
        onChange(selectedIds.filter((i) => i !== id));
    };

    const filteredProfiles = profiles.filter((p) => {
        const searchStr = `${p.brand} ${p.material} ${p.color_hex}`.toLowerCase();
        return searchStr.includes(searchQuery.toLowerCase());
    });

    const selectedProfiles = profiles.filter((p) => selectedIds.includes(p.id));

    return (
        <div className={cn("relative w-full", className)} ref={containerRef}>
            {/* Main Trigger / Selected Display */}
            <div
                onClick={() => setIsOpen(!isOpen)}
                className={cn(
                    "min-h-[44px] w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 cursor-pointer transition-all hover:border-slate-700 flex flex-wrap gap-2 items-center",
                    isOpen && "ring-2 ring-blue-500/20 border-blue-500/50"
                )}
            >
                {selectedProfiles.length > 0 ? (
                    selectedProfiles.map((profile) => (
                        <div
                            key={profile.id}
                            className="flex items-center gap-1.5 bg-slate-800 border border-slate-700 text-slate-200 pl-2 pr-1 py-0.5 rounded-lg text-sm animate-in fade-in zoom-in duration-200"
                        >
                            <span
                                className="w-2 h-2 rounded-full border border-white/10"
                                style={{ backgroundColor: profile.color_hex }}
                            />
                            <span>{profile.brand} {profile.material}</span>
                            <button
                                onClick={(e) => removeProfile(e, profile.id)}
                                className="hover:bg-slate-700 p-0.5 rounded-md transition-colors text-slate-400 hover:text-white"
                            >
                                <X className="w-3 h-3" />
                            </button>
                        </div>
                    ))
                ) : (
                    <span className="text-slate-500 text-sm">Select material profiles...</span>
                )}
                <div className="ml-auto pl-2 flex items-center gap-2 text-slate-500">
                    <ChevronsUpDown className="w-4 h-4" />
                </div>
            </div>

            {/* Dropdown Popover */}
            {isOpen && (
                <div className="absolute z-50 top-full left-0 w-full mt-2 bg-slate-900 border border-slate-800 rounded-xl shadow-2xl overflow-hidden animate-in fade-in slide-in-from-top-2 duration-200">
                    {/* Search Input */}
                    <div className="flex items-center px-3 border-b border-slate-800 bg-slate-950/50">
                        <Search className="w-4 h-4 text-slate-500" />
                        <input
                            type="text"
                            placeholder="Search profiles..."
                            className="w-full bg-transparent border-none focus:ring-0 p-3 text-sm text-slate-200 placeholder:text-slate-600"
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            autoFocus
                        />
                    </div>

                    {/* Profiles List */}
                    <div className="max-h-[300px] overflow-y-auto p-1.5">
                        {filteredProfiles.length > 0 ? (
                            filteredProfiles.map((profile) => {
                                const isSelected = selectedIds.includes(profile.id);
                                return (
                                    <div
                                        key={profile.id}
                                        onClick={() => toggleProfile(profile.id)}
                                        className={cn(
                                            "flex items-center justify-between px-3 py-2.5 rounded-lg cursor-pointer transition-all group",
                                            isSelected
                                                ? "bg-blue-500/10 text-blue-400"
                                                : "hover:bg-slate-800 text-slate-400 hover:text-slate-200"
                                        )}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div
                                                className="w-4 h-4 rounded-full border border-white/10 shadow-sm"
                                                style={{ backgroundColor: profile.color_hex.startsWith('#') ? profile.color_hex : `#${profile.color_hex}` }}
                                            />
                                            <div className="flex flex-col">
                                                <span className="text-sm font-medium">{profile.brand} {profile.material}</span>
                                                <span className="text-[10px] uppercase tracking-wider opacity-60">
                                                    {profile.color_hex} • {profile.density}g/cm³
                                                </span>
                                            </div>
                                        </div>
                                        {isSelected && (
                                            <Check className="w-4 h-4 text-blue-500" />
                                        )}
                                    </div>
                                );
                            })
                        ) : (
                            <div className="py-8 text-center text-slate-600 text-sm italic">
                                No profiles found.
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
