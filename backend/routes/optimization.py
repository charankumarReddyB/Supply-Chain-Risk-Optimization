"""
routes/optimization.py
Optimization Engine API endpoints.
Provides recommendations for: best supplier, best warehouse, inventory reorder,
best shipping method, transportation improvement, cost reduction, delivery optimization.
"""

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from backend.services.optimization_service import OptimizationService

optimization_bp = Blueprint("optimization", __name__, url_prefix="/api/optimization")


@optimization_bp.route("/suppliers", methods=["GET"])
@jwt_required()
def recommend_suppliers():
    """
    GET /api/optimization/suppliers
    Recommends best suppliers ranked by rating and average delay.
    Each result includes an actionable recommendation label.
    """
    try:
        return jsonify(OptimizationService.get_best_suppliers()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load supplier recommendations: {str(e)}"}), 500


@optimization_bp.route("/warehouses", methods=["GET"])
@jwt_required()
def recommend_warehouses():
    """
    GET /api/optimization/warehouses
    Recommends best warehouses based on throughput, delay rate, and utilization.
    """
    try:
        return jsonify(OptimizationService.get_best_warehouses()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load warehouse recommendations: {str(e)}"}), 500


@optimization_bp.route("/shipping-method", methods=["GET"])
@jwt_required()
def recommend_shipping_method():
    """
    GET /api/optimization/shipping-method
    Recommends optimal shipping methods based on historical on-time performance.
    """
    try:
        return jsonify(OptimizationService.get_best_shipping_methods()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load shipping recommendations: {str(e)}"}), 500


@optimization_bp.route("/delayed-deliveries", methods=["GET"])
@jwt_required()
def detect_delays():
    """
    GET /api/optimization/delayed-deliveries
    Returns OLTP shipments that arrived later than scheduled.
    """
    try:
        return jsonify(OptimizationService.get_delayed_deliveries()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to detect delayed deliveries: {str(e)}"}), 500


@optimization_bp.route("/replenish", methods=["GET"])
@jwt_required()
def recommend_replenishment():
    """
    GET /api/optimization/replenish
    Returns products that need inventory reorder with recommended quantities and urgency.
    """
    try:
        return jsonify(OptimizationService.get_inventory_replenishment()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to calculate replenishment: {str(e)}"}), 500


@optimization_bp.route("/high-risk-shipments", methods=["GET"])
@jwt_required()
def identify_high_risk():
    """
    GET /api/optimization/high-risk-shipments
    Returns orders classified as High Risk from the OLAP fact table.
    """
    try:
        return jsonify(OptimizationService.get_high_risk_shipments()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to identify high risk shipments: {str(e)}"}), 500


@optimization_bp.route("/cost-reduction", methods=["GET"])
@jwt_required()
def recommend_cost_reductions():
    """
    GET /api/optimization/cost-reduction
    Returns orders with negative profit and actionable cost reduction suggestions.
    """
    try:
        return jsonify(OptimizationService.get_cost_reduction_opportunities()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to analyze cost reduction: {str(e)}"}), 500


@optimization_bp.route("/delivery", methods=["GET"])
@jwt_required()
def delivery_optimization():
    """
    GET /api/optimization/delivery
    Returns delivery performance analysis with route/mode improvement suggestions.
    """
    try:
        return jsonify(OptimizationService.get_delivery_optimization()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to load delivery optimization: {str(e)}"}), 500


@optimization_bp.route("/transportation", methods=["GET"])
@jwt_required()
def transportation_improvement():
    """
    GET /api/optimization/transportation
    Returns shipping mode comparison for transportation improvement recommendations.
    """
    try:
        return jsonify(OptimizationService.get_transportation_improvement()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to analyze transportation: {str(e)}"}), 500
