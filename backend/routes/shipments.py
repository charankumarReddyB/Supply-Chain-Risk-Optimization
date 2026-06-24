from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from backend.models.database import execute_query
from datetime import datetime
from backend.middleware.auth_middleware import admin_required

shipments_bp = Blueprint("shipments", __name__, url_prefix="/api/shipments")

@shipments_bp.route("", methods=["GET"])
@jwt_required()
def get_all_shipments():
    try:
        query = """
            SELECT 
                s.shipment_id,
                s.order_id,
                o.order_date,
                s.shipping_date,
                s.shipping_mode,
                s.days_shipping_real,
                s.days_shipment_scheduled,
                s.delivery_status,
                s.late_delivery_risk
            FROM shipments s
            JOIN orders o ON s.order_id = o.order_id
            ORDER BY s.shipping_date DESC
            LIMIT 100
        """
        shipments = execute_query(query)
        for s in shipments:
            if isinstance(s["order_date"], datetime):
                s["order_date"] = s["order_date"].strftime("%Y-%m-%d %H:%M:%S")
            if isinstance(s["shipping_date"], datetime):
                s["shipping_date"] = s["shipping_date"].strftime("%Y-%m-%d %H:%M:%S")
        return jsonify(shipments), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch shipments: {str(e)}"}), 500

@shipments_bp.route("/<int:shipment_id>", methods=["GET"])
@jwt_required()
def get_shipment(shipment_id):
    try:
        query = """
            SELECT 
                s.shipment_id,
                s.order_id,
                o.order_date,
                s.shipping_date,
                s.shipping_mode,
                s.days_shipping_real,
                s.days_shipment_scheduled,
                s.delivery_status,
                s.late_delivery_risk,
                c.fname as customer_fname,
                c.lname as customer_lname,
                p.product_name
            FROM shipments s
            JOIN orders o ON s.order_id = o.order_id
            JOIN customers c ON o.customer_id = c.customer_id
            JOIN products p ON o.product_id = p.product_id
            WHERE s.shipment_id = %s
        """
        shipment = execute_query(query, (shipment_id,))
        if not shipment:
            return jsonify({"error": "Shipment not found"}), 404
            
        ship_dict = shipment[0]
        if isinstance(ship_dict["order_date"], datetime):
            ship_dict["order_date"] = ship_dict["order_date"].strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(ship_dict["shipping_date"], datetime):
            ship_dict["shipping_date"] = ship_dict["shipping_date"].strftime("%Y-%m-%d %H:%M:%S")
            
        return jsonify(ship_dict), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch shipment: {str(e)}"}), 500

@shipments_bp.route("/<int:shipment_id>", methods=["PUT"])
@admin_required
def update_shipment_tracking(shipment_id):
    """Updates shipment with real shipping dates and recalculates delays/delivery status."""
    data = request.get_json() or {}
    days_shipping_real = data.get("days_shipping_real")
    delivery_status = data.get("delivery_status")
    
    if days_shipping_real is None:
        return jsonify({"error": "days_shipping_real field is required"}), 400
        
    try:
        # Check if shipment exists
        shipment = execute_query("SELECT * FROM shipments WHERE shipment_id = %s", (shipment_id,))
        if not shipment:
            return jsonify({"error": "Shipment not found"}), 404
            
        ship_dict = shipment[0]
        scheduled = ship_dict["days_shipment_scheduled"]
        
        # Calculate late delivery risk
        late_risk = 1 if days_shipping_real > scheduled else 0
        
        if not delivery_status:
            if late_risk == 1:
                delivery_status = "Late delivery"
            else:
                delivery_status = "Shipping on time"
                
        # Update shipment table
        execute_query(
            """UPDATE shipments 
               SET days_shipping_real = %s, delivery_status = %s, late_delivery_risk = %s 
               WHERE shipment_id = %s""",
            (days_shipping_real, delivery_status, late_risk, shipment_id),
            fetch=False
        )
        
        # Sync with Data Warehouse (OLAP)
        order_id = ship_dict["order_id"]
        
        # Get shipping parameters to update fact table
        shipping_mode = ship_dict["shipping_mode"]
        
        # Find if dim_shipping entry exists
        dim_ship = execute_query(
            """SELECT Shipping_ID FROM dim_shipping 
               WHERE Shipping_Mode = %s AND Delivery_Status = %s 
                 AND Shipping_Date_Real_Days = %s AND Shipping_Date_Scheduled_Days = %s""",
            (shipping_mode, delivery_status, days_shipping_real, scheduled)
        )
        
        if dim_ship:
            shipping_id = dim_ship[0]["Shipping_ID"]
        else:
            execute_query(
                """INSERT INTO dim_shipping (Shipping_Mode, Delivery_Status, Shipping_Date_Real_Days, Shipping_Date_Scheduled_Days) 
                   VALUES (%s, %s, %s, %s)""",
                (shipping_mode, delivery_status, days_shipping_real, scheduled),
                fetch=False
            )
            shipping_id_res = execute_query("SELECT LAST_INSERT_ID() as last_id")
            shipping_id = shipping_id_res[0]["last_id"]
            
        # Recalculate risk level for fact_order
        delay = days_shipping_real - scheduled
        
        # Fetch profit
        order_info = execute_query("SELECT profit FROM orders WHERE order_id = %s", (order_id,))
        profit = float(order_info[0]["profit"]) if order_info else 0.0
        
        if delay > 0 and profit < 0:
            risk_level = "High"
        elif delay > 0 or profit < 0:
            risk_level = "Medium"
        else:
            risk_level = "Low"
            
        # Update fact table
        execute_query(
            """UPDATE fact_order 
               SET Shipping_ID = %s, Delivery_Delay = %s, Risk_Level = %s 
               WHERE Order_ID = %s""",
            (shipping_id, delay, risk_level, order_id),
            fetch=False
        )
        
        return jsonify({
            "message": "Shipment updated successfully and synchronized with Data Warehouse",
            "late_risk": late_risk,
            "risk_level": risk_level
        }), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update shipment: {str(e)}"}), 500
