/**
 * Represents a single product entry in the public catalog listing.
 */
export interface ProductCatalogItem {
    id: number;
    sku: string;
    name: string;
    /**
     * User-friendly filename stripped of UUID prefixes.
     */
    printfile_display_name: string;
    /**
     * Array of Hex Codes (e.g., ["#FF0000", "#0000FF"]) 
     * extracted from the product's variants.
     */
    variant_colors: string[];
    /**
     * List of unique material types (e.g., ["PLA", "PETG"])
     * supported by the product's variants.
     */
    material_tags: string[];
}
