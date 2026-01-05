/**
 * Printer Control API Client
 * Typed API functions for automation configuration and manual overrides.
 */

const API_BASE = 'http://127.0.0.1:8000/api';

export type ClearingStrategy = 'MANUAL' | 'A1_INERTIAL_FLING' | 'X1_MECHANICAL_SWEEP';

export interface AutomationConfig {
    can_auto_eject?: boolean;
    thermal_release_temp?: number;
    clearing_strategy?: ClearingStrategy;
}

/**
 * Update automation configuration for a printer.
 * Auto-eject, thermal release temperature, and clearing strategy.
 */
export async function updateAutomationConfig(
    printerSerial: string,
    config: AutomationConfig
): Promise<void> {
    const res = await fetch(`${API_BASE}/printers/${printerSerial}/automation-config`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || 'Failed to update automation config');
    }
}

/**
 * Manually trigger bed clearing sweep sequence.
 * Only allowed when printer is IDLE, COOLDOWN, or AWAITING_CLEARANCE.
 */
export async function forceClearPrinter(printerSerial: string): Promise<void> {
    const res = await fetch(`${API_BASE}/printers/${printerSerial}/control/force-clear`, {
        method: 'POST',
    });

    if (!res.ok) {
        const error = await res.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || 'Failed to trigger clearing');
    }
}
