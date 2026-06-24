-- ============================================================================
-- Supply Chain Risk Optimization
-- Complete Analytics SQL Queries (OLAP Star Schema)
-- ============================================================================

USE supply_chain_db;

-- ============================================================================
-- 1. TOP DELAYED SUPPLIERS
-- Measures supplier reliability by average delivery delay days.
-- ============================================================================
SELECT
    s.Supplier_Name,
    s.Supplier_Rating,
    COUNT(f.Fact_ID)                AS Total_Orders,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delivery_Delay_Days,
    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS Delayed_Orders,
    ROUND(
        SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) / COUNT(f.Fact_ID) * 100,
        2
    ) AS Delay_Rate_Percent
FROM dim_supplier s
    JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
GROUP BY
    s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating
ORDER BY Avg_Delivery_Delay_Days DESC;


-- ============================================================================
-- 2. MONTHLY SALES & PROFIT TREND
-- Provides month-over-month sales and profit performance.
-- ============================================================================
SELECT
    d.Year,
    d.Month,
    d.Month_Name,
    d.Quarter,
    COUNT(DISTINCT f.Order_ID)   AS Total_Orders,
    SUM(f.Quantity)              AS Total_Units_Sold,
    ROUND(SUM(f.Sales), 2)       AS Monthly_Revenue,
    ROUND(SUM(f.Profit), 2)      AS Monthly_Profit,
    ROUND(SUM(f.Profit) / SUM(f.Sales) * 100, 2) AS Profit_Margin_Percent
FROM fact_order f
    JOIN dim_date d ON f.Date_ID = d.Date_ID
GROUP BY
    d.Year, d.Month, d.Month_Name, d.Quarter
ORDER BY d.Year ASC, d.Month ASC;


-- ============================================================================
-- 3. YEARLY SALES & PROFIT SUMMARY
-- Annual performance overview.
-- ============================================================================
SELECT
    d.Year,
    COUNT(DISTINCT f.Order_ID)   AS Total_Orders,
    SUM(f.Quantity)              AS Total_Units_Sold,
    ROUND(SUM(f.Sales), 2)       AS Annual_Revenue,
    ROUND(SUM(f.Profit), 2)      AS Annual_Profit,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delivery_Delay,
    SUM(CASE WHEN f.Risk_Level = 'High'   THEN 1 ELSE 0 END) AS High_Risk_Count,
    SUM(CASE WHEN f.Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS Med_Risk_Count,
    SUM(CASE WHEN f.Risk_Level = 'Low'    THEN 1 ELSE 0 END) AS Low_Risk_Count
FROM fact_order f
    JOIN dim_date d ON f.Date_ID = d.Date_ID
GROUP BY d.Year
ORDER BY d.Year ASC;


-- ============================================================================
-- 4. INVENTORY LEVELS & STOCKOUT RISK
-- Identifies products below safety stock or reorder point.
-- ============================================================================
SELECT
    p.product_id,
    p.product_name,
    w.name                    AS Warehouse_Name,
    i.stock_level,
    i.reorder_point,
    i.safety_stock,
    i.lead_time_days,
    (i.reorder_point + i.safety_stock - i.stock_level) AS Recommended_Reorder_Qty,
    CASE
        WHEN i.stock_level <= i.safety_stock  THEN 'CRITICAL (Below Safety Stock)'
        WHEN i.stock_level <= i.reorder_point THEN 'WARNING (Below Reorder Point)'
        ELSE 'OK'
    END AS Inventory_Status
FROM inventory i
    JOIN products p ON i.product_id = p.product_id
    JOIN warehouses w ON i.warehouse_id = w.warehouse_id
ORDER BY i.stock_level ASC;


-- ============================================================================
-- 5. REVENUE ANALYSIS BY CUSTOMER SEGMENT
-- Breaks down sales performance across business segments.
-- ============================================================================
SELECT
    c.Customer_Segment,
    COUNT(DISTINCT f.Order_ID)   AS Total_Orders,
    ROUND(SUM(f.Sales), 2)       AS Total_Revenue,
    ROUND(SUM(f.Profit), 2)      AS Total_Profit,
    ROUND(SUM(f.Profit) / SUM(f.Sales) * 100, 2) AS Profit_Margin_Percent,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay_Days
FROM fact_order f
    JOIN dim_customer c ON f.Customer_ID = c.Customer_ID
GROUP BY c.Customer_Segment
ORDER BY Total_Revenue DESC;


-- ============================================================================
-- 6. DELIVERY PERFORMANCE BY SHIPPING MODE
-- Analyzes late vs. on-time deliveries per shipping service class.
-- ============================================================================
SELECT
    s.Shipping_Mode,
    COUNT(f.Fact_ID)            AS Total_Shipments,
    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS Delayed_Shipments,
    ROUND(
        SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) / COUNT(f.Fact_ID) * 100,
        2
    )                           AS Delay_Rate_Percent,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay_Days,
    ROUND(SUM(f.Sales), 2)      AS Total_Revenue
