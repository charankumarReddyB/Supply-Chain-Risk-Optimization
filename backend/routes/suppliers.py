from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.database import execute_query
from backend.middleware.auth_middleware import admin_required

suppliers_bp = Blueprint("suppliers", __name__, url_prefix="/api/suppliers")

@suppliers_bp.route("", methods=["GET"])
@jwt_required()
def get_all_suppliers():
    try:
        suppliers = execute_query("SELECT * FROM suppliers ORDER BY supplier_id")
        for s in suppliers:
            s["currency"] = "INR"
        return jsonify(suppliers), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch suppliers: {str(e)}"}), 500

@suppliers_bp.route("/<int:supplier_id>", methods=["GET"])
@jwt_required()
def get_supplier(supplier_id):
    try:
        supplier = execute_query("SELECT * FROM suppliers WHERE supplier_id = %s", (supplier_id,))
        if not supplier:
            return jsonify({"error": "Supplier not found"}), 404
        s_dict = supplier[0]
        s_dict["currency"] = "INR"
        return jsonify(s_dict), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch supplier: {str(e)}"}), 500

@suppliers_bp.route("", methods=["POST"])
@admin_required
def create_supplier():
    data = request.get_json() or {}
    supplier_id = data.get("supplier_id")
    name = data.get("name")
    email = data.get("email", "")
    phone = data.get("phone", "")
    rating = data.get("rating", 5.0)
    status = data.get("status", "Active")

    if not supplier_id:
        try:
            max_id_res = execute_query("SELECT MAX(supplier_id) as max_id FROM suppliers")
            max_id = max_id_res[0]["max_id"] if max_id_res and max_id_res[0]["max_id"] is not None else 100
            supplier_id = max_id + 1
        except Exception as e:
            return jsonify({"error": f"Failed to auto-generate supplier_id: {str(e)}"}), 500

    if not name:
        return jsonify({"error": "name is a required field"}), 400

    try:
        existing = execute_query("SELECT supplier_id FROM suppliers WHERE supplier_id = %s", (supplier_id,))
        if existing:
            return jsonify({"error": f"Supplier with ID {supplier_id} already exists"}), 409

        execute_query(
            """INSERT INTO suppliers (supplier_id, name, email, phone, rating, status)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (supplier_id, name, email, phone, rating, status),
            fetch=False
        )

        # Sync to OLAP dim_supplier (ignore if already exists)
        try:
            execute_query(
                "INSERT INTO dim_supplier (Supplier_ID, Supplier_Name, Supplier_Rating, Supplier_Status) VALUES (%s, %s, %s, %s)",
                (supplier_id, name, rating, status),
                fetch=False
            )
        except Exception:
            pass

        return jsonify({"message": "Supplier created successfully"}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create supplier: {str(e)}"}), 500

@suppliers_bp.route("/<int:supplier_id>", methods=["PUT"])
@admin_required
def update_supplier(supplier_id):
    data = request.get_json() or {}

    try:
        existing = execute_query("SELECT supplier_id FROM suppliers WHERE supplier_id = %s", (supplier_id,))
        if not existing:
            return jsonify({"error": "Supplier not found"}), 404

        fields, params, dim_fields, dim_params = [], [], [], []

        for col, val in [("name", data.get("name")), ("email", data.get("email")),
                         ("phone", data.get("phone")), ("rating", data.get("rating")),
                         ("status", data.get("status"))]:
            if val is not None:
                fields.append(f"{col} = %s")
                params.append(val)

        for col, val in [("Supplier_Name", data.get("name")), ("Supplier_Rating", data.get("rating")),
                         ("Supplier_Status", data.get("status"))]:
            if val is not None:
                dim_fields.append(f"{col} = %s")
                dim_params.append(val)

        if fields:
            params.append(supplier_id)
            execute_query(f"UPDATE suppliers SET {', '.join(fields)} WHERE supplier_id = %s", params, fetch=False)

        if dim_fields:
            dim_params.append(supplier_id)
            execute_query(f"UPDATE dim_supplier SET {', '.join(dim_fields)} WHERE Supplier_ID = %s", dim_params, fetch=False)

        return jsonify({"message": "Supplier updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update supplier: {str(e)}"}), 500

@suppliers_bp.route("/<int:supplier_id>", methods=["DELETE"])
@admin_required
def delete_supplier(supplier_id):
    try:
        existing = execute_query("SELECT supplier_id FROM suppliers WHERE supplier_id = %s", (supplier_id,))
        if not existing:
            return jsonify({"error": "Supplier not found"}), 404

        execute_query("DELETE FROM suppliers WHERE supplier_id = %s", (supplier_id,), fetch=False)
        try:
            execute_query("DELETE FROM dim_supplier WHERE Supplier_ID = %s", (supplier_id,), fetch=False)
        except Exception:
            pass
        return jsonify({"message": "Supplier deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete supplier: {str(e)}"}), 500

@suppliers_bp.route("/performance", methods=["GET"])
@jwt_required()
def get_supplier_performance():
    """Returns analytics regarding supplier reliability, order counts, and delay rates."""
    try:
        query = """
            SELECT
                s.Supplier_ID as supplier_id,
                s.Supplier_Name as name,
                s.Supplier_Rating as rating,
                s.Supplier_Status as status,
                COUNT(f.Fact_ID) as total_orders,
                ROUND(SUM(f.Sales), 2) as total_sales,
                ROUND(AVG(f.Delivery_Delay), 2) as avg_delay_days,
                SUM(CASE WHEN f.Delivery_Delay > 0 THEN 1 ELSE 0 END) as delayed_orders_count
            FROM dim_supplier s
            LEFT JOIN fact_order f ON s.Supplier_ID = f.Supplier_ID
            GROUP BY s.Supplier_ID, s.Supplier_Name, s.Supplier_Rating, s.Supplier_Status
            ORDER BY avg_delay_days ASC
        """
        performance = execute_query(query)
        for p in performance:
            p["currency"] = "INR"
        return jsonify(performance), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch supplier performance: {str(e)}"}), 500
