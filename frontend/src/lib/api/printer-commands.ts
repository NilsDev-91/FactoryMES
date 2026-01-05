import { z } from 'zod';
import { apiClient } from '../api-client';

export const PrinterCommandSchema = z.enum([
    'CONFIRM_CLEARANCE',
    'PAUSE_PRINT',
    'RESUME_PRINT',
    'CANCEL_PRINT',
    'CLEAR_ERROR'
]);

export type PrinterCommand = z.infer<typeof PrinterCommandSchema>;

/**
 * Maps frontend UI commands to backend API endpoints
 */
const CommandEndpointMap: Record<PrinterCommand, string> = {
    CONFIRM_CLEARANCE: '/confirm-clearance',
    PAUSE_PRINT: '/pause',
    RESUME_PRINT: '/resume',
    CANCEL_PRINT: '/cancel',
    CLEAR_ERROR: '/clear-error'
};

/**
 * Dispatches a hardware command to a specific printer
 */
export async function sendPrinterCommand(printerId: string, command: PrinterCommand) {
    const validatedCommand = PrinterCommandSchema.parse(command);
    const endpoint = `/printers/${printerId}${CommandEndpointMap[validatedCommand]}`;

    return apiClient(endpoint, {
        method: 'POST',
    });
}

/**
 * Fetches the current list of printers
 */
export async function getPrinters() {
    return apiClient<any[]>('/printers');
}
