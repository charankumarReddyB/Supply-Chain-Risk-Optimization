# Supply Chain Risk Analysis — Complete API Documentation

Base URL: `http://localhost:5000`  
All protected endpoints require: `Authorization: Bearer <jwt_token>`  
Content-Type: `application/json`

---

## 1. Authentication (`/api/auth`)

### POST /api/auth/register
Register a new user.
```json
Request: { "username": "john", "email": "john@example.com", "password": "secure123", "role": "user" }
Response 201: { "message": "User registered successfully" }
Response 400: { "error": "Username or email already registered" }
```

### POST /api/auth/login
Authenticate and receive JWT token.
```json
Request: { "username": "admin", "password": "admin123" }
Response 200: { "token": "eyJ...", "user": { "id": 1, "username": "admin", "role": "admin" } }
Response 401: { "error": "Invalid credentials" }
```

### GET /api/auth/me 🔒
Returns profile of authenticated user.
```json
Response 200: { "user": { "id": 1, "username": "admin", "email": "...", "role": "admin", "created_at": "..." } }
```

### PUT /api/auth/change-password 🔒
Change the authenticated user's password.
```json
Request: { "old_password": "current", "new_password": "newSecure123" }
Response 200: { "message": "Password changed successfully" }
```

### POST /api/auth/logout 🔒
Client-side logout (JWT is stateless; client must discard token).
```json
Response 200: { "message": "Logged out successfully. Please discard your token." }
```

---

## 2. Dashboard (`/api/dashboard`)

### GET /api/dashboard/stats 🔒
Returns all dashboard KPIs, risk distribution, monthly trend, segments, and inventory status.
```json
Response 200: {
  "kpis": { "total_orders": 18000, "total_revenue": 9500000.00, "total_profit": 1200000.00,
            "total_customers": 1400, "total_suppliers": 5, "total_warehouses": 3,
            "avg_delivery_delay_days": 1.23, "delayed_deliveries": 9000,
            "high_risk_orders": 4500, "medium_risk_orders": 7000, "low_risk_orders": 6500 },
  "risk_distribution": [{ "risk_level": "High", "count": 4500, "percentage": 25.0 }, ...],
  "monthly_sales_trend": [{ "year": 2023, "month": 1, "revenue": 800000.00, ... }, ...],
  "segment_breakdown": [{ "segment": "Consumer", "revenue": 4000000.00 }, ...],
  "inventory_status": { "critical": 12, "warning": 45, "ok": 800 }
}
```

### GET /api/dashboard/kpis 🔒
Returns only KPI metrics.

### GET /api/dashboard/monthly-sales?limit=24 🔒
Returns monthly revenue and profit trend.

### GET /api/dashboard/supplier-ranking?limit=10 🔒
Returns top supplier ranking by rating and delay.

### GET /api/dashboard/top-products?limit=10 🔒
Returns top selling products by revenue.

### GET /api/dashboard/late-deliveries?limit=20 🔒
Returns most delayed shipments with context.

### GET /api/dashboard/warehouse-performance 🔒
Returns performance metrics per warehouse.

### GET /api/dashboard/inventory-status 🔒
Returns inventory health: CRITICAL / WARNING / OK counts.

---

## 3. Analytics (OLAP) (`/api/analytics`)

### GET /api/analytics/top-delayed-suppliers?limit=10 🔒
Returns top suppliers by average delivery delay.

### GET /api/analytics/highest-revenue-products?limit=10 🔒
Returns products ranked by total revenue.

### GET /api/analytics/inventory-summary 🔒
Returns all inventory with status classification (CRITICAL/WARNING/OK).

### GET /api/analytics/monthly-sales?year=2023 🔒
Returns monthly sales trend, optionally filtered by year.

### GET /api/analytics/warehouse-performance 🔒
Returns full warehouse throughput, delay, and risk analytics.

### GET /api/analytics/shipping-performance 🔒
Returns delay rate, avg delay, and revenue by shipping mode.

### GET /api/analytics/risk-summary 🔒
Returns High/Medium/Low risk distribution with revenue and profit.

### GET /api/analytics/supplier-ranking 🔒
Returns all suppliers ranked by composite performance score.

---

## 4. Suppliers (`/api/suppliers`)

### GET /api/suppliers 🔒
Returns all suppliers.

### GET /api/suppliers/<id> 🔒
Returns a single supplier.

