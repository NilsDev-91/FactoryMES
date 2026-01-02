import { Job } from './job';

export interface OrderItem {
    sku: string;
    quantity: number;
    title: string;
    variation_details?: string;
}

export interface Order {
    id: number;
    ebay_order_id: string;
    buyer_username: string;
    total_price: number;
    currency: string;
    status: string;
    created_at: string;
    items: OrderItem[];
    jobs: Job[];
}
