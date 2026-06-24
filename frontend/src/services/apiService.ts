/**
 * Supply Chain API Service
 * Complete integration layer for the Flask REST backend.
 * Backend Base URL: http://localhost:5000
 */

const BASE_URL = "http://localhost:5000/api";

// ── Auth helpers ────────────────────────────────────────────────────────────
const getHeaders = (): Record<string, string> => {
  const token = localStorage.getItem("sc_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

const handleResponse = async (res: Response) => {
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
};

export const apiService = {

  // ════════════════════════════════════════════════════════════════════
  // AUTH
  // ════════════════════════════════════════════════════════════════════
  auth: {
    login: async (username: string, password: string) => {
      const res = await fetch(`${BASE_URL}/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Login failed");
      localStorage.setItem("sc_token", data.token);
      localStorage.setItem("sc_user", JSON.stringify(data.user));
      return data;
    },

    register: async (payload: { username: string; email: string; password: string; role?: string }) => {
      return handleResponse(await fetch(`${BASE_URL}/auth/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      }));
    },

    changePassword: async (old_password: string, new_password: string) => {
      return handleResponse(await fetch(`${BASE_URL}/auth/change-password`, {
        method: "PUT",
        headers: getHeaders(),
        body: JSON.stringify({ old_password, new_password }),
      }));
    },

    getMe: async () => {
      return handleResponse(await fetch(`${BASE_URL}/auth/me`, { headers: getHeaders() }));
    },

    logout: () => {
      localStorage.removeItem("sc_token");
      localStorage.removeItem("sc_user");
    },

    getCurrentUser: () => {
      const u = localStorage.getItem("sc_user");
      return u ? JSON.parse(u) : null;
    },

    isLoggedIn: () => !!localStorage.getItem("sc_token"),
  },

  // ════════════════════════════════════════════════════════════════════
  // DASHBOARD
  // ════════════════════════════════════════════════════════════════════
  dashboard: {
    getStats: async () =>
      handleResponse(await fetch(`${BASE_URL}/dashboard/stats`, { headers: getHeaders() })),

    getKPIs: async () =>
      handleResponse(await fetch(`${BASE_URL}/dashboard/kpis`, { headers: getHeaders() })),

    getMonthlySales: async (limit = 12) =>
      handleResponse(await fetch(`${BASE_URL}/dashboard/monthly-sales?limit=${limit}`, { headers: getHeaders() })),

    getSupplierRanking: async (limit = 10) =>
      handleResponse(await fetch(`${BASE_URL}/dashboard/supplier-ranking?limit=${limit}`, { headers: getHeaders() })),

    getTopProducts: async (limit = 10) =>
      handleResponse(await fetch(`${BASE_URL}/dashboard/top-products?limit=${limit}`, { headers: getHeaders() })),

    getLateDeliveries: async (limit = 20) =>
      handleResponse(await fetch(`${BASE_URL}/dashboard/late-deliveries?limit=${limit}`, { headers: getHeaders() })),

    getWarehousePerformance: async () =>
      handleResponse(await fetch(`${BASE_URL}/dashboard/warehouse-performance`, { headers: getHeaders() })),

    getInventoryStatus: async () =>
      handleResponse(await fetch(`${BASE_URL}/dashboard/inventory-status`, { headers: getHeaders() })),
  },

  // ════════════════════════════════════════════════════════════════════
  // ANALYTICS (OLAP)
  // ════════════════════════════════════════════════════════════════════
  analytics: {
    topDelayedSuppliers: async (limit = 10) =>
      handleResponse(await fetch(`${BASE_URL}/analytics/top-delayed-suppliers?limit=${limit}`, { headers: getHeaders() })),

    highestRevenueProducts: async (limit = 10) =>
      handleResponse(await fetch(`${BASE_URL}/analytics/highest-revenue-products?limit=${limit}`, { headers: getHeaders() })),

    inventorySummary: async () =>
      handleResponse(await fetch(`${BASE_URL}/analytics/inventory-summary`, { headers: getHeaders() })),

    monthlySales: async (year?: number) =>
      handleResponse(await fetch(`${BASE_URL}/analytics/monthly-sales${year ? `?year=${year}` : ""}`, { headers: getHeaders() })),

    warehousePerformance: async () =>
      handleResponse(await fetch(`${BASE_URL}/analytics/warehouse-performance`, { headers: getHeaders() })),

    shippingPerformance: async () =>
      handleResponse(await fetch(`${BASE_URL}/analytics/shipping-performance`, { headers: getHeaders() })),

    riskSummary: async () =>
      handleResponse(await fetch(`${BASE_URL}/analytics/risk-summary`, { headers: getHeaders() })),

    supplierRanking: async () =>
      handleResponse(await fetch(`${BASE_URL}/analytics/supplier-ranking`, { headers: getHeaders() })),
  },

  // ════════════════════════════════════════════════════════════════════
  // SUPPLIERS
  // ════════════════════════════════════════════════════════════════════
  suppliers: {
    list: async () =>
      handleResponse(await fetch(`${BASE_URL}/suppliers`, { headers: getHeaders() })),

    get: async (id: number) =>
      handleResponse(await fetch(`${BASE_URL}/suppliers/${id}`, { headers: getHeaders() })),

    create: async (payload: { supplier_id?: number; name: string; email?: string; phone?: string; rating?: number; status?: string }) =>
      handleResponse(await fetch(`${BASE_URL}/suppliers`, {
        method: "POST", headers: getHeaders(), body: JSON.stringify(payload),
      })),

    update: async (id: number, payload: Partial<{ name: string; email: string; phone: string; rating: number; status: string }>) =>
      handleResponse(await fetch(`${BASE_URL}/suppliers/${id}`, {
        method: "PUT", headers: getHeaders(), body: JSON.stringify(payload),
      })),

    delete: async (id: number) =>
      handleResponse(await fetch(`${BASE_URL}/suppliers/${id}`, {
        method: "DELETE", headers: getHeaders(),
      })),

    performance: async () =>
      handleResponse(await fetch(`${BASE_URL}/suppliers/performance`, { headers: getHeaders() })),
  },

  // ════════════════════════════════════════════════════════════════════
  // PRODUCTS
  // ════════════════════════════════════════════════════════════════════
  products: {
    list: async () =>
      handleResponse(await fetch(`${BASE_URL}/products`, { headers: getHeaders() })),

    get: async (id: number) =>
      handleResponse(await fetch(`${BASE_URL}/products/${id}`, { headers: getHeaders() })),

    create: async (payload: { product_id?: number; category_id?: number; category_name?: string; product_name: string; product_price: number; description?: string }) =>
      handleResponse(await fetch(`${BASE_URL}/products`, {
        method: "POST", headers: getHeaders(), body: JSON.stringify(payload),
      })),

    update: async (id: number, payload: Partial<{ product_name: string; product_price: number; category_name: string; description: string }>) =>
      handleResponse(await fetch(`${BASE_URL}/products/${id}`, {
        method: "PUT", headers: getHeaders(), body: JSON.stringify(payload),
      })),

    delete: async (id: number) =>
      handleResponse(await fetch(`${BASE_URL}/products/${id}`, {
        method: "DELETE", headers: getHeaders(),
      })),

    highRisk: async () =>
      handleResponse(await fetch(`${BASE_URL}/products/high-risk`, { headers: getHeaders() })),
  },

  // ════════════════════════════════════════════════════════════════════
  // INVENTORY
  // ════════════════════════════════════════════════════════════════════
  inventory: {
    list: async () =>
      handleResponse(await fetch(`${BASE_URL}/inventory`, { headers: getHeaders() })),

    update: async (id: number, payload: Partial<{ stock_level: number; reorder_point: number; safety_stock: number; lead_time_days: number }>) =>
      handleResponse(await fetch(`${BASE_URL}/inventory/${id}`, {
        method: "PUT", headers: getHeaders(), body: JSON.stringify(payload),
      })),

    replenishAlerts: async () =>
      handleResponse(await fetch(`${BASE_URL}/inventory/replenish`, { headers: getHeaders() })),
  },

  // ════════════════════════════════════════════════════════════════════
  // ORDERS
  // ════════════════════════════════════════════════════════════════════
  orders: {
    list: async () =>
      handleResponse(await fetch(`${BASE_URL}/orders`, { headers: getHeaders() })),

    get: async (id: number) =>
      handleResponse(await fetch(`${BASE_URL}/orders/${id}`, { headers: getHeaders() })),

    create: async (payload: {
      order_id?: number; customer_id: number; product_id: number; quantity?: number;
      sales: number; profit?: number; order_status?: string; payment_type?: string;
      shipping_mode?: string; days_shipment_scheduled?: number;
    }) =>
      handleResponse(await fetch(`${BASE_URL}/orders`, {
        method: "POST", headers: getHeaders(), body: JSON.stringify(payload),
      })),

    update: async (id: number, payload: { order_status: string }) =>
      handleResponse(await fetch(`${BASE_URL}/orders/${id}`, {
        method: "PUT", headers: getHeaders(), body: JSON.stringify(payload),
      })),

    delete: async (id: number) =>
      handleResponse(await fetch(`${BASE_URL}/orders/${id}`, {
        method: "DELETE", headers: getHeaders(),
      })),
  },

  // ════════════════════════════════════════════════════════════════════
  // SHIPMENTS
  // ════════════════════════════════════════════════════════════════════
  shipments: {
    list: async () =>
      handleResponse(await fetch(`${BASE_URL}/shipments`, { headers: getHeaders() })),

    get: async (id: number) =>
      handleResponse(await fetch(`${BASE_URL}/shipments/${id}`, { headers: getHeaders() })),

    updateTracking: async (id: number, payload: { days_shipping_real: number; delivery_status?: string }) =>
      handleResponse(await fetch(`${BASE_URL}/shipments/${id}`, {
        method: "PUT", headers: getHeaders(), body: JSON.stringify(payload),
      })),
  },

  // ════════════════════════════════════════════════════════════════════
  // WAREHOUSES
  // ════════════════════════════════════════════════════════════════════
  warehouses: {
    list: async () =>
      handleResponse(await fetch(`${BASE_URL}/warehouses`, { headers: getHeaders() })),

    get: async (id: number) =>
      handleResponse(await fetch(`${BASE_URL}/warehouses/${id}`, { headers: getHeaders() })),

    olap_summary: async () =>
      handleResponse(await fetch(`${BASE_URL}/warehouses/olap/summary`, { headers: getHeaders() })),
  },

  // ════════════════════════════════════════════════════════════════════
  // RISK ANALYSIS + ML
  // ════════════════════════════════════════════════════════════════════
  risk: {
    summary: async () =>
      handleResponse(await fetch(`${BASE_URL}/risk/summary`, { headers: getHeaders() })),

    suppliers: async () =>
      handleResponse(await fetch(`${BASE_URL}/risk/suppliers`, { headers: getHeaders() })),

    deliveryDelays: async () =>
      handleResponse(await fetch(`${BASE_URL}/risk/delivery-delays`, { headers: getHeaders() })),

    inventoryShortage: async () =>
      handleResponse(await fetch(`${BASE_URL}/risk/inventory-shortage`, { headers: getHeaders() })),

    shippingPerformance: async () =>
      handleResponse(await fetch(`${BASE_URL}/risk/shipping-performance`, { headers: getHeaders() })),

    warehousePerformance: async () =>
      handleResponse(await fetch(`${BASE_URL}/risk/warehouse-performance`, { headers: getHeaders() })),

    predict: async (payload: {
      days_shipment_scheduled: number; shipping_mode: string; customer_segment: string;
      category_name: string; product_price: number; sales: number; discount_rate: number;
    }) =>
      handleResponse(await fetch(`${BASE_URL}/risk/predict`, {
        method: "POST", headers: getHeaders(), body: JSON.stringify(payload),
      })),

    modelInfo: async () =>
      handleResponse(await fetch(`${BASE_URL}/risk/model-info`, { headers: getHeaders() })),

    retrainModel: async () =>
      handleResponse(await fetch(`${BASE_URL}/risk/train`, {
        method: "POST", headers: getHeaders(),
      })),
  },

  // ════════════════════════════════════════════════════════════════════
  // OPTIMIZATION ENGINE
  // ════════════════════════════════════════════════════════════════════
  optimization: {
    suppliers: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/suppliers`, { headers: getHeaders() })),

    warehouses: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/warehouses`, { headers: getHeaders() })),

    shippingMethod: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/shipping-method`, { headers: getHeaders() })),

    delayedDeliveries: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/delayed-deliveries`, { headers: getHeaders() })),

    replenish: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/replenish`, { headers: getHeaders() })),

    highRiskShipments: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/high-risk-shipments`, { headers: getHeaders() })),

    costReduction: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/cost-reduction`, { headers: getHeaders() })),

    delivery: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/delivery`, { headers: getHeaders() })),

    transportation: async () =>
      handleResponse(await fetch(`${BASE_URL}/optimization/transportation`, { headers: getHeaders() })),
  },

  // ════════════════════════════════════════════════════════════════════
  // REPORTS
  // ════════════════════════════════════════════════════════════════════
  reports: {
    downloadPdf: () => {
      const token = localStorage.getItem("sc_token");
      const url = `${BASE_URL}/reports/pdf${token ? `?token=${token}` : ""}`;
      window.open(url, "_blank");
    },

    downloadExcel: () => {
      const token = localStorage.getItem("sc_token");
      const url = `${BASE_URL}/reports/excel${token ? `?token=${token}` : ""}`;
      window.open(url, "_blank");
    },

    downloadRiskSummaryPdf: () => {
      const token = localStorage.getItem("sc_token");
      window.open(`${BASE_URL}/reports/risk-summary${token ? `?token=${token}` : ""}`, "_blank");
    },

    downloadSupplierExcel: () => {
      const token = localStorage.getItem("sc_token");
      window.open(`${BASE_URL}/reports/supplier-performance${token ? `?token=${token}` : ""}`, "_blank");
    },

    downloadMonthly: (year: number, month: number) => {
      const token = localStorage.getItem("sc_token");
      window.open(`${BASE_URL}/reports/monthly?year=${year}&month=${month}${token ? `&token=${token}` : ""}`, "_blank");
    },

    downloadYearly: (year: number) => {
      const token = localStorage.getItem("sc_token");
      window.open(`${BASE_URL}/reports/yearly?year=${year}${token ? `&token=${token}` : ""}`, "_blank");
    },
  },

  // ════════════════════════════════════════════════════════════════════
  // ETL PIPELINE
  // ════════════════════════════════════════════════════════════════════
  etl: {
    run: async () =>
      handleResponse(await fetch(`${BASE_URL}/etl/run`, {
        method: "POST", headers: getHeaders(),
      })),

    status: async () =>
      handleResponse(await fetch(`${BASE_URL}/etl/status`, { headers: getHeaders() })),

    logs: async (limit = 20) =>
      handleResponse(await fetch(`${BASE_URL}/etl/logs?limit=${limit}`, { headers: getHeaders() })),

    generateData: async (num_records = 18500) =>
      handleResponse(await fetch(`${BASE_URL}/etl/generate-data`, {
        method: "POST", headers: getHeaders(), body: JSON.stringify({ num_records }),
      })),
  },

  // ════════════════════════════════════════════════════════════════════
  // MONTE CARLO SIMULATION
  // ════════════════════════════════════════════════════════════════════
  monteCarlo: {
    run: async () =>
      handleResponse(await fetch(`${BASE_URL}/monte-carlo/run`, {
        method: "POST", headers: getHeaders(),
      })),

    results: async () =>
      handleResponse(await fetch(`${BASE_URL}/monte-carlo/results`, { headers: getHeaders() })),

    graphUrl: (filename: string) => `${BASE_URL}/monte-carlo/graph/${filename}`,
  },
};
