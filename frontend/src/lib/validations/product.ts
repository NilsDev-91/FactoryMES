import * as z from 'zod';

/**
 * Robust Product Form Schema
 * Handles Phase 6 Continuous Printing safety and initial render states.
 */
export const productFormSchema = z.object({
    name: z.string().min(3, "Product name must be at least 3 characters"),
    sku: z.string().optional(),
    description: z.string().optional(),
    print_file_id: z.number({ required_error: "Print file is required" }),
    generate_variants_for_profile_ids: z.array(z.string()).optional().default([]),

    // Phase 6: Continuous Printing (Automation Safety)
    // Accept empty string as initial state to avoid hydration/uncontrolled warnings
    part_height_mm: z.preprocess(
        (val) => val === "" ? undefined : val,
        z.union([z.number(), z.undefined(), z.null(), z.literal('')])
    ),
    is_continuous_printing: z.boolean().default(false),
}).superRefine((data, ctx) => {
    // Logic: if continuous printing is ON, we MUST have a valid number height >= 50
    if (data.is_continuous_printing) {
        const height = typeof data.part_height_mm === 'number' ? data.part_height_mm : 0;
        if (!data.part_height_mm || height < 50) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: "Safety: Continuous Printing requires part height ≥ 50mm (Gantry Sweep restriction)",
                path: ["is_continuous_printing"], // Attach to the toggle
            });
        }
    }
});

export type ProductFormValues = z.infer<typeof productFormSchema>;