### POST /api/suppliers 🔒
```json
Request: { "supplier_id": 6, "name": "New Supplier", "email": "...", "phone": "...", "rating": 4.5, "status": "Active" }
Response 201: { "message": "Supplier created successfully" }
```

### PUT /api/suppliers/<id> 🔒
Update supplier fields (name, email, phone, rating, status).

### DELETE /api/suppliers/<id> 🔒
Delete a supplier and its dim_supplier record.

### GET /api/suppliers/performance 🔒
Returns supplier analytics: total orders, avg delay, high-risk count.

---

## 5. Products (`/api/products`)

### GET /api/products 🔒 | GET /api/products/<id> 🔒
List all or get single product.

### POST /api/products 🔒
```json
Request: { "product_id": 99, "category_id": 10, "category_name": "Electronics", "product_name": "Widget X", "product_price": 99.99 }
```

### PUT /api/products/<id> 🔒 | DELETE /api/products/<id> 🔒
Update or delete product (syncs OLTP + OLAP).

### GET /api/products/high-risk 🔒
Returns products with high risk rate percentages.

---

## 6. Inventory (`/api/inventory`)

### GET /api/inventory 🔒
Returns all inventory items with product and warehouse details.

### PUT /api/inventory/<inventory_id> 🔒
```json
Request: { "stock_level": 500, "reorder_point": 100, "safety_stock": 20, "lead_time_days": 5 }
```

### GET /api/inventory/replenish 🔒
Returns items below reorder point with urgency and recommended quantities.

---

## 7. Orders (`/api/orders`)

### GET /api/orders 🔒
Returns latest 100 orders with customer and product details.

### GET /api/orders/<order_id> 🔒
Returns a single order with attached shipment info.

### POST /api/orders 🔒
```json
Request: { "order_id": 99999, "customer_id": 1, "product_id": 100, "quantity": 2, "sales": 199.98, "profit": 50.00, "payment_type": "DEBIT" }
Response 201: { "message": "Order created successfully", "order_id": 99999 }
```
Creates order in OLTP and OLAP (fact_order), decrements inventory.

### PUT /api/orders/<order_id> 🔒
```json
Request: { "order_status": "COMPLETE" }
```

### DELETE /api/orders/<order_id> 🔒
Deletes order (cascades to shipment).

---

## 8. Shipments (`/api/shipments`)

### GET /api/shipments 🔒 | GET /api/shipments/<id> 🔒
List or get shipments.

### PUT /api/shipments/<id> 🔒
Update real shipping days and sync with OLAP fact_order.
```json
Request: { "days_shipping_real": 6, "delivery_status": "Late delivery" }
Response 200: { "message": "...", "late_risk": 1, "risk_level": "Medium" }
```

---

## 9. Warehouses (`/api/warehouses`)

### GET /api/warehouses 🔒 | GET /api/warehouses/<id> 🔒
List or get warehouses (with inventory).

### POST /api/warehouses 🔒
```json
Request: { "warehouse_id": 4, "name": "South Hub", "city": "Dallas", "state": "TX", "country": "USA", "capacity": 45000, "manager": "Jane Doe" }
```

### PUT /api/warehouses/<id> 🔒 | DELETE /api/warehouses/<id> 🔒
Update or delete warehouse (syncs OLTP + dim_warehouse).

### GET /api/warehouses/olap/summary 🔒
Returns row counts for all star schema tables.

### DELETE /api/warehouses/olap/clear 🔒
Truncates all OLAP fact and dimension tables.

---

## 10. Risk Analysis (`/api/risk`)

### GET /api/risk/summary 🔒
Overall consolidated risk summary.

### GET /api/risk/suppliers 🔒
Supplier risk scores with delay rates and risk categories.

### GET /api/risk/delivery-delays 🔒
Delay stats by shipping mode + critical late shipments.

### GET /api/risk/inventory-shortage 🔒
Products at CRITICAL or WARNING inventory risk.

### GET /api/risk/shipping-performance 🔒
Shipping mode risk assessment.

### GET /api/risk/warehouse-performance 🔒
Warehouse-level risk scores and delay analysis.

### POST /api/risk/predict 🔒
ML-based risk prediction for a given order.
```json
Request: {
  "days_shipment_scheduled": 4,
  "shipping_mode": "Standard Class",
  "customer_segment": "Consumer",
  "category_name": "Cleats",
  "product_price": 89.99,
  "sales": 89.99,
  "discount_rate": 0.0
}
Response 200: { "prediction": "Low", "probabilities": { "High": 0.12, "Low": 0.75, "Medium": 0.13 } }
```

