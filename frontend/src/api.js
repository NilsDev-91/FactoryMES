const API_BASE_URL = 'http://localhost:8000';

export const fetchPrinters = async () => {
    console.log("[DEBUG] fetchPrinters called");
    try {
        const response = await fetch(`${API_BASE_URL}/api/printers`);
        console.log("[DEBUG] fetchPrinters status:", response.status);
        if (!response.ok) {
            console.warn('[DEBUG] Failed to fetch printers');
            return [];
        }
        const json = await response.json();
        console.log("[DEBUG] fetchPrinters data:", json);
        return json;
    } catch (e) {
        console.error("[DEBUG] fetchPrinters error", e);
        return [];
    }
};

export const fetchOrders = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/orders`);
        if (!response.ok) {
            console.warn('Failed to fetch orders');
            return [];
        }
        return response.json();
    } catch (e) {
        return [];
    }
};

export const fetchProducts = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/products`);
        if (!response.ok) throw new Error('Failed to fetch products');
        return response.json();
    } catch (e) {
        console.error("fetchProducts error", e);
        return [];
    }
};

export const createProduct = async (productData) => {
    const response = await fetch(`${API_BASE_URL}/api/products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(productData),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to create product' }));
        throw new Error(err.detail || 'Failed to create product');
    }
    return response.json();
};

export const uploadProductFile = async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/api/products/upload`, {
        method: 'POST',
        body: formData, // No Content-Type header needed
    });

    if (!response.ok) throw new Error('File upload failed');
    return response.json();
};

export const deleteProduct = async (id) => {
    const response = await fetch(`${API_BASE_URL}/api/products/${id}`, {
        method: 'DELETE',
    });
    if (!response.ok) throw new Error('Failed to delete product');
    return response.json();
};

export const updateProduct = async (id, data) => {
    const response = await fetch(`${API_BASE_URL}/api/products/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!response.ok) throw new Error('Failed to update product');
    return response.json();
};

export const fetchConfigStatus = async () => {
    try {
        const response = await fetch(`${API_BASE_URL}/api/system/config/status`);
        if (!response.ok) return { ebay_configured: false };
        return response.json();
    } catch (e) {
        return { ebay_configured: false };
    }
};

export const updateEbayConfig = async (data) => {
    const response = await fetch(`${API_BASE_URL}/api/system/config/ebay`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        const err = await response.json().catch(() => ({ detail: 'Failed to update eBay config' }));
        throw new Error(err.detail || 'Failed to update eBay config');
    }
    return response.json();
};
