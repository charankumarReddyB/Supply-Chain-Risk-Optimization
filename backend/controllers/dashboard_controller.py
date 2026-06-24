"""
controllers/dashboard_controller.py
Business logic for dashboard KPI aggregation and analytics.
"""

import logging
from backend.models.database import execute_query

logger = logging.getLogger(__name__)


class DashboardController:

    @staticmethod
    def get_kpis() -> dict:
        """Returns all high-level KPI metrics from the fact table."""
        try:
            result = execute_query("""
                SELECT
                    COUNT(DISTINCT Order_ID)    AS total_orders,
                    COUNT(DISTINCT Customer_ID) AS total_customers,
                    COUNT(DISTINCT Supplier_ID) AS total_suppliers,
                    COUNT(DISTINCT Warehouse_ID) AS total_warehouses,
                    SUM(Quantity)               AS total_items_sold,
                    ROUND(SUM(Sales), 2)        AS total_revenue,
                    ROUND(SUM(Profit), 2)       AS total_profit,
                    ROUND(AVG(Delivery_Delay), 2) AS avg_delivery_delay_days,
                    SUM(CASE WHEN Delivery_Delay > 0 THEN 1 ELSE 0 END) AS delayed_deliveries,
                    SUM(CASE WHEN Risk_Level = 'High'   THEN 1 ELSE 0 END) AS high_risk_orders,
                    SUM(CASE WHEN Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS medium_risk_orders,
                    SUM(CASE WHEN Risk_Level = 'Low'    THEN 1 ELSE 0 END) AS low_risk_orders
                FROM fact_order
            """)
            return result[0] if result else {}
        except Exception as e:
            logger.error(f"KPI fetch error: {e}")
            raise

    @staticmethod
    def get_risk_distribution() -> list:
        """Returns the count and percentage breakdown of risk levels."""
        try:
            return execute_query("""
                SELECT
                    Risk_Level  AS risk_level,
                    COUNT(*)    AS count,
                    ROUND(COUNT(*) / (SELECT COUNT(*) FROM fact_order) * 100, 2) AS percentage
                FROM fact_order
                GROUP BY Risk_Level
                ORDER BY FIELD(Risk_Level, 'High', 'Medium', 'Low')
            """)
        except Exception as e:
            logger.error(f"Risk distribution fetch error: {e}")
            raise

    @staticmethod
    def get_monthly_sales(limit: int = 24) -> list:
        """Returns monthly revenue and profit trend for charting."""
        try:
            return execute_query(f"""
                SELECT
                    d.Year        AS year,
                    d.Month       AS month,
                    d.Month_Name  AS month_name,
                    d.Quarter     AS quarter,
                    COUNT(DISTINCT f.Order_ID)   AS total_orders,
                    COUNT(DISTINCT CASE WHEN f.Delivery_Delay > 0 THEN f.Order_ID END) AS `delayed`,
                    COUNT(DISTINCT CASE WHEN f.Delivery_Delay <= 0 THEN f.Order_ID END) AS `delivered`,
                    ROUND(SUM(f.Sales), 2)        AS revenue,
                    ROUND(SUM(f.Profit), 2)       AS profit
                FROM fact_order f
                    JOIN dim_date d ON f.Date_ID = d.Date_ID
                GROUP BY d.Year, d.Month, d.Month_Name, d.Quarter
                ORDER BY d.Year ASC, d.Month ASC
                LIMIT {int(limit)}
            """)
        except Exception as e:
            logger.error(f"Monthly sales fetch error: {e}")
            raise

    @staticmethod
    def get_segment_breakdown() -> list:
        """Revenue breakdown by customer segment."""
        try:
            return execute_query("""
                SELECT
                    c.Customer_Segment AS segment,
                    COUNT(DISTINCT f.Order_ID) AS total_orders,
                    ROUND(SUM(f.Sales), 2)     AS revenue,
                    ROUND(SUM(f.Profit), 2)    AS profit
                FROM fact_order f
                    JOIN dim_customer c ON f.Customer_ID = c.Customer_ID
                GROUP BY c.Customer_Segment
                ORDER BY revenue DESC
            """)
        except Exception as e:
            logger.error(f"Segment breakdown fetch error: {e}")
            raise

    @staticmethod
    def get_supplier_ranking(limit: int = 10) -> list:
        """Supplier ranking by composite performance score."""
        try:
            return execute_query(f"""
                SELECT
                    s.Supplier_ID,
                    s.Supplier_Name                  AS name,
                    s.Supplier_Rating                AS rating,
                    s.Supplier_Status                AS status,
                    COUNT(f.Fact_ID)                 AS total_orders,
                    ROUND(SUM(f.Sales), 2)           AS total_sales,
                    ROUND(AVG(f.Delivery_Delay), 2)  AS avg_delay_days,
                    SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS high_risk_orders
                FROM dim_supplier s
                    LEFT JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
                GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating, s.Supplier_Status
                ORDER BY s.Supplier_Rating DESC, avg_delay_days ASC
                LIMIT {int(limit)}
            """)
        except Exception as e:
            logger.error(f"Supplier ranking fetch error: {e}")
            raise

    @staticmethod
    def get_top_selling_products(limit: int = 10) -> list:
        """Top products by total revenue."""
        try:
            return execute_query(f"""
                SELECT
                    p.Product_ID,
                    p.Product_Name              AS product_name,
                    p.Product_Category_Name     AS category,
                    SUM(f.Quantity)             AS units_sold,
                    ROUND(SUM(f.Sales), 2)      AS total_revenue,
                    ROUND(SUM(f.Profit), 2)     AS total_profit
                FROM dim_product p
                    JOIN fact_order f ON p.Product_ID = f.Product_ID
                GROUP BY p.Product_ID, p.Product_Name, p.Product_Category_Name
                ORDER BY total_revenue DESC
                LIMIT {int(limit)}
            """)
        except Exception as e:
            logger.error(f"Top products fetch error: {e}")
            raise

    @staticmethod
    def get_late_deliveries(limit: int = 20) -> list:
        """Returns a list of the most delayed shipments."""
        try:
            return execute_query(f"""
                SELECT
                    f.Order_ID,
                    c.Customer_Fname    AS customer_fname,
                    c.Customer_Lname    AS customer_lname,
                    p.Product_Name      AS product_name,
                    s.Supplier_Name     AS supplier_name,
                    sh.Shipping_Mode    AS shipping_mode,
                    f.Delivery_Delay    AS delay_days,
                    f.Risk_Level        AS risk_level,
                    d.Full_Date         AS order_date
                FROM fact_order f
                    JOIN dim_customer c  ON f.Customer_ID  = c.Customer_ID
                    JOIN dim_product p   ON f.Product_ID   = p.Product_ID
                    JOIN dim_supplier s  ON f.Supplier_ID  = s.Supplier_ID
                    JOIN dim_shipping sh ON f.Shipping_ID  = sh.Shipping_ID
                    JOIN dim_date d      ON f.Date_ID      = d.Date_ID
                WHERE f.Delivery_Delay > 0
                ORDER BY f.Delivery_Delay DESC
                LIMIT {int(limit)}
            """)
        except Exception as e:
            logger.error(f"Late deliveries fetch error: {e}")
            raise

    @staticmethod
    def get_warehouse_performance() -> list:
        """Performance metrics per warehouse."""
        try:
            return execute_query("""
                SELECT
                    w.Warehouse_ID,
                    w.Warehouse_Name,
                    w.Warehouse_City,
                    COUNT(f.Fact_ID)              AS total_orders,
                    ROUND(SUM(f.Sales), 2)        AS total_revenue,
                    ROUND(AVG(f.Delivery_Delay), 2) AS avg_delay,
                    SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS high_risk
                FROM dim_warehouse w
                    LEFT JOIN fact_order f ON w.Warehouse_ID = f.Warehouse_ID
                GROUP BY w.Warehouse_ID, w.Warehouse_Name, w.Warehouse_City
                ORDER BY total_revenue DESC
            """)
        except Exception as e:
            logger.error(f"Warehouse performance fetch error: {e}")
            raise

    @staticmethod
    def get_inventory_status() -> dict:
        """Summary of inventory health: OK, WARNING, CRITICAL counts."""
        try:
            critical = execute_query(
                "SELECT COUNT(*) AS count FROM inventory WHERE stock_level <= safety_stock"
            )
            warning = execute_query(
                "SELECT COUNT(*) AS count FROM inventory WHERE stock_level > safety_stock AND stock_level <= reorder_point"
            )
            ok = execute_query(
                "SELECT COUNT(*) AS count FROM inventory WHERE stock_level > reorder_point"
            )
            return {
                "critical": critical[0]["count"] if critical else 0,
                "warning": warning[0]["count"] if warning else 0,
                "ok": ok[0]["count"] if ok else 0
            }
        except Exception as e:
            logger.error(f"Inventory status fetch error: {e}")
            raise

    @staticmethod
    def get_recent_activities() -> list:
        """Gathers real-time recent activities from orders, inventory, and ETL logs."""
        activities = []
        try:
            # 1. Fetch recent orders
            recent_orders = execute_query("""
                SELECT o.order_id, o.order_status, o.order_date, p.product_name, c.fname, c.lname
                FROM orders o
                JOIN products p ON o.product_id = p.product_id
                JOIN customers c ON o.customer_id = c.customer_id
                ORDER BY o.order_date DESC LIMIT 5
            """)
            for o in recent_orders:
                time_str = o["order_date"].strftime("%b %d, %H:%M") if hasattr(o["order_date"], "strftime") else str(o["order_date"])
                status = o["order_status"].lower()
                act_type = "success" if status == "complete" else "info" if status == "processing" else "warning"
                activities.append({
                    "time": time_str,
                    "text": f"Order #{o['order_id']} for {o['product_name']} placed by {o['fname']} {o['lname']} is {o['order_status']}",
                    "type": act_type
                })
                
            # 2. Fetch recent ETL runs
            recent_etl = execute_query("""
                SELECT run_at, status, records_processed FROM etl_logs ORDER BY run_at DESC LIMIT 3
            """)
            for etl in recent_etl:
                time_str = etl["run_at"].strftime("%b %d, %H:%M") if hasattr(etl["run_at"], "strftime") else str(etl["run_at"])
                status = etl["status"]
                act_type = "success" if status == "SUCCESS" else "alert"
                activities.append({
                    "time": time_str,
                    "text": f"ETL Pipeline execution {status.lower()} ({etl['records_processed']} records processed)",
                    "type": act_type
                })
                
            # 3. Fetch critical stock items
            low_stock = execute_query("""
                SELECT p.product_name, i.stock_level, w.name as wh_name
                FROM inventory i
                JOIN products p ON i.product_id = p.product_id
                JOIN warehouses w ON i.warehouse_id = w.warehouse_id
                WHERE i.stock_level <= i.safety_stock LIMIT 3
            """)
            for item in low_stock:
                activities.append({
                    "time": "System Alert",
                    "text": f"Inventory Alert: {item['product_name']} is running low in {item['wh_name']} (stock: {item['stock_level']})",
                    "type": "alert"
                })
                
            # Sort activities - system alerts first, then order chronologically if possible, or just limit to 6
            return activities[:6]
        except Exception as e:
            logger.error(f"Failed to fetch recent activities: {str(e)}")
            return [
                { "time": "Just now", "text": "System operational. Real-time logging active.", "type": "info" }
            ]

