from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.database import execute_query
from backend.middleware.auth_middleware import admin_required

products_bp = Blueprint("products", __name__, url_prefix="/api/products")

@products_bp.route("", methods=["GET"])
@jwt_required()
def get_all_products():
    try:
        products = execute_query("SELECT * FROM products ORDER BY product_id")
        for p in products:
            p["currency"] = "INR"
        return jsonify(products), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch products: {str(e)}"}), 500

@products_bp.route("/<int:product_id>", methods=["GET"])
@jwt_required()
def get_product(product_id):
    try:
        product = execute_query("SELECT * FROM products WHERE product_id = %s", (product_id,))
        if not product:
            return jsonify({"error": "Product not found"}), 404
        p_dict = product[0]
        p_dict["currency"] = "INR"
        return jsonify(p_dict), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch product: {str(e)}"}), 500

@products_bp.route("", methods=["POST"])
@admin_required
def create_product():
    data = request.get_json() or {}
    product_id   = data.get("product_id")
    category_id  = data.get("category_id", 1)
    category_name = data.get("category_name", "General")
    product_name  = data.get("product_name")
    product_price = data.get("product_price")
    product_status = data.get("product_status", "0")
    description  = data.get("description", "")

    if not product_id:
        try:
            max_id_res = execute_query("SELECT MAX(product_id) as max_id FROM products")
            max_id = max_id_res[0]["max_id"] if max_id_res and max_id_res[0]["max_id"] is not None else 1000
            product_id = max_id + 1
        except Exception as e:
            return jsonify({"error": f"Failed to auto-generate product_id: {str(e)}"}), 500

    if not product_name or product_price is None:
        return jsonify({"error": "product_name and product_price are required"}), 400

    try:
        existing = execute_query("SELECT product_id FROM products WHERE product_id = %s", (product_id,))
        if existing:
            return jsonify({"error": f"Product with ID {product_id} already exists"}), 409

        execute_query(
            """INSERT INTO products (product_id, category_id, category_name, product_name, product_price, product_status, description)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (product_id, category_id, category_name, product_name, product_price, product_status, description),
            fetch=False
        )

        # OLAP sync
        try:
            execute_query(
                """INSERT INTO dim_product (Product_ID, Product_Category_Id, Product_Category_Name, Product_Name, Product_Price, Product_Status)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (product_id, category_id, category_name, product_name, product_price, product_status),
                fetch=False
            )
        except Exception:
            pass

        # Initialize inventory (default warehouse 1)
        try:
            execute_query(
                """INSERT INTO inventory (product_id, warehouse_id, stock_level, reorder_point, safety_stock, lead_time_days)
                   VALUES (%s, 1, 100, 50, 10, 5)""",
                (product_id,),
                fetch=False
            )
        except Exception:
            pass

        return jsonify({"message": "Product created successfully"}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create product: {str(e)}"}), 500

@products_bp.route("/<int:product_id>", methods=["PUT"])
@admin_required
def update_product(product_id):
    data = request.get_json() or {}

    try:
        existing = execute_query("SELECT product_id FROM products WHERE product_id = %s", (product_id,))
        if not existing:
            return jsonify({"error": "Product not found"}), 404

        fields, params, dim_fields, dim_params = [], [], [], []

        mappings = [
            ("category_id", "Product_Category_Id"),
            ("category_name", "Product_Category_Name"),
            ("product_name", "Product_Name"),
            ("product_price", "Product_Price"),
            ("product_status", "Product_Status"),
        ]
        for oltp_col, olap_col in mappings:
            val = data.get(oltp_col)
            if val is not None:
                fields.append(f"{oltp_col} = %s"); params.append(val)
                dim_fields.append(f"{olap_col} = %s"); dim_params.append(val)

        if data.get("description") is not None:
            fields.append("description = %s"); params.append(data["description"])

        if fields:
            params.append(product_id)
            execute_query(f"UPDATE products SET {', '.join(fields)} WHERE product_id = %s", params, fetch=False)

        if dim_fields:
            dim_params.append(product_id)
            execute_query(f"UPDATE dim_product SET {', '.join(dim_fields)} WHERE Product_ID = %s", dim_params, fetch=False)

        return jsonify({"message": "Product updated successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update product: {str(e)}"}), 500

@products_bp.route("/<int:product_id>", methods=["DELETE"])
@admin_required
def delete_product(product_id):
    try:
        existing = execute_query("SELECT product_id FROM products WHERE product_id = %s", (product_id,))
        if not existing:
            return jsonify({"error": "Product not found"}), 404

        execute_query("DELETE FROM inventory WHERE product_id = %s", (product_id,), fetch=False)
        execute_query("DELETE FROM products WHERE product_id = %s", (product_id,), fetch=False)
        try:
            execute_query("DELETE FROM dim_product WHERE Product_ID = %s", (product_id,), fetch=False)
        except Exception:
            pass
        return jsonify({"message": "Product deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete product: {str(e)}"}), 500

@products_bp.route("/high-risk", methods=["GET"])
@jwt_required()
def get_high_risk_products():
    """Returns products frequently associated with late deliveries or negative profit."""
    try:
        query = """
            SELECT
                p.Product_ID as product_id,
                p.Product_Name as product_name,
                p.Product_Category_Name as category,
                p.Product_Price as price,
                COUNT(f.Fact_ID) as total_orders,
                SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) as high_risk_orders_count,
                ROUND(SUM(CASE WHEN f.Risk_Level = 'High' THEN 1 ELSE 0 END) / COUNT(f.Fact_ID) * 100, 2) as risk_rate_percentage
            FROM dim_product p
            JOIN fact_order f ON p.Product_ID = f.Product_ID
            GROUP BY p.Product_ID, p.Product_Name, p.Product_Category_Name, p.Product_Price
            HAVING risk_rate_percentage > 0
            ORDER BY risk_rate_percentage DESC
            LIMIT 20
        """
        results = execute_query(query)
        return jsonify(results), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch high risk products: {str(e)}"}), 500
