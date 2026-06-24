from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.database import execute_query
from datetime import datetime
from backend.middleware.auth_middleware import admin_required

orders_bp = Blueprint("orders", __name__, url_prefix="/api/orders")

@orders_bp.route("", methods=["GET"])
@jwt_required()
def get_all_orders():
    try:
        # Fetch detailed order list joining customer and product
        query = """
            SELECT 
                o.order_id,
                o.customer_id,
                c.fname as customer_fname,
                c.lname as customer_lname,
                o.product_id,
                p.product_name,
                o.quantity,
                o.sales,
                o.profit,
                o.order_date,
                o.order_status,
                o.payment_type
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN products p ON o.product_id = p.product_id
            ORDER BY o.order_date DESC
            LIMIT 100
        """
        orders = execute_query(query)
        # Format date for JSON and add currency
        for o in orders:
            if isinstance(o["order_date"], datetime):
                o["order_date"] = o["order_date"].strftime("%Y-%m-%d %H:%M:%S")
            o["currency"] = "INR"
        return jsonify(orders), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch orders: {str(e)}"}), 500

@orders_bp.route("/<int:order_id>", methods=["GET"])
@jwt_required()
def get_order_details(order_id):
    try:
        query = """
            SELECT 
                o.order_id,
                o.customer_id,
                c.fname as customer_fname,
                c.lname as customer_lname,
                o.product_id,
                p.product_name,
                o.quantity,
                o.sales,
                o.profit,
                o.order_date,
                o.order_status,
                o.payment_type
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN products p ON o.product_id = p.product_id
            WHERE o.order_id = %s
        """
        order = execute_query(query, (order_id,))
        if not order:
            return jsonify({"error": "Order not found"}), 404
            
        order_dict = order[0]
        if isinstance(order_dict["order_date"], datetime):
            order_dict["order_date"] = order_dict["order_date"].strftime("%Y-%m-%d %H:%M:%S")
        order_dict["currency"] = "INR"
            
        # Get shipment info if available
        shipment = execute_query("SELECT * FROM shipments WHERE order_id = %s", (order_id,))
        if shipment:
            shipment_dict = shipment[0]
            if isinstance(shipment_dict["shipping_date"], datetime):
                shipment_dict["shipping_date"] = shipment_dict["shipping_date"].strftime("%Y-%m-%d %H:%M:%S")
            order_dict["shipment"] = shipment_dict
        else:
            order_dict["shipment"] = None
            
        return jsonify(order_dict), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch order: {str(e)}"}), 500

