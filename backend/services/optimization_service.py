"""
services/optimization_service.py
Optimization Engine - Recommends best suppliers, warehouses, shipping methods,
inventory reorder quantities, cost reduction actions, and delivery improvements.
"""

import logging
from backend.models.database import execute_query

logger = logging.getLogger(__name__)


class OptimizationService:

    @staticmethod
    def get_best_suppliers() -> list:
        """
        Recommends best suppliers based on rating, average delay, and high-risk rate.
        Returns suppliers sorted by composite score (best first).
        """
        query = """
            SELECT
                s.supplier_id,
                s.name,
                s.rating,
                s.status,
                COALESCE(ROUND(AVG(f.Delivery_Delay), 2), 0) AS avg_delay_days,
                COUNT(f.Fact_ID)                             AS total_orders,
                SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) AS high_risk_orders
            FROM suppliers s
            LEFT JOIN fact_order f ON s.supplier_id = f.Supplier_ID
            GROUP BY s.supplier_id, s.name, s.rating, s.status
            ORDER BY s.rating DESC, avg_delay_days ASC
        """
        results = execute_query(query)
        for row in results:
            total = row["total_orders"] or 1
            high_rate = (row["high_risk_orders"] or 0) / total
            avg_delay = row["avg_delay_days"] or 0
            rating = row["rating"] or 0

            if rating >= 4.0 and avg_delay <= 1.0 and high_rate <= 0.1:
                row["recommendation"] = "Preferred Partner (High Reliability & Quality)"
                row["priority"] = 1
            elif rating >= 3.5 and avg_delay <= 2.0:
                row["recommendation"] = "Approved Supplier (Standard Reliability)"
                row["priority"] = 2
            else:
                row["recommendation"] = "Risk Factor (Underperforming – Monitor Closely)"
                row["priority"] = 3

        return sorted(results, key=lambda x: x["priority"])

    @staticmethod
    def get_best_warehouses() -> list:
        """
        Recommends warehouses by on-time performance and throughput.
        """
        results = execute_query("""
            SELECT
                w.Warehouse_ID,
                w.Warehouse_Name   AS name,
                w.Warehouse_City   AS city,
                w.Warehouse_State  AS state,
                w.Warehouse_Capacity AS capacity,
                COUNT(f.Fact_ID)                   AS total_orders,
                ROUND(SUM(f.Sales), 2)             AS total_revenue,
                ROUND(AVG(f.Delivery_Delay), 2)    AS avg_delay_days,
                SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS delayed_orders,
                ROUND(
                    SUM(CASE WHEN f.Delivery_Delay <= 0 THEN 1 ELSE 0 END) /
                    COUNT(f.Fact_ID) * 100, 2
                )                                  AS on_time_rate_pct
            FROM dim_warehouse w
                LEFT JOIN fact_order f ON w.Warehouse_ID = f.Warehouse_ID
            GROUP BY w.Warehouse_ID, w.Warehouse_Name, w.Warehouse_City,
                     w.Warehouse_State, w.Warehouse_Capacity
        """)

        for row in results:
            on_time = row["on_time_rate_pct"] or 0
            avg_delay = row["avg_delay_days"] or 0

            if on_time >= 70 and avg_delay <= 1.0:
                row["recommendation"] = "Preferred Fulfillment Hub (High On-Time Rate)"
            elif on_time >= 50:
                row["recommendation"] = "Approved Warehouse (Average Performance)"
            else:
                row["recommendation"] = "Needs Improvement (High Delay Rate)"

        return sorted(results, key=lambda x: x["on_time_rate_pct"] or 0, reverse=True)

    @staticmethod
    def get_best_shipping_methods() -> list:
        """
        Recommends optimal shipping methods based on on-time delivery rates.
        """
        results = execute_query("""
            SELECT
                sh.Shipping_Mode,
                COUNT(f.Fact_ID)                   AS total_shipments,
                SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS "delayed",
                ROUND(AVG(f.Delivery_Delay), 2)    AS avg_delay_days,
                ROUND(
                    SUM(CASE WHEN f.Delivery_Delay <= 0 THEN 1 ELSE 0 END) /
                    COUNT(f.Fact_ID) * 100, 2
                )                                  AS on_time_rate_pct,
                ROUND(SUM(f.Sales), 2)             AS total_revenue
            FROM fact_order f
                JOIN dim_shipping sh ON f.Shipping_ID = sh.Shipping_ID
            GROUP BY sh.Shipping_Mode
        """)

        for row in results:
            on_time = row["on_time_rate_pct"] or 0
            if on_time >= 70:
                row["recommendation"] = "Highly Recommended – Best On-Time Performance"
                row["priority"] = 1
            elif on_time >= 50:
                row["recommendation"] = "Acceptable – Moderate On-Time Rate"
                row["priority"] = 2
            else:
                row["recommendation"] = "Not Recommended – Frequent Delays"
                row["priority"] = 3

        return sorted(results, key=lambda x: x["on_time_rate_pct"] or 0, reverse=True)

    @staticmethod
    def get_delayed_deliveries(limit: int = 50) -> list:
        """
        Detects OLTP shipments where real days > scheduled days.
        """
        return execute_query(f"""
            SELECT
                s.shipment_id,
                o.order_id,
                c.fname, c.lname,
                p.product_name,
                s.shipping_mode,
                s.days_shipping_real,
                s.days_shipment_scheduled,
                (s.days_shipping_real - s.days_shipment_scheduled) AS delay_days,
                s.delivery_status
            FROM shipments s
                JOIN orders o    ON s.order_id    = o.order_id
                JOIN customers c ON o.customer_id = c.customer_id
                JOIN products p  ON o.product_id  = p.product_id
            WHERE s.days_shipping_real > s.days_shipment_scheduled
            ORDER BY delay_days DESC
            LIMIT {int(limit)}
        """)

    @staticmethod
    def get_inventory_replenishment() -> list:
        """
        Identifies stock items requiring replenishment based on reorder points.
        Adds urgency classification and recommended order quantity.
        """
        results = execute_query("""
            SELECT
                i.inventory_id,
                p.product_id,
                p.product_name,
                p.product_price,
                w.name             AS warehouse_name,
                i.stock_level,
                i.reorder_point,
                i.safety_stock,
                i.lead_time_days,
                (i.reorder_point + i.safety_stock - i.stock_level) AS recommended_reorder_qty
            FROM inventory i
                JOIN products p   ON i.product_id   = p.product_id
                JOIN warehouses w ON i.warehouse_id  = w.warehouse_id
            WHERE i.stock_level <= i.reorder_point
            ORDER BY (i.stock_level / GREATEST(i.reorder_point, 1)) ASC
        """)

        for row in results:
            ratio = row["stock_level"] / max(row["reorder_point"], 1)
            if row["stock_level"] <= row["safety_stock"]:
                row["urgency"] = "CRITICAL – Below Safety Stock"
            elif ratio <= 0.5:
                row["urgency"] = "HIGH – Under 50% of Reorder Point"
            else:
                row["urgency"] = "MEDIUM – Reorder Threshold Breached"

            # Estimated cost of reorder
            qty = max(row["recommended_reorder_qty"], 0)
            row["estimated_reorder_cost"] = round(qty * float(row["product_price"] or 0), 2)

        return results

    @staticmethod
    def get_high_risk_shipments(limit: int = 50) -> list:
        """
        Returns OLAP orders classified as High Risk.
        """
        return execute_query(f"""
            SELECT
                f.Order_ID,
                c.Customer_Fname,
                c.Customer_Lname,
                p.Product_Name,
                s.Shipping_Mode,
                f.Sales,
                f.Profit,
                f.Delivery_Delay,
                f.Risk_Level
            FROM fact_order f
                JOIN dim_customer c  ON f.Customer_ID  = c.Customer_ID
                JOIN dim_product p   ON f.Product_ID   = p.Product_ID
                JOIN dim_shipping s  ON f.Shipping_ID  = s.Shipping_ID
            WHERE f.Risk_Level = 'High'
            ORDER BY f.Profit ASC
            LIMIT {int(limit)}
        """)

    @staticmethod
    def get_cost_reduction_opportunities(limit: int = 50) -> list:
        """
        Returns orders with negative profit and attaches actionable cost insights.
        """
        results = execute_query(f"""
            SELECT
                o.order_id,
                p.product_name,
                o.quantity,
                o.sales,
                o.profit,
                ROUND(o.sales - o.profit, 2) AS total_cost,
                sh.shipping_mode,
                sh.delivery_status
            FROM orders o
                JOIN products p  ON o.product_id = p.product_id
                JOIN shipments sh ON o.order_id  = sh.order_id
            WHERE o.profit < 0
            ORDER BY o.profit ASC
            LIMIT {int(limit)}
        """)

        for row in results:
            loss_pct = abs(row["profit"]) / max(row["sales"], 0.01)
            if loss_pct > 0.5:
                row["actionable_insight"] = "Discontinue or renegotiate pricing structure immediately."
            elif row["delivery_status"] == "Late delivery":
                row["actionable_insight"] = "Switch carrier/shipping mode to avoid late delivery penalties."
            else:
                row["actionable_insight"] = "Adjust discount rates or unit price to restore margins."

        return results

    @staticmethod
    def get_delivery_optimization() -> dict:
        """
        Returns delivery performance analysis with actionable improvement suggestions.
        """
        mode_stats = execute_query("""
            SELECT
                sh.Shipping_Mode,
                COUNT(f.Fact_ID)                   AS total_orders,
                ROUND(AVG(f.Delivery_Delay), 2)    AS avg_delay,
                SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS late_count,
                ROUND(
                    SUM(CASE WHEN f.Delivery_Delay <= 0 THEN 1 ELSE 0 END) /
                    COUNT(f.Fact_ID) * 100, 2
                )                                  AS on_time_pct
            FROM fact_order f
                JOIN dim_shipping sh ON f.Shipping_ID = sh.Shipping_ID
            GROUP BY sh.Shipping_Mode
            ORDER BY on_time_pct DESC
        """)

        suggestions = []
        for row in mode_stats:
            if (row["on_time_pct"] or 0) < 50:
                suggestions.append({
                    "shipping_mode": row["Shipping_Mode"],
                    "issue": f"Only {row['on_time_pct']}% on-time rate with avg {row['avg_delay']} day delay",
                    "suggestion": "Replace or supplement with a higher-performing carrier."
                })

        return {
            "shipping_mode_stats": mode_stats,
            "improvement_suggestions": suggestions
        }

    @staticmethod
    def get_transportation_improvement() -> dict:
        """
        Compares shipping modes and recommends transport strategy improvements.
        """
        comparison = execute_query("""
            SELECT
                sh.Shipping_Mode,
                COUNT(f.Fact_ID)                   AS total,
                ROUND(AVG(f.Delivery_Delay), 2)    AS avg_delay,
                ROUND(SUM(f.Profit) / SUM(f.Sales) * 100, 2) AS profit_margin_pct,
                SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) AS delayed_count
            FROM fact_order f
                JOIN dim_shipping sh ON f.Shipping_ID = sh.Shipping_ID
            GROUP BY sh.Shipping_Mode
        """)

        # Find best mode (lowest avg_delay with highest profit margin)
        best = sorted(comparison, key=lambda x: (x["avg_delay"] or 99, -(x["profit_margin_pct"] or 0)))
        best_mode = best[0]["Shipping_Mode"] if best else "Standard Class"

        recommendations = [{
            "action": f"Prioritize '{best_mode}' shipping mode for high-value orders.",
            "reason": "Lowest average delay and best profit margin combination."
        }]

        for row in comparison:
            if (row["avg_delay"] or 0) > 2 and (row["delayed_count"] or 0) > 100:
                recommendations.append({
                    "action": f"Reduce usage of '{row['Shipping_Mode']}' for time-sensitive orders.",
                    "reason": f"Average {row['avg_delay']} day delay with {row['delayed_count']} delayed shipments."
                })

        return {
            "mode_comparison": comparison,
            "recommended_primary_mode": best_mode,
            "recommendations": recommendations
        }
