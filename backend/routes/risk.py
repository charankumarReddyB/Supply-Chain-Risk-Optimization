"""
routes/risk.py
Risk analysis API endpoints.
Covers: supplier risk, delivery delays, inventory shortage,
shipping performance, warehouse performance, overall risk summary.
Also provides ML-based prediction and model training endpoints.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.controllers.risk_controller import RiskController
from backend.ml.predict import RiskPredictor
from backend.ml.train import train_model
from backend.middleware.auth_middleware import admin_required

risk_bp = Blueprint("risk", __name__, url_prefix="/api/risk")


@risk_bp.route("/summary", methods=["GET"])
@jwt_required()
def get_risk_summary():
    """
    GET /api/risk/summary
    Returns overall consolidated risk summary across all dimensions.
    """
    try:
        return jsonify(RiskController.get_overall_risk_summary()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve risk summary: {str(e)}"}), 500


@risk_bp.route("/suppliers", methods=["GET"])
@jwt_required()
def get_supplier_risk():
    """
    GET /api/risk/suppliers
    Returns each supplier's computed risk score, delay stats, and risk category.
    """
    try:
        return jsonify(RiskController.get_supplier_risk()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to analyze supplier risk: {str(e)}"}), 500


@risk_bp.route("/delivery-delays", methods=["GET"])
@jwt_required()
def get_delivery_delay_risk():
    """
    GET /api/risk/delivery-delays
    Returns delay statistics per shipping mode and a list of critical late shipments.
    """
    try:
        return jsonify(RiskController.get_delivery_delay_risk()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to analyze delivery delay risk: {str(e)}"}), 500


@risk_bp.route("/inventory-shortage", methods=["GET"])
@jwt_required()
def get_inventory_shortage_risk():
    """
    GET /api/risk/inventory-shortage
    Returns inventory items at risk: CRITICAL (below safety stock) or WARNING.
    """
    try:
        return jsonify(RiskController.get_inventory_shortage_risk()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to analyze inventory shortage risk: {str(e)}"}), 500


@risk_bp.route("/shipping-performance", methods=["GET"])
@jwt_required()
def get_shipping_performance_risk():
    """
    GET /api/risk/shipping-performance
    Evaluates risk and performance per shipping mode.
    """
    try:
        return jsonify(RiskController.get_shipping_performance_risk()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to analyze shipping performance: {str(e)}"}), 500


@risk_bp.route("/warehouse-performance", methods=["GET"])
@jwt_required()
def get_warehouse_performance_risk():
    """
    GET /api/risk/warehouse-performance
    Evaluates warehouse-level risk scores with delay ratios.
    """
    try:
        return jsonify(RiskController.get_warehouse_performance_risk()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to analyze warehouse risk: {str(e)}"}), 500


# ─── ML Endpoints ────────────────────────────────────────────────────────────

@risk_bp.route("/predict", methods=["POST"])
@jwt_required()
def predict_risk():
    """
    POST /api/risk/predict
    Predicts the risk level (Low / Medium / High) for a given order.
    Body:
    {
        "days_shipment_scheduled": int,
        "shipping_mode": str,
        "customer_segment": str,
        "category_name": str,
        "product_price": float,
        "sales": float,
        "discount_rate": float
    }
    """
    data = request.get_json(silent=True) or {}
    predictor = RiskPredictor()
    result = predictor.predict(data)

    if "error" in result:
        return jsonify(result), 400
    return jsonify(result), 200


@risk_bp.route("/model-info", methods=["GET"])
@jwt_required()
def get_model_info():
    """
    GET /api/risk/model-info
    Returns Decision Tree model metrics:
    accuracy, precision, recall, F1 score, confusion matrix, feature importance.
    """
    predictor = RiskPredictor()
    info = predictor.get_model_info()

    if info is None or "error" in (info or {}):
        return jsonify({"error": "Model not trained. Call POST /api/risk/train first."}), 400
    return jsonify(info), 200


@risk_bp.route("/train", methods=["POST"])
@admin_required
def trigger_training():
    """
    POST /api/risk/train
    Trains (or retrains) the Decision Tree risk classifier on the full dataset.
    Returns the resulting model metrics.
    """
    try:
        train_model()
        # Reload singleton predictor
        RiskPredictor._instance = None
        predictor = RiskPredictor()
        info = predictor.get_model_info()
        return jsonify({
            "message": "Model trained successfully",
            "metrics": info
        }), 200
    except Exception as e:
        return jsonify({"error": f"Training failed: {str(e)}"}), 500