### GET /api/risk/model-info 🔒
Returns trained model metrics (accuracy, precision, recall, F1, confusion matrix, feature importance).

### POST /api/risk/train 🔒
Retrains the Decision Tree classifier and returns new metrics.

---

## 11. Optimization Engine (`/api/optimization`)

### GET /api/optimization/suppliers 🔒
Best supplier recommendations with priority tiers.

### GET /api/optimization/warehouses 🔒
Best warehouse recommendations by on-time rate and throughput.

### GET /api/optimization/shipping-method 🔒
Best shipping mode recommendations by on-time performance.

### GET /api/optimization/delayed-deliveries 🔒
Top 50 most delayed OLTP shipments.

### GET /api/optimization/replenish 🔒
Inventory reorder recommendations with urgency and cost estimates.

### GET /api/optimization/high-risk-shipments 🔒
Top 50 highest-risk orders from OLAP fact table.

### GET /api/optimization/cost-reduction 🔒
Orders with negative profit + actionable cost reduction insights.

### GET /api/optimization/delivery 🔒
Delivery performance analysis with improvement suggestions.

### GET /api/optimization/transportation 🔒
Shipping mode comparison with transportation improvement recommendations.

---

## 12. Reports (`/api/reports`)

### GET /api/reports/pdf 🔒
Downloads comprehensive PDF risk analysis report.

### GET /api/reports/excel 🔒
Downloads multi-sheet Excel: Summary, Supplier Performance, Inventory, High Risk Orders.

### GET /api/reports/risk-summary 🔒
Downloads focused risk distribution PDF.

### GET /api/reports/supplier-performance 🔒
Downloads supplier performance Excel report.

### GET /api/reports/monthly?year=2023&month=5 🔒
Downloads monthly performance Excel report.

### GET /api/reports/yearly?year=2023 🔒
Downloads yearly summary Excel with top products.

---

## 13. ETL Pipeline (`/api/etl`)

### POST /api/etl/run 🔒
Triggers the ETL pipeline asynchronously (background thread).
```json
Response 202: { "message": "ETL pipeline started." }
Response 409: { "message": "ETL pipeline is already running" }
```

### GET /api/etl/status 🔒
Returns whether ETL is running and the last result.
```json
Response 200: { "running": false, "last_result": { "status": "SUCCESS", "duration": 45.2 } }
```

### GET /api/etl/logs?limit=20 🔒
Returns ETL execution history from the database.

### POST /api/etl/generate-data 🔒
Generates the mock DataCo CSV dataset.
```json
Request: { "num_records": 18500 }
Response 200: { "message": "Generated 18500 records in dataset CSV" }
```

---

## 14. Monte Carlo Simulation (`/api/monte-carlo`)

### POST /api/monte-carlo/run 🔒
Runs all 4 Monte Carlo simulations (10,000 iterations each).
```json
Response 200: {
  "timestamp": "2024-01-15T10:30:00",
  "total_simulations_per_scenario": 10000,
  "delivery_delay": {
    "delay_probability": 0.5482,
    "delay_probability_percent": 54.82,
    "average_simulated_delay_days": 1.23,
    "p95_delay_days": 4.8,
    "graph_url": "/api/monte-carlo/graph/delivery_delay.png"
  },
  "inventory_stockout": { "stockout_probability": 0.2341, ... },
  "supplier_failure": { "overall_at_least_one_supplier_failure_probability": 0.8901, ... },
  "transportation_delay": { "shipping_mode_results": [...], ... }
}
```

### GET /api/monte-carlo/results 🔒
Returns the last cached Monte Carlo simulation results.

### GET /api/monte-carlo/graph/<filename>
Serves a simulation distribution graph PNG (no auth required).
- `delivery_delay.png`
- `inventory_stockout.png`
- `supplier_failure.png`
- `transportation_delay.png`

---

## Error Responses

| Code | Meaning |
|---|---|
| 400 | Bad Request – missing or invalid fields |
| 401 | Unauthorized – missing/expired JWT token |
| 403 | Forbidden – insufficient role |
| 404 | Not Found – resource doesn't exist |
| 409 | Conflict – duplicate resource or process already running |
| 415 | Unsupported Media Type – not application/json |
| 500 | Internal Server Error – unexpected exception |

All errors return: `{ "error": "description" }`
