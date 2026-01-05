import * as z from 'zod';

/**
 * Robust Product Form Schema
 * Handles Phase 6 Continuous Printing safety and initial render states.
 */
export const productFormSchema = z.object({
    name: z.string().min(3, "Product name must be at least 3 characters"),
    sku: z.string().optional(),
    description: z.string().optional(),
    print_file_id: z.number({ message: "Print file is required" }),
    generate_variants_for_profile_ids: z.array(z.string()),

    // Phase 6: Continuous Printing (Automation Safety)
    part_height_mm: z.number().min(38, "Part too short for A1 Auto-Eject (<38mm).").optional().nullable(),
    is_continuous_printing: z.boolean().optional(),
}).superRefine((data, ctx) => {
    // Logic: if continuous printing is ON, we MUST have a valid number height >= 38
    if (data.is_continuous_printing) {
        const height = data.part_height_mm ?? 0;
        if (!data.part_height_mm || height < 38) {
            ctx.addIssue({
                code: z.ZodIssueCode.custom,
                message: "Safety: Continuous Printing requires part height ≥ 38mm (Gantry Sweep restriction)",
                path: ["is_continuous_printing"], // Attach to the toggle
            });
        }
    }
});

export type ProductFormValues = z.infer<typeof productFormSchema>;
