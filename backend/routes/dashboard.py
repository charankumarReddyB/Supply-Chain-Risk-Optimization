"""
routes/dashboard.py
Dashboard API endpoints returning KPIs, trends, and analytics summaries.
All endpoints are JWT-protected.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from backend.controllers.dashboard_controller import DashboardController

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@dashboard_bp.route("/stats", methods=["GET"])
@jwt_required()
def get_stats():
    """
    GET /api/dashboard/stats
    Returns full dashboard KPIs: orders, revenue, profit, risk, delay, inventory.
    """
    try:
        kpis = DashboardController.get_kpis()
        risk_dist = DashboardController.get_risk_distribution()
        monthly = DashboardController.get_monthly_sales(limit=24)
        segments = DashboardController.get_segment_breakdown()
        inventory = DashboardController.get_inventory_status()
        recent_activities = DashboardController.get_recent_activities()
        supplier_ranking = DashboardController.get_supplier_ranking(limit=6)

        return jsonify({
            "kpis": kpis,
            "risk_distribution": risk_dist,
            "monthly_sales_trend": monthly,
            "segment_breakdown": segments,
            "inventory_status": inventory,
            "recent_activities": recent_activities,
            "supplier_ranking": supplier_ranking,
            "currency": "INR"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Failed to retrieve dashboard stats: {str(e)}"}), 500


@dashboard_bp.route("/kpis", methods=["GET"])
@jwt_required()
def get_kpis():
    """
    GET /api/dashboard/kpis
    Returns all KPI metrics for quick display cards.
    """
    try:
        kpi_data = DashboardController.get_kpis()
        kpi_data["currency"] = "INR"
        return jsonify(kpi_data), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve KPIs: {str(e)}"}), 500


@dashboard_bp.route("/monthly-sales", methods=["GET"])
@jwt_required()
def get_monthly_sales():
    """
    GET /api/dashboard/monthly-sales?limit=12
    Returns monthly revenue and profit trend.
    """
    try:
        limit = request.args.get("limit", 24, type=int)
        return jsonify(DashboardController.get_monthly_sales(limit=limit)), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve monthly sales: {str(e)}"}), 500


@dashboard_bp.route("/supplier-ranking", methods=["GET"])
@jwt_required()
def get_supplier_ranking():
    """
    GET /api/dashboard/supplier-ranking?limit=10
    Returns top supplier ranking by performance score.
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        return jsonify(DashboardController.get_supplier_ranking(limit=limit)), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve supplier ranking: {str(e)}"}), 500


@dashboard_bp.route("/top-products", methods=["GET"])
@jwt_required()
def get_top_products():
    """
    GET /api/dashboard/top-products?limit=10
    Returns top selling products by revenue.
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        return jsonify(DashboardController.get_top_selling_products(limit=limit)), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve top products: {str(e)}"}), 500


@dashboard_bp.route("/late-deliveries", methods=["GET"])
@jwt_required()
def get_late_deliveries():
    """
    GET /api/dashboard/late-deliveries?limit=20
    Returns most delayed shipments with customer and product context.
    """
    try:
        limit = request.args.get("limit", 20, type=int)
        return jsonify(DashboardController.get_late_deliveries(limit=limit)), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve late deliveries: {str(e)}"}), 500


@dashboard_bp.route("/warehouse-performance", methods=["GET"])
@jwt_required()
def get_warehouse_performance():
    """
    GET /api/dashboard/warehouse-performance
    Returns performance metrics per warehouse including delay rates and risk counts.
    """
    try:
        return jsonify(DashboardController.get_warehouse_performance()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve warehouse performance: {str(e)}"}), 500


@dashboard_bp.route("/inventory-status", methods=["GET"])
@jwt_required()
def get_inventory_status():
    """
    GET /api/dashboard/inventory-status
    Returns inventory health summary: CRITICAL / WARNING / OK counts.
    """
    try:
        return jsonify(DashboardController.get_inventory_status()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve inventory status: {str(e)}"}), 500
