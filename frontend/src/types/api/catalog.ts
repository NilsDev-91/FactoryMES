/**
 * Product Catalog Types
 */

export interface ProductCatalogItem {
    id: number;
    name: string;
    sku?: string;
    description?: string;
    variant_colors?: string[];  // Array of hex colors
    material_tags?: string[];   // Array of material types like "PLA", "PETG"
    printfile_display_name?: string;
    print_file_id?: number;
    variant_count?: number;
    created_at?: string;
}