FROM fact_order f
    JOIN dim_shipping s ON f.Shipping_ID = s.Shipping_ID
GROUP BY s.Shipping_Mode
ORDER BY Delay_Rate_Percent DESC;


-- ============================================================================
-- 7. HIGH-RISK ORDERS LIST
-- Extracts transactions with high delivery delays and negative profit.
-- ============================================================================
SELECT
    f.Order_ID,
    c.Customer_Fname,
    c.Customer_Lname,
    c.Customer_Segment,
    p.Product_Name,
    p.Product_Category_Name,
    s.Shipping_Mode,
    f.Sales,
    f.Profit,
    f.Delivery_Delay  AS Delay_Days,
    f.Risk_Level,
    d.Full_Date       AS Order_Date
FROM fact_order f
    JOIN dim_customer c  ON f.Customer_ID  = c.Customer_ID
    JOIN dim_product p   ON f.Product_ID   = p.Product_ID
    JOIN dim_shipping s  ON f.Shipping_ID  = s.Shipping_ID
    JOIN dim_date d      ON f.Date_ID      = d.Date_ID
WHERE f.Risk_Level = 'High'
ORDER BY f.Profit ASC;


-- ============================================================================
-- 8. HIGHEST REVENUE PRODUCTS (TOP 20)
-- Products generating the most revenue and their risk profiles.
-- ============================================================================
SELECT
    p.Product_ID,
    p.Product_Name,
    p.Product_Category_Name,
    p.Product_Price,
    COUNT(f.Fact_ID)             AS Total_Orders,
    SUM(f.Quantity)              AS Units_Sold,
    ROUND(SUM(f.Sales), 2)       AS Total_Revenue,
    ROUND(SUM(f.Profit), 2)      AS Total_Profit,
    ROUND(SUM(f.Profit) / SUM(f.Sales) * 100, 2) AS Profit_Margin_Percent,
    SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS High_Risk_Count,
    ROUND(
        SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) / COUNT(f.Fact_ID) * 100,
        2
    ) AS Risk_Rate_Percent
FROM dim_product p
    JOIN fact_order f ON p.Product_ID = f.Product_ID
GROUP BY p.Product_ID, p.Product_Name, p.Product_Category_Name, p.Product_Price
ORDER BY Total_Revenue DESC
LIMIT 20;