@orders_bp.route("", methods=["POST"])
@admin_required
def create_order():
    data = request.get_json() or {}
    order_id = data.get("order_id")
    customer_id = data.get("customer_id")
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)
    sales = data.get("sales")
    profit = data.get("profit")
    order_date = data.get("order_date")
    order_status = data.get("order_status", "PENDING")
    payment_type = data.get("payment_type", "DEBIT")
    
    # Shipment parameters if requested to create shipment
    shipping_mode = data.get("shipping_mode", "Standard Class")
    days_shipment_scheduled = data.get("days_shipment_scheduled", 4)
    
    if not order_id:
        try:
            max_id_res = execute_query("SELECT MAX(order_id) as max_id FROM orders")
            max_id = max_id_res[0]["max_id"] if max_id_res and max_id_res[0]["max_id"] is not None else 200000
            order_id = max_id + 1
        except Exception as e:
            return jsonify({"error": f"Failed to auto-generate order_id: {str(e)}"}), 500

    if not customer_id or not product_id or sales is None or profit is None:
        return jsonify({"error": "customer_id, product_id, sales, and profit are required"}), 400
        
    try:
        # Check order_id uniqueness
        existing = execute_query("SELECT order_id FROM orders WHERE order_id = %s", (order_id,))
        if existing:
            return jsonify({"error": f"Order with ID {order_id} already exists"}), 400
            
        # Verify customer and product exist
        cust = execute_query("SELECT customer_id FROM customers WHERE customer_id = %s", (customer_id,))
        if not cust:
            return jsonify({"error": "Customer not found"}), 404
        prod = execute_query("SELECT product_id, category_id, category_name, product_price FROM products WHERE product_id = %s", (product_id,))
        if not prod:
            return jsonify({"error": "Product not found"}), 404
            
        # Parse date
        if not order_date:
            order_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        else:
            order_date_str = order_date
            
        # Insert OLTP order
        execute_query(
            """INSERT INTO orders (order_id, customer_id, product_id, quantity, sales, profit, order_date, order_status, payment_type) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (order_id, customer_id, product_id, quantity, sales, profit, order_date_str, order_status, payment_type),
            fetch=False
        )
        
        # Create default shipment in OLTP
        from datetime import timedelta as _td
        ship_date = datetime.now() + _td(days=days_shipment_scheduled)
        ship_date_str = ship_date.strftime("%Y-%m-%d %H:%M:%S")
        
        execute_query(
            """INSERT INTO shipments (order_id, shipping_date, shipping_mode, days_shipping_real, days_shipment_scheduled, delivery_status, late_delivery_risk) 
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (order_id, ship_date_str, shipping_mode, None, days_shipment_scheduled, "Shipping on time", 0),
            fetch=False
        )
        
        # We will also insert this into the Star Schema if desired, but running the ETL pipeline is the primary way to populate OLAP.
        # For immediate updates, we can populate OLAP tables here too:
        date_obj = datetime.strptime(order_date_str, "%Y-%m-%d %H:%M:%S") if " " in order_date_str else datetime.strptime(order_date_str, "%Y-%m-%d")
        date_id = int(date_obj.strftime("%Y%m%d"))
        
        # Ensure date entry exists
        existing_date = execute_query("SELECT Date_ID FROM dim_date WHERE Date_ID = %s", (date_id,))
        if not existing_date:
            execute_query(
                """INSERT INTO dim_date (Date_ID, Full_Date, Day, Month, Year, Quarter, Month_Name, Day_Of_Week) 
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (date_id, date_obj.date().strftime("%Y-%m-%d"), date_obj.day, date_obj.month, date_obj.year, 
                 (date_obj.month - 1) // 3 + 1, date_obj.strftime("%B"), date_obj.strftime("%A")),
                fetch=False
            )
            
        # Create a dim_shipping record for this shipment
        execute_query(
            """INSERT INTO dim_shipping (Shipping_Mode, Delivery_Status, Shipping_Date_Real_Days, Shipping_Date_Scheduled_Days) 
               VALUES (%s, %s, %s, %s)""",
            (shipping_mode, "Shipping on time", 0, days_shipment_scheduled),
            fetch=False
        )
        shipping_id_res = execute_query("SELECT LAST_INSERT_ID() as last_id")
        shipping_id = shipping_id_res[0]["last_id"]
        
        # Determine risk level
        risk_level = "Low" # Defaults to low since not shipped yet
        
        supplier_id = (product_id % 5) + 1
        warehouse_id = (product_id % 3) + 1
        
        # Insert OLAP fact record
        execute_query(
            """INSERT INTO fact_order (Order_ID, Customer_ID, Product_ID, Supplier_ID, Warehouse_ID, Date_ID, Shipping_ID, Quantity, Sales, Profit, Delivery_Delay, Risk_Level) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (order_id, customer_id, product_id, supplier_id, warehouse_id, date_id, shipping_id, quantity, sales, profit, 0, risk_level),
            fetch=False
        )
        
        # Adjust stock levels in Inventory
        execute_query(
            "UPDATE inventory SET stock_level = stock_level - %s WHERE product_id = %s",
            (quantity, product_id),
            fetch=False
        )
        
        return jsonify({"message": "Order created successfully", "order_id": order_id}), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create order: {str(e)}"}), 500

@orders_bp.route("/<int:order_id>", methods=["PUT"])
@admin_required
def update_order_status(order_id):
    data = request.get_json() or {}
    order_status = data.get("order_status")
    
    if not order_status:
        return jsonify({"error": "order_status field is required"}), 400
        
    try:
        existing = execute_query("SELECT order_id FROM orders WHERE order_id = %s", (order_id,))
        if not existing:
            return jsonify({"error": "Order not found"}), 404
            
        execute_query("UPDATE orders SET order_status = %s WHERE order_id = %s", (order_status, order_id), fetch=False)
        return jsonify({"message": f"Order status updated to {order_status}"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update order: {str(e)}"}), 500

@orders_bp.route("/<int:order_id>", methods=["DELETE"])
@admin_required
def delete_order(order_id):
    try:
        existing = execute_query("SELECT order_id FROM orders WHERE order_id = %s", (order_id,))
        if not existing:
            return jsonify({"error": "Order not found"}), 404
            
        execute_query("DELETE FROM orders WHERE order_id = %s", (order_id,), fetch=False)
        # Note: cascading deletes are handled by foreign keys
        return jsonify({"message": "Order deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete order: {str(e)}"}), 500
