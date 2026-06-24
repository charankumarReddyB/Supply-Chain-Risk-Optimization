"""
routes/warehouse.py
Warehouse CRUD API + data warehouse (OLAP) management endpoints.
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.database import execute_query
from backend.warehouse.schema import get_warehouse_summary, clear_warehouse
from backend.middleware.auth_middleware import admin_required

warehouse_bp = Blueprint("warehouse", __name__, url_prefix="/api/warehouses")


@warehouse_bp.route("", methods=["GET"])
@jwt_required()
def get_all_warehouses():
    """
    GET /api/warehouses
    Returns all warehouse records with inventory utilization.
    """
    try:
        warehouses = execute_query("""
            SELECT
                w.*,
                COALESCE(SUM(i.stock_level), 0)   AS total_stock,
                COUNT(DISTINCT i.product_id)       AS distinct_products
            FROM warehouses w
            LEFT JOIN inventory i ON w.warehouse_id = i.warehouse_id
            GROUP BY w.warehouse_id, w.name, w.city, w.state, w.country, w.capacity, w.manager
        """)
        return jsonify(warehouses), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch warehouses: {str(e)}"}), 500


@warehouse_bp.route("/<int:warehouse_id>", methods=["GET"])
@jwt_required()
def get_warehouse(warehouse_id):
    """
    GET /api/warehouses/<warehouse_id>
    Returns a single warehouse with its inventory details.
    """
    try:
        wh = execute_query(
            "SELECT * FROM warehouses WHERE warehouse_id = %s", (warehouse_id,)
        )
        if not wh:
            return jsonify({"error": "Warehouse not found"}), 404

        inventory = execute_query("""
            SELECT p.product_name, i.stock_level, i.reorder_point, i.safety_stock
            FROM inventory i
            JOIN products p ON i.product_id = p.product_id
            WHERE i.warehouse_id = %s
        """, (warehouse_id,))

        result = wh[0]
        result["inventory"] = inventory
        return jsonify(result), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch warehouse: {str(e)}"}), 500


@warehouse_bp.route("", methods=["POST"])
@admin_required
def create_warehouse():
    """
    POST /api/warehouses
    Body: { warehouse_id, name, city, state, country, capacity, manager }
    Creates a warehouse in both OLTP and OLAP dim_warehouse.
    """
    data = request.get_json(silent=True) or {}
    warehouse_id = data.get("warehouse_id")
    name = (data.get("name") or "").strip()
    city = data.get("city", "")
    state = data.get("state", "")
    country = data.get("country", "")
    capacity = data.get("capacity", 0)
    manager = data.get("manager", "")

    if not warehouse_id or not name:
        return jsonify({"error": "warehouse_id and name are required"}), 400

    try:
        existing = execute_query(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id = %s", (warehouse_id,)
        )
        if existing:
            return jsonify({"error": f"Warehouse {warehouse_id} already exists"}), 400

        execute_query(
            """INSERT INTO warehouses (warehouse_id, name, city, state, country, capacity, manager)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (warehouse_id, name, city, state, country, capacity, manager),
            fetch=False
        )
        execute_query(
            """INSERT INTO dim_warehouse (Warehouse_ID, Warehouse_Name, Warehouse_City, Warehouse_State, Warehouse_Capacity)
               VALUES (%s, %s, %s, %s, %s)""",
            (warehouse_id, name, city, state, capacity),
            fetch=False
        )
        return jsonify({"message": "Warehouse created successfully"}), 201

    except Exception as e:
        return jsonify({"error": f"Failed to create warehouse: {str(e)}"}), 500


@warehouse_bp.route("/<int:warehouse_id>", methods=["PUT"])
@admin_required
def update_warehouse(warehouse_id):
    """
    PUT /api/warehouses/<warehouse_id>
    Updates warehouse fields (any combination of: name, city, state, country, capacity, manager).
    """
    data = request.get_json(silent=True) or {}
    try:
        existing = execute_query(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id = %s", (warehouse_id,)
        )
        if not existing:
            return jsonify({"error": "Warehouse not found"}), 404

        fields, params = [], []
        dim_fields, dim_params = [], []

        for field, col, dim_col in [
            ("name", "name", "Warehouse_Name"),
            ("city", "city", "Warehouse_City"),
            ("state", "state", "Warehouse_State"),
            ("country", "country", None),
            ("manager", "manager", None),
        ]:
            if data.get(field) is not None:
                fields.append(f"{col} = %s")
                params.append(data[field])
                if dim_col:
                    dim_fields.append(f"{dim_col} = %s")
                    dim_params.append(data[field])

        if data.get("capacity") is not None:
            fields.append("capacity = %s")
            params.append(data["capacity"])
            dim_fields.append("Warehouse_Capacity = %s")
            dim_params.append(data["capacity"])

        if fields:
            params.append(warehouse_id)
            execute_query(
                f"UPDATE warehouses SET {', '.join(fields)} WHERE warehouse_id = %s",
                params, fetch=False
            )
        if dim_fields:
            dim_params.append(warehouse_id)
            execute_query(
                f"UPDATE dim_warehouse SET {', '.join(dim_fields)} WHERE Warehouse_ID = %s",
                dim_params, fetch=False
            )

        return jsonify({"message": "Warehouse updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to update warehouse: {str(e)}"}), 500


@warehouse_bp.route("/<int:warehouse_id>", methods=["DELETE"])
@admin_required
def delete_warehouse(warehouse_id):
    """
    DELETE /api/warehouses/<warehouse_id>
    Removes warehouse from OLTP and OLAP tables.
    """
    try:
        existing = execute_query(
            "SELECT warehouse_id FROM warehouses WHERE warehouse_id = %s", (warehouse_id,)
        )
        if not existing:
            return jsonify({"error": "Warehouse not found"}), 404

        execute_query("DELETE FROM warehouses WHERE warehouse_id = %s", (warehouse_id,), fetch=False)
        execute_query("DELETE FROM dim_warehouse WHERE Warehouse_ID = %s", (warehouse_id,), fetch=False)
        return jsonify({"message": "Warehouse deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to delete warehouse: {str(e)}"}), 500


# ─── Data Warehouse (OLAP) Management ────────────────────────────────────────

@warehouse_bp.route("/olap/summary", methods=["GET"])
@jwt_required()
def get_olap_summary():
    """
    GET /api/warehouses/olap/summary
    Returns row counts for all star schema tables (fact + dimensions).
    """
    try:
        return jsonify(get_warehouse_summary()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve OLAP summary: {str(e)}"}), 500


@warehouse_bp.route("/olap/clear", methods=["DELETE"])
@admin_required
def clear_olap():
    """
    DELETE /api/warehouses/olap/clear
    Truncates all OLAP fact and dimension tables (use with caution).
    """
    try:
        return jsonify(clear_warehouse()), 200
    except Exception as e:
        return jsonify({"error": f"Failed to clear OLAP warehouse: {str(e)}"}), 500
