from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.database import execute_query
from backend.services.optimization_service import OptimizationService
from backend.middleware.auth_middleware import admin_required

inventory_bp = Blueprint("inventory", __name__, url_prefix="/api/inventory")

@inventory_bp.route("", methods=["GET"])
@jwt_required()
def get_all_inventory():
    try:
        query = """
            SELECT 
                i.inventory_id,
                p.product_id,
                p.product_name,
                p.product_price,
                w.name as warehouse_name,
                i.stock_level,
                i.reorder_point,
                i.safety_stock,
                i.lead_time_days
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            JOIN warehouses w ON i.warehouse_id = w.warehouse_id
        """
        inventory = execute_query(query)
        return jsonify(inventory), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch inventory: {str(e)}"}), 500

@inventory_bp.route("/replenish", methods=["GET"])
@jwt_required()
def get_replenishment_suggestions():
    try:
        suggestions = OptimizationService.get_inventory_replenishment()
        return jsonify(suggestions), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch replenishment suggestions: {str(e)}"}), 500

@inventory_bp.route("/<int:inventory_id>", methods=["PUT"])
@admin_required
def update_inventory(inventory_id):
    data = request.get_json() or {}
    stock_level = data.get("stock_level")
    reorder_point = data.get("reorder_point")
    safety_stock = data.get("safety_stock")
    lead_time_days = data.get("lead_time_days")
    
    try:
        # Check if exists
        existing = execute_query("SELECT inventory_id FROM inventory WHERE inventory_id = %s", (inventory_id,))
        if not existing:
            return jsonify({"error": "Inventory item not found"}), 404
            
        fields = []
        params = []
        
        if stock_level is not None:
            fields.append("stock_level = %s")
            params.append(stock_level)
        if reorder_point is not None:
            fields.append("reorder_point = %s")
            params.append(reorder_point)
        if safety_stock is not None:
            fields.append("safety_stock = %s")
            params.append(safety_stock)
        if lead_time_days is not None:
            fields.append("lead_time_days = %s")
            params.append(lead_time_days)
            
        if fields:
            params.append(inventory_id)
            execute_query(f"UPDATE inventory SET {', '.join(fields)} WHERE inventory_id = %s", params, fetch=False)
            
        return jsonify({"message": "Inventory updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update inventory: {str(e)}"}), 500
