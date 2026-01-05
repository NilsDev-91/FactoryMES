import React from 'react';
import { LucideProps } from 'lucide-react';

export function BambuPrinterIcon(props: LucideProps) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width={props.size || 24}
            height={props.size || 24}
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={props.strokeWidth || 2}
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            {/* Outer Frame (Enclosure) - Generic Cuboid */}
            <rect x="3" y="3" width="18" height="18" rx="2" />

            {/* Gantry (X-Axis Carbon Rod) - Top Third */}
            <line x1="3" y1="9" x2="21" y2="9" />

            {/* Toolhead - Distinct Block on Gantry */}
            <rect x="10" y="7" width="4" height="4" rx="1" />

            {/* Build Plate - Bottom Third */}
            <line x1="7" y1="16" x2="17" y2="16" />

            {/* Z-Axis Lead Screws (Subtle Detail) */}
            <line x1="7" y1="16" x2="7" y2="21" className="opacity-50" />
            <line x1="17" y1="16" x2="17" y2="21" className="opacity-50" />
        </svg>
    );
}
