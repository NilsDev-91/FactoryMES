import React, { useState, useEffect, useRef } from 'react';
import { LucideIcon } from 'lucide-react';

interface LiveTelemetryCardProps {
    label: string;
    value: number | string;
    unit: string;
    icon: LucideIcon;
    color?: string;
}

const LiveTelemetryCard: React.FC<LiveTelemetryCardProps> = ({
    label,
    value,
    unit,
    icon: Icon,
    color = "blue"
}) => {
    const [isUpdating, setIsUpdating] = useState(false);
    const prevValueRef = useRef<number | string>(value);

    useEffect(() => {
        if (prevValueRef.current !== value) {
            setIsUpdating(true);
            const timer = setTimeout(() => setIsUpdating(false), 1000);
            prevValueRef.current = value;
            return () => clearTimeout(timer);
        }
    }, [value]);

    const colors = {
        orange: "text-orange-400 border-orange-500/20 ring-orange-500/50",
        blue: "text-blue-400 border-blue-500/20 ring-blue-500/50",
        emerald: "text-emerald-400 border-emerald-500/20 ring-emerald-500/50",
        cyan: "text-cyan-400 border-cyan-500/20 ring-cyan-500/50",
    };

    const selectedColor = colors[color as keyof typeof colors] || colors.blue;

    return (
        <div className={`
            bg-slate-900/40 border rounded-xl p-4 transition-all duration-300
            ${isUpdating ? `ring-2 ${selectedColor} border-transparent scale-[1.02] shadow-lg` : "border-slate-800/80"}
        `}>
            <div className="flex justify-between items-start mb-2">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{label}</span>
                <Icon size={16} className={isUpdating ? selectedColor : "text-slate-600 transition-colors"} />
            </div>
            <div className="flex items-baseline gap-1">
                <span className={`text-2xl font-bold font-mono transition-colors duration-300 ${isUpdating ? selectedColor : "text-white"}`}>
                    {value}
                </span>
                <span className="text-sm font-medium text-slate-500">{unit}</span>
            </div>
            {isUpdating && (
                <div className={`mt-2 h-0.5 rounded-full bg-current ${selectedColor} animate-pulse w-full opacity-30`} />
            )}
        </div>
    );
};

export default LiveTelemetryCard;
