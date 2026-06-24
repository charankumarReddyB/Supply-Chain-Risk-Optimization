"""
routes/analytics.py
OLAP Analytics API endpoints backed by the data warehouse (star schema).
All endpoints are JWT-protected.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.controllers.analytics_controller import AnalyticsController

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


@analytics_bp.route("/top-delayed-suppliers", methods=["GET"])
@jwt_required()
def top_delayed_suppliers():
    """
    GET /api/analytics/top-delayed-suppliers?limit=10
    Returns top suppliers by average delivery delay.
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        return jsonify(AnalyticsController.get_top_delayed_suppliers(limit=limit)), 200
    except Exception as e:
        return jsonify({"error": f"Query failed: {str(e)}"}), 500


@analytics_bp.route("/highest-revenue-products", methods=["GET"])
@jwt_required()
def highest_revenue_products():
    """
    GET /api/analytics/highest-revenue-products?limit=10
    Returns top products by total revenue.
    """
    try:
        limit = request.args.get("limit", 10, type=int)
        return jsonify(AnalyticsController.get_highest_revenue_products(limit=limit)), 200
    except Exception as e:
        return jsonify({"error": f"Query failed: {str(e)}"}), 500


@analytics_bp.route("/inventory-summary", methods=["GET"])
@jwt_required()
def inventory_summary():
    """
    GET /api/analytics/inventory-summary
    Returns full inventory with stockout status classification.
    """
    try:
        return jsonify(AnalyticsController.get_inventory_summary()), 200
    except Exception as e:
        return jsonify({"error": f"Query failed: {str(e)}"}), 500


@analytics_bp.route("/monthly-sales", methods=["GET"])
@jwt_required()
def monthly_sales():
    """
    GET /api/analytics/monthly-sales?year=2023
    Returns monthly sales trend. Optionally filter by year.
    """
    try:
        year = request.args.get("year", None, type=int)
        return jsonify(AnalyticsController.get_monthly_sales_trend(year=year)), 200
    except Exception as e:
        return jsonify({"error": f"Query failed: {str(e)}"}), 500


@analytics_bp.route("/warehouse-performance", methods=["GET"])
@jwt_required()
def warehouse_performance():
    """
    GET /api/analytics/warehouse-performance
    Returns throughput, delay, revenue, and risk metrics per warehouse.
    """
    try:
        return jsonify(AnalyticsController.get_warehouse_performance()), 200
    except Exception as e:
        return jsonify({"error": f"Query failed: {str(e)}"}), 500


@analytics_bp.route("/shipping-performance", methods=["GET"])
@jwt_required()
def shipping_performance():
    """
    GET /api/analytics/shipping-performance
    Returns delay rate, average delay, and revenue by shipping mode.
    """
    try:
        return jsonify(AnalyticsController.get_shipping_performance()), 200
    except Exception as e:
        return jsonify({"error": f"Query failed: {str(e)}"}), 500


@analytics_bp.route("/risk-summary", methods=["GET"])
@jwt_required()
def risk_summary():
    """
    GET /api/analytics/risk-summary
    Returns risk distribution: count, revenue, profit, avg delay per risk level.
    """
    try:
        return jsonify(AnalyticsController.get_risk_summary()), 200
    except Exception as e:
        return jsonify({"error": f"Query failed: {str(e)}"}), 500


@analytics_bp.route("/supplier-ranking", methods=["GET"])
@jwt_required()
def supplier_ranking():
    """
    GET /api/analytics/supplier-ranking
    Returns all suppliers ranked by composite performance score.
    """
    try:
        return jsonify(AnalyticsController.get_supplier_ranking()), 200
    except Exception as e:
        return jsonify({"error": f"Query failed: {str(e)}"}), 500
