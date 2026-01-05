
'use client';

import { ColumnDef } from '@tanstack/react-table';
import { FileText, Settings, Trash2 } from 'lucide-react';
import { ProductCatalogItem } from '@/types/api/catalog';

// --- Custom UI Components (Standalone for now) ---

const Badge = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => (
    <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-800 border border-slate-700 text-slate-400 ${className}`}>
        {children}
    </span>
);

const ColorCircle = ({ hex }: { hex: string }) => {
    let cleanHex = hex.replace('#', '');
    if (cleanHex.length === 8) cleanHex = cleanHex.substring(0, 6);
    const displayColor = `#${cleanHex}`;
    return (
        <div className="group relative">
            <div
                className="w-4 h-4 rounded-full border border-white/10 shadow-sm transition-transform hover:scale-125"
                style={{ backgroundColor: displayColor }}
            />
            {/* Simple Tooltip on Hover */}
            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2 py-1 bg-slate-950 border border-slate-800 text-[10px] text-white rounded opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity whitespace-nowrap z-50 shadow-xl">
                {displayColor}
            </div>
        </div>
    );
};

// --- Column Definitions ---

export const getColumns = (
    onEdit: (id: number) => void,
    onDelete: (id: number, name: string) => void
): ColumnDef<ProductCatalogItem>[] => [
        {
            accessorKey: 'id',
            header: 'ID',
            cell: ({ row }) => <span className="font-mono text-slate-500 text-xs">#{row.original.id}</span>
        },
        {
            header: 'Product',
            cell: ({ row }) => {
                const product = row.original;
                return (
                    <div className="flex items-center gap-4">
                        <div className="w-12 h-12 rounded-lg bg-slate-800 border border-slate-700 overflow-hidden flex items-center justify-center shrink-0 shadow-sm">
                            <img
                                src={`http://127.0.0.1:8000/api/products/${product.id}/thumbnail`}
                                alt={product.name}
                                className="w-full h-full object-cover"
                                onError={(e) => {
                                    (e.target as HTMLImageElement).style.display = 'none';
                                    (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
                                }}
                            />
                            <div className="hidden">
                                <FileText size={20} className="text-slate-600" />
                            </div>
                        </div>
                        <div>
                            <div className="font-bold text-white tracking-tight">{product.name}</div>
                            <div className="text-[10px] font-mono text-purple-400/80 uppercase tracking-widest">{product.sku}</div>
                        </div>
                    </div>
                );
            }
        },
        {
            header: 'Requirements',
            cell: ({ row }) => {
                const variant_colors = row.original.variant_colors || [];
                const material_tags = row.original.material_tags || [];
                return (
                    <div className="flex items-center gap-3">
                        {/* Colors */}
                        <div className="flex -space-x-1">
                            {variant_colors.length > 0 ? (
                                variant_colors.map((hex, idx) => (
                                    <ColorCircle key={`${hex}-${idx}`} hex={hex} />
                                ))
                            ) : (
                                <span className="text-[10px] text-slate-600 italic">No Color Req</span>
                            )}
                        </div>

                        {/* Materials */}
                        <div className="flex gap-1">
                            {material_tags.map((tag) => (
                                <Badge key={tag}>{tag}</Badge>
                            ))}
                        </div>
                    </div>
                );
            }
        },
        {
            header: 'File',
            cell: ({ row }) => {
                const product = row.original;
                const fileName = product.printfile_display_name;
                const hasFile = fileName && fileName !== "No File";

                if (!hasFile) {
                    return <span className="text-slate-600 text-[10px] italic">No Asset Linked</span>;
                }

                return (
                    <button
                        onClick={() => {
                            // Action for the file (e.g., copy path or trigger logic)
                            console.log("File Action:", fileName);
                        }}
                        className="flex items-center gap-2 text-slate-400 hover:text-emerald-400 text-xs font-mono bg-slate-800/50 hover:bg-emerald-500/10 border border-slate-700 hover:border-emerald-500/20 px-3 py-1.5 rounded-lg transition-all"
                    >
                        <FileText size={14} className="shrink-0" />
                        <span className="max-w-[150px] truncate">
                            {fileName}
                        </span>
                    </button>
                );
            }
        },
        {
            id: 'actions',
            header: () => <div className="text-right">Actions</div>,
            cell: ({ row }) => {
                const product = row.original;
                return (
                    <div className="flex justify-end gap-1">
                        <button
                            onClick={() => onEdit(product.id)}
                            className="p-2 text-slate-500 hover:text-white hover:bg-slate-800 rounded-lg transition-all"
                        >
                            <Settings size={16} />
                        </button>
                        <button
                            onClick={() => onDelete(product.id, product.name)}
                            className="p-2 text-slate-500 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                        >
                            <Trash2 size={16} />
                        </button>
                    </div>
                );
            }
        }
    ];
