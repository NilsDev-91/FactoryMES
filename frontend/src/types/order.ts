export interface OrderItem {
    id: number;
    order_id: number;
    sku: string;
    title: string;
    quantity: number;
    variation_details?: string;
}

export interface Order {
    id: number;
    ebay_order_id: string;
    buyer_username: string;
    total_price: number;
    currency: string;
    status: 'OPEN' | 'QUEUED' | 'PRINTING' | 'DONE' | 'FAILED' | 'IN_PROGRESS';
    created_at: string;
    items: OrderItem[];
    error_message?: string;
}
