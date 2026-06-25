"""
controllers/risk_controller.py
Business logic for supply chain risk analysis.
Analyzes supplier delays, delivery delays, inventory shortage,
shipping performance, warehouse performance, and generates risk scores.
"""

import logging
from backend.models.database import execute_query

logger = logging.getLogger(__name__)


class RiskController:

    @staticmethod
    def get_supplier_risk() -> list:
        """
        Analyzes each supplier's risk based on delay rate, high-risk order
        proportion, and rating. Returns a risk score (0-100, lower = better).
        """
        try:
            suppliers = execute_query("""
                SELECT
                    s.Supplier_ID,
                    s.Supplier_Name                       AS supplier_name,
                    s.Supplier_Rating                     AS rating,
                    s.Supplier_Status                     AS status,
                    COUNT(f.Fact_ID)                      AS total_orders,
                    ROUND(AVG(f.Delivery_Delay), 2)       AS avg_delay_days,
                    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END)  AS delayed_orders,
                    SUM(CASE WHEN f.Risk_Level = 'High'   THEN 1 ELSE 0 END) AS high_risk_orders,
                    SUM(CASE WHEN f.Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS medium_risk_orders,
                    ROUND(SUM(f.Sales), 2)                AS total_sales
                FROM dim_supplier s
                    LEFT JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
                GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating, s.Supplier_Status
                ORDER BY avg_delay_days DESC
            """)

            for row in suppliers:
                total = row["total_orders"] or 1
                delay_rate = (row["delayed_orders"] or 0) / total
                high_risk_rate = (row["high_risk_orders"] or 0) / total
                rating_val = float(row["rating"]) if row["rating"] is not None else 5.0
                rating_penalty = max(0.0, (5.0 - rating_val) / 5.0)

                # Composite risk score (0-100): higher = more risky
                risk_score = round(
                    (delay_rate * 40) + (high_risk_rate * 40) + (rating_penalty * 20), 2
                )
                row["risk_score"] = risk_score

                if risk_score >= 50:
                    row["risk_category"] = "High Risk"
                elif risk_score >= 25:
                    row["risk_category"] = "Medium Risk"
                else:
                    row["risk_category"] = "Low Risk"

            return suppliers

        except Exception as e:
            logger.error(f"Supplier risk analysis error: {e}")
            raise

    @staticmethod
    def get_delivery_delay_risk() -> dict:
        """
        Analyzes delivery delay patterns across shipping modes and suppliers.
        Returns summary statistics and a list of critical late shipments.
        """
        try:
            summary = execute_query("""
                SELECT
                    sh.Shipping_Mode,
                    COUNT(f.Fact_ID)                      AS total_shipments,
                    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS delayed,
                    ROUND(AVG(CASE WHEN f.Delivery_Delay > 0 THEN f.Delivery_Delay END), 2) AS avg_delay_days,
                    ROUND(
                        SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) /
                        COUNT(f.Fact_ID) * 100, 2
                    ) AS delay_rate_percent
                FROM fact_order f
                    JOIN dim_shipping sh ON f.Shipping_ID = sh.Shipping_ID
                GROUP BY sh.Shipping_Mode
                ORDER BY delay_rate_percent DESC
            """)

            critical = execute_query("""
                SELECT
                    f.Order_ID,
                    c.Customer_Fname, c.Customer_Lname,
                    p.Product_Name,
                    s.Supplier_Name,
                    sh.Shipping_Mode,
                    f.Delivery_Delay,
                    f.Risk_Level,
                    d.Full_Date AS order_date
                FROM fact_order f
                    JOIN dim_customer c  ON f.Customer_ID  = c.Customer_ID
                    JOIN dim_product p   ON f.Product_ID   = p.Product_ID
                    JOIN dim_supplier s  ON f.Supplier_ID  = s.Supplier_ID
                    JOIN dim_shipping sh ON f.Shipping_ID  = sh.Shipping_ID
                    JOIN dim_date d      ON f.Date_ID      = d.Date_ID
                WHERE f.Risk_Level = 'High' AND f.Delivery_Delay > 0
                ORDER BY f.Delivery_Delay DESC
                LIMIT 30
            """)

            return {
                "shipping_mode_summary": summary,
                "critical_late_shipments": critical
            }

        except Exception as e:
            logger.error(f"Delivery delay risk analysis error: {e}")
            raise

    @staticmethod
    def get_inventory_shortage_risk() -> list:
        """
        Identifies products at risk of stockout based on stock vs.
        safety stock and reorder point thresholds.
        """
        try:
            results = execute_query("""
                SELECT
                    i.inventory_id,
                    p.product_id,
                    p.product_name,
                    p.product_price,
                    w.name              AS warehouse_name,
                    i.stock_level,
                    i.reorder_point,
                    i.safety_stock,
                    i.lead_time_days,
                    (i.reorder_point - i.stock_level) AS deficit,
                    CASE
                        WHEN i.stock_level <= i.safety_stock  THEN 'CRITICAL'
                        WHEN i.stock_level <= i.reorder_point THEN 'WARNING'
                        ELSE 'OK'
                    END AS stockout_risk
                FROM inventory i
                    JOIN products p    ON i.product_id   = p.product_id
                    JOIN warehouses w  ON i.warehouse_id = w.warehouse_id
                ORDER BY
                    CASE
                        WHEN i.stock_level <= i.safety_stock  THEN 1
                        WHEN i.stock_level <= i.reorder_point THEN 2
                        ELSE 3
                    END,
                    i.stock_level ASC
            """)
            return results
        except Exception as e:
            logger.error(f"Inventory shortage risk error: {e}")
            raise

    @staticmethod
    def get_shipping_performance_risk() -> list:
        """
        Evaluates shipping performance risk per mode with delay statistics.
        """
        try:
            return execute_query("""
                SELECT
                    sh.Shipping_Mode,
                    COUNT(f.Fact_ID)                   AS total_orders,
                    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS delayed_orders,
                    ROUND(AVG(f.Delivery_Delay), 2)    AS avg_delay_days,
                    ROUND(
                        SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) /
                        COUNT(f.Fact_ID) * 100, 2
                    )                                  AS delay_rate_pct,
                    ROUND(SUM(f.Sales), 2)             AS total_revenue,
                    ROUND(SUM(f.Profit), 2)            AS total_profit
                FROM fact_order f
                    JOIN dim_shipping sh ON f.Shipping_ID = sh.Shipping_ID
                GROUP BY sh.Shipping_Mode
                ORDER BY delay_rate_pct DESC
            """)
        except Exception as e:
            logger.error(f"Shipping performance risk error: {e}")
            raise

    @staticmethod
    def get_warehouse_performance_risk() -> list:
        """
        Evaluates warehouse-level risk scores based on delay and risk ratios.
        """
        try:
            warehouses = execute_query("""
                SELECT
                    w.Warehouse_ID,
                    w.Warehouse_Name,
                    w.Warehouse_City,
                    w.Warehouse_Capacity,
                    COUNT(f.Fact_ID)                   AS total_orders,
                    ROUND(AVG(f.Delivery_Delay), 2)    AS avg_delay_days,
                    SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS delayed_orders,
                    SUM(CASE WHEN f.Risk_Level = 'High'   THEN 1 ELSE 0 END) AS high_risk,
                    SUM(CASE WHEN f.Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS medium_risk,
                    SUM(CASE WHEN f.Risk_Level = 'Low'    THEN 1 ELSE 0 END) AS low_risk,
                    ROUND(SUM(f.Sales), 2)             AS total_revenue
                FROM dim_warehouse w
                    LEFT JOIN fact_order f ON w.Warehouse_ID = f.Warehouse_ID
                GROUP BY w.Warehouse_ID, w.Warehouse_Name, w.Warehouse_City, w.Warehouse_Capacity
            """)

            for row in warehouses:
                total = row["total_orders"] or 1
                delay_rate = (row["delayed_orders"] or 0) / total
                high_rate = (row["high_risk"] or 0) / total
                risk_score = round((delay_rate * 50) + (high_rate * 50), 2)
                row["risk_score"] = risk_score
                row["risk_category"] = (
                    "High Risk" if risk_score >= 50 else
                    "Medium Risk" if risk_score >= 25 else
                    "Low Risk"
                )

            return sorted(warehouses, key=lambda x: x["risk_score"], reverse=True)

        except Exception as e:
            logger.error(f"Warehouse performance risk error: {e}")
            raise

    @staticmethod
    def get_overall_risk_summary() -> dict:
        """
        Returns a consolidated risk summary across all dimensions.
        """
        try:
            fact_summary = execute_query("""
                SELECT
                    COUNT(*) AS total_records,
                    SUM(CASE WHEN Risk_Level = 'High'   THEN 1 ELSE 0 END) AS high_risk,
                    SUM(CASE WHEN Risk_Level = 'Medium' THEN 1 ELSE 0 END) AS medium_risk,
                    SUM(CASE WHEN Risk_Level = 'Low'    THEN 1 ELSE 0 END) AS low_risk,
                    ROUND(AVG(Delivery_Delay), 2)       AS avg_delivery_delay,
                    SUM(CASE WHEN Delivery_Delay > 0 THEN 1 ELSE 0 END) AS total_delayed
                FROM fact_order
            """)

            inventory_critical = execute_query(
                "SELECT COUNT(*) AS count FROM inventory WHERE stock_level <= safety_stock"
            )

            return {
                "fact_summary": fact_summary[0] if fact_summary else {},
                "inventory_critical_items": inventory_critical[0]["count"] if inventory_critical else 0
            }

        except Exception as e:
            logger.error(f"Overall risk summary error: {e}")
            raise
