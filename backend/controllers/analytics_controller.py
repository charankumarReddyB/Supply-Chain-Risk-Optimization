"""
controllers/analytics_controller.py
Business logic for all advanced OLAP analytics queries.
"""

import logging
from backend.models.database import execute_query

logger = logging.getLogger(__name__)


class AnalyticsController:

    @staticmethod
    def get_top_delayed_suppliers(limit: int = 10) -> list:
        """Top suppliers by average delivery delay."""
        try:
            return execute_query(f"""
                SELECT
                    s.Supplier_ID,
                    s.Supplier_Name,
                    s.Supplier_Rating,
                    COUNT(f.Fact_ID)                      AS Total_Orders,
                    ROUND(AVG(f.Delivery_Delay), 2)       AS Avg_Delay_Days,
                    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS Delayed_Orders,
                    ROUND(
                        SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) /
                        COUNT(f.Fact_ID) * 100, 2
                    ) AS Delay_Rate_Percent
                FROM dim_supplier s
                    JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
                GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating
                ORDER BY Avg_Delay_Days DESC
                LIMIT {int(limit)}
            """)
        except Exception as e:
            logger.error(f"Top delayed suppliers error: {e}")
            raise

    @staticmethod
    def get_highest_revenue_products(limit: int = 10) -> list:
        """Top products by total revenue generated."""
        try:
            return execute_query(f"""
                SELECT
                    p.Product_ID,
                    p.Product_Name,
                    p.Product_Category_Name     AS Category,
                    p.Product_Price,
                    COUNT(f.Fact_ID)             AS Total_Orders,
                    SUM(f.Quantity)              AS Units_Sold,
                    ROUND(SUM(f.Sales), 2)       AS Total_Revenue,
                    ROUND(SUM(f.Profit), 2)      AS Total_Profit,
                    ROUND(SUM(f.Profit) / SUM(f.Sales) * 100, 2) AS Profit_Margin_Pct
                FROM dim_product p
                    JOIN fact_order f ON p.Product_ID = f.Product_ID
                GROUP BY p.Product_ID, p.Product_Name, p.Product_Category_Name, p.Product_Price
                ORDER BY Total_Revenue DESC
                LIMIT {int(limit)}
            """)
        except Exception as e:
            logger.error(f"Highest revenue products error: {e}")
            raise

    @staticmethod
    def get_inventory_summary() -> list:
        """Full inventory summary with status classification."""
        try:
            return execute_query("""
                SELECT
                    p.product_id,
                    p.product_name,
                    p.category_name,
                    w.name                   AS warehouse_name,
                    i.stock_level,
                    i.reorder_point,
                    i.safety_stock,
                    i.lead_time_days,
                    CASE
                        WHEN i.stock_level <= i.safety_stock  THEN 'CRITICAL'
                        WHEN i.stock_level <= i.reorder_point THEN 'WARNING'
                        ELSE 'OK'
                    END AS status
                FROM inventory i
                    JOIN products p   ON i.product_id   = p.product_id
                    JOIN warehouses w ON i.warehouse_id = w.warehouse_id
                ORDER BY i.stock_level ASC
            """)
        except Exception as e:
            logger.error(f"Inventory summary error: {e}")
            raise

    @staticmethod
    def get_monthly_sales_trend(year: int = None) -> list:
        """Monthly sales and profit trend, optionally filtered by year."""
        try:
            year_filter = f"WHERE d.Year = {int(year)}" if year else ""
            return execute_query(f"""
                SELECT
                    d.Year,
                    d.Month,
                    d.Month_Name,
                    d.Quarter,
                    COUNT(DISTINCT f.Order_ID)   AS Total_Orders,
                    ROUND(SUM(f.Sales), 2)        AS Monthly_Revenue,
                    ROUND(SUM(f.Profit), 2)       AS Monthly_Profit
                FROM fact_order f
                    JOIN dim_date d ON f.Date_ID = d.Date_ID
                {year_filter}
                GROUP BY d.Year, d.Month, d.Month_Name, d.Quarter
                ORDER BY d.Year ASC, d.Month ASC
            """)
        except Exception as e:
            logger.error(f"Monthly sales trend error: {e}")
            raise

    @staticmethod
    def get_warehouse_performance() -> list:
        """Performance analytics per warehouse."""
        try:
            return execute_query("""
                SELECT
                    w.Warehouse_ID,
                    w.Warehouse_Name,
                    w.Warehouse_City,
                    w.Warehouse_State,
                    w.Warehouse_Capacity,
                    COUNT(f.Fact_ID)               AS Total_Orders,
                    SUM(f.Quantity)                AS Total_Units,
                    ROUND(SUM(f.Sales), 2)         AS Total_Revenue,
                    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay,
                    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS Delayed_Orders,
                    ROUND(
                        SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) /
                        COUNT(f.Fact_ID) * 100, 2
                    ) AS Delay_Rate_Pct,
                    SUM(CASE WHEN f.Risk_Level = 'High'   THEN 1 ELSE 0 END) AS High_Risk,
                    SUM(CASE WHEN f.Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS Med_Risk,
                    SUM(CASE WHEN f.Risk_Level = 'Low'    THEN 1 ELSE 0 END) AS Low_Risk
                FROM dim_warehouse w
                    JOIN fact_order f ON w.Warehouse_ID = f.Warehouse_ID
                GROUP BY w.Warehouse_ID, w.Warehouse_Name, w.Warehouse_City,
                         w.Warehouse_State, w.Warehouse_Capacity
                ORDER BY Total_Orders DESC
            """)
        except Exception as e:
            logger.error(f"Warehouse performance analytics error: {e}")
            raise

    @staticmethod
    def get_shipping_performance() -> list:
        """Delivery and delay analytics per shipping mode."""
        try:
            return execute_query("""
                SELECT
                    sh.Shipping_Mode,
                    COUNT(f.Fact_ID)                   AS Total_Shipments,
                    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS Delayed,
                    ROUND(AVG(f.Delivery_Delay), 2)    AS Avg_Delay_Days,
                    ROUND(
                        SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) /
                        COUNT(f.Fact_ID) * 100, 2
                    )                                  AS Delay_Rate_Pct,
                    ROUND(SUM(f.Sales), 2)             AS Total_Revenue,
                    ROUND(SUM(f.Profit), 2)            AS Total_Profit
                FROM fact_order f
                    JOIN dim_shipping sh ON f.Shipping_ID = sh.Shipping_ID
                GROUP BY sh.Shipping_Mode
                ORDER BY Delay_Rate_Pct DESC
            """)
        except Exception as e:
            logger.error(f"Shipping performance analytics error: {e}")
            raise

    @staticmethod
    def get_risk_summary() -> list:
        """Risk distribution summary across all orders."""
        try:
            return execute_query("""
                SELECT
                    f.Risk_Level,
                    COUNT(*) AS Count,
                    ROUND(SUM(f.Sales), 2) AS Total_Revenue,
                    ROUND(SUM(f.Profit), 2) AS Total_Profit,
                    ROUND(AVG(f.Delivery_Delay), 2) AS Avg_Delay,
                    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_order), 2) AS Percentage
                FROM fact_order f
                GROUP BY f.Risk_Level
                ORDER BY CASE f.Risk_Level WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 WHEN 'Low' THEN 3 ELSE 4 END
            """)
        except Exception as e:
            logger.error(f"Risk summary error: {e}")
            raise

    @staticmethod
    def get_supplier_ranking() -> list:
        """Full supplier ranking with composite performance score."""
        try:
            suppliers = execute_query("""
                SELECT
                    s.Supplier_ID                      AS "Supplier_ID",
                    s.Supplier_Name                    AS "Supplier_Name",
                    s.Supplier_Rating                  AS "Supplier_Rating",
                    s.Supplier_Status                  AS "Supplier_Status",
                    COUNT(f.Fact_ID)                   AS "Total_Orders",
                    ROUND(SUM(f.Sales), 2)             AS "Total_Revenue",
                    ROUND(AVG(f.Delivery_Delay), 2)    AS "Avg_Delay",
                    SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS "High_Risk_Orders"
                FROM dim_supplier s
                    LEFT JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
                GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating, s.Supplier_Status
            """)

            for row in suppliers:
                total = row["Total_Orders"] or 1
                high_risk_rate = (row["High_Risk_Orders"] or 0) / total
                avg_delay = float(row["Avg_Delay"]) if row["Avg_Delay"] is not None else 0.0
                rating = float(row["Supplier_Rating"]) if row["Supplier_Rating"] is not None else 0.0

                score = round(
                    (rating / 5.0) * 50 -
                    (avg_delay / 10.0) * 30 -
                    high_risk_rate * 20,
                    4
                )
                row["Composite_Score"] = score

            return sorted(suppliers, key=lambda x: x["Composite_Score"], reverse=True)

        except Exception as e:
            logger.error(f"Supplier ranking error: {e}")
            raise

    @staticmethod
    def get_cost_by_category() -> list:
        """Cost by category: Sales - Profit."""
        try:
            return execute_query("""
                SELECT 
                    p.Product_Category_Name AS category, 
                    ROUND(SUM(f.Sales - f.Profit), 2) AS total_cost,
                    'INR' as currency
                FROM fact_order f 
                JOIN dim_product p ON f.Product_ID = p.Product_ID
                GROUP BY p.Product_Category_Name
                ORDER BY total_cost DESC
            """)
        except Exception as e:
            logger.error(f"Cost by category query error: {e}")
            raise

    @staticmethod
    def get_cost_by_region() -> list:
        """Cost by region: Sales - Profit."""
        try:
            return execute_query("""
                SELECT 
                    w.Warehouse_City AS region, 
                    ROUND(SUM(f.Sales - f.Profit), 2) AS total_cost,
                    'INR' as currency
                FROM fact_order f 
                JOIN dim_warehouse w ON f.Warehouse_ID = w.Warehouse_ID
                GROUP BY w.Warehouse_City
                ORDER BY total_cost DESC
            """)
        except Exception as e:
            logger.error(f"Cost by region query error: {e}")
            raise