-- ============================================================================
-- 9. WAREHOUSE PERFORMANCE ANALYSIS
-- Evaluates throughput, delays, and risk distribution per warehouse.
-- ============================================================================
SELECT
    w.Warehouse_ID,
    w.Warehouse_Name,
    w.Warehouse_City,
    w.Warehouse_State,
    w.Warehouse_Capacity,
    COUNT(f.Fact_ID)              AS Total_Orders_Processed,
    SUM(f.Quantity)               AS Total_Units_Shipped,
    ROUND(SUM(f.Sales), 2)        AS Total_Revenue_Generated,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delivery_Delay_Days,
    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS Delayed_Orders,
    ROUND(
        SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) / COUNT(f.Fact_ID) * 100,
        2
    ) AS Delay_Rate_Percent,
    SUM(CASE WHEN f.Risk_Level = 'High'   THEN 1 ELSE 0 END) AS High_Risk_Orders,
    SUM(CASE WHEN f.Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS Med_Risk_Orders,
    SUM(CASE WHEN f.Risk_Level = 'Low'    THEN 1 ELSE 0 END) AS Low_Risk_Orders
FROM dim_warehouse w
    JOIN fact_order f ON w.Warehouse_ID = f.Warehouse_ID
GROUP BY w.Warehouse_ID, w.Warehouse_Name, w.Warehouse_City, w.Warehouse_State, w.Warehouse_Capacity
ORDER BY Total_Orders_Processed DESC;


-- ============================================================================
-- 10. SUPPLIER RANKING (COMPOSITE SCORE)
-- Ranks suppliers by combined performance: rating + delay + revenue.
-- ============================================================================
SELECT
    s.Supplier_ID,
    s.Supplier_Name,
    s.Supplier_Rating,
    s.Supplier_Status,
    COUNT(f.Fact_ID)             AS Total_Orders,
    ROUND(SUM(f.Sales), 2)       AS Total_Revenue,
    ROUND(SUM(f.Profit), 2)      AS Total_Profit,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay_Days,
    SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS High_Risk_Orders,
    ROUND(
        (s.Supplier_Rating / 5.0) * 0.5 -
        (COALESCE(AVG(f.Delivery_Delay), 0) / 10.0) * 0.3 -
        (COALESCE(SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END), 0) / COALESCE(COUNT(f.Fact_ID), 1)) * 0.2,
        4
    ) AS Composite_Score
FROM dim_supplier s
    LEFT JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating, s.Supplier_Status
ORDER BY Composite_Score DESC;


-- ============================================================================
-- 11. RISK SUMMARY (FULL DISTRIBUTION)
-- Complete risk breakdown across all dimensions.
-- ============================================================================
SELECT
    f.Risk_Level,
    COUNT(f.Fact_ID)             AS Total_Orders,
    ROUND(SUM(f.Sales), 2)       AS Total_Revenue,
    ROUND(SUM(f.Profit), 2)      AS Total_Profit,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay_Days,
    ROUND(COUNT(f.Fact_ID) / (SELECT COUNT(*) FROM fact_order) * 100, 2) AS Percentage_Of_Total
FROM fact_order f
GROUP BY f.Risk_Level
ORDER BY FIELD(f.Risk_Level, 'High', 'Medium', 'Low');


-- ============================================================================
-- 12. LATE DELIVERIES BY SHIPPING MODE (DETAILED)
-- ============================================================================
SELECT
    sh.Shipping_Mode,
    sh.Delivery_Status,
    COUNT(f.Fact_ID)             AS Count,
    ROUND(SUM(f.Sales), 2)       AS Revenue_Impacted,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay
FROM fact_order f
    JOIN dim_shipping sh ON f.Shipping_ID = sh.Shipping_ID
WHERE f.Delivery_Delay > 0
GROUP BY sh.Shipping_Mode, sh.Delivery_Status
ORDER BY Avg_Delay DESC;


-- ============================================================================
-- 13. DASHBOARD KPI SUMMARY (Single-Row Result)
-- ============================================================================
SELECT
    COUNT(DISTINCT f.Order_ID)   AS Total_Orders,
    COUNT(DISTINCT f.Customer_ID) AS Total_Customers,
    COUNT(DISTINCT f.Supplier_ID) AS Total_Suppliers,
    COUNT(DISTINCT f.Warehouse_ID) AS Total_Warehouses,
    SUM(f.Quantity)              AS Total_Items_Sold,
    ROUND(SUM(f.Sales), 2)       AS Total_Revenue,
    ROUND(SUM(f.Profit), 2)      AS Total_Profit,
    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delivery_Delay_Days,
    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS Total_Delayed_Deliveries,
    SUM(CASE WHEN f.Risk_Level = 'High'   THEN 1 ELSE 0 END) AS High_Risk_Orders,
    SUM(CASE WHEN f.Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS Med_Risk_Orders,
    SUM(CASE WHEN f.Risk_Level = 'Low'    THEN 1 ELSE 0 END) AS Low_Risk_Orders
FROM fact_order f;