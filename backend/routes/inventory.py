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

@inventory_bp.route("", methods=["POST"])
@admin_required
def create_inventory():
    data = request.get_json() or {}
    product_id = data.get("product_id")
    warehouse_id = data.get("warehouse_id", 1)  # Default warehouse 1
    stock_level = data.get("stock_level", 0)
    reorder_point = data.get("reorder_point", 50)
    safety_stock = data.get("safety_stock", 10)
    lead_time_days = data.get("lead_time_days", 5)

    if not product_id:
        return jsonify({"error": "product_id is a required field"}), 400

    try:
        # Check if product exists
        prod = execute_query("SELECT product_id FROM products WHERE product_id = %s", (product_id,))
        if not prod:
            return jsonify({"error": "Product not found"}), 404

        # Check if inventory already exists for this product in this warehouse
        existing = execute_query(
            "SELECT inventory_id FROM inventory WHERE product_id = %s AND warehouse_id = %s",
            (product_id, warehouse_id)
        )
        if existing:
            return jsonify({"error": f"Inventory for product {product_id} in warehouse {warehouse_id} already exists"}), 409

        execute_query(
            """INSERT INTO inventory (product_id, warehouse_id, stock_level, reorder_point, safety_stock, lead_time_days)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (product_id, warehouse_id, stock_level, reorder_point, safety_stock, lead_time_days),
            fetch=False
        )

        return jsonify({"message": "Inventory record created successfully"}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create inventory: {str(e)}"}), 500
