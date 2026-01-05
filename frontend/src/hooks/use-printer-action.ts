"use client"

import { useMutation, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"
import { sendPrinterCommand, PrinterCommand } from "../lib/api/printer-commands"
import { Printer } from "../types/printer"

interface PrinterMutationContext {
    previousPrinters?: Printer[]
}

export function usePrinterAction(printerId: string) {
    const queryClient = useQueryClient()

    return useMutation({
        mutationFn: (command: PrinterCommand) => sendPrinterCommand(printerId, command),

        // Optimistic Update Logic
        onMutate: async (command) => {
            // Cancel any outgoing refetches (so they don't overwrite our optimistic update)
            await queryClient.cancelQueries({ queryKey: ['printers'] })

            // Snapshot the previous value
            const previousPrinters = queryClient.getQueryData<Printer[]>(['printers'])

            // Optimistically update to the new value
            if (command === 'CONFIRM_CLEARANCE') {
                queryClient.setQueryData<Printer[]>(['printers'], (old) => {
                    if (!old) return previousPrinters;

                    return old.map((p) =>
                        p.serial === printerId
                            ? { ...p, current_status: 'IDLE', current_progress: 0 }
                            : p
                    );
                });

                toast.info("Clearing printer state...", {
                    id: `printer-action-${printerId}`,
                    description: "Optimistic transition to IDLE initiated."
                });
            }

            return { previousPrinters }
        },

        // If the mutation fails, use the context we returned above
        onError: (err, command, context) => {
            if (context?.previousPrinters) {
                queryClient.setQueryData(['printers'], context.previousPrinters)
            }

            toast.error("Action Failed", {
                id: `printer-action-${printerId}`,
                description: err instanceof Error ? err.message : "Hardware communication error"
            });
        },

        // Always refetch after error or success to throw away optimistic local state
        onSettled: (data, error, command) => {
            queryClient.invalidateQueries({ queryKey: ['printers'] });

            if (!error) {
                if (command === 'CONFIRM_CLEARANCE') {
                    toast.success("Bed Clearance Verified", {
                        id: `printer-action-${printerId}`,
                        description: "Printer marked as ready. Next job queued."
                    });
                } else {
                    toast.success(`Command Sent: ${command.replace('_', ' ')}`, {
                        id: `printer-action-${printerId}`
                    });
                }
            }
        },
    })
}
