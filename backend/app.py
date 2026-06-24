"""
app.py
Supply Chain Risk Analysis & Optimization - Flask Application Entry Point.
Registers all Blueprints and initializes extensions.
"""

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


def create_app(config_class=None):
    if config_class is None:
        from backend.config import Config
        config_class = Config

    app = Flask(__name__)
    app.config.from_object(config_class)

    # ─── Extensions ──────────────────────────────────────────────────────────

    # Enable CORS for all /api/* routes
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Initialize JWT Manager
    jwt = JWTManager(app)

    # JWT Error Handlers
    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired", "sub_status": "token_expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"error": "Invalid token signature", "sub_status": "token_invalid"}), 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"error": "Access token required", "sub_status": "token_missing"}), 401

    # ─── Blueprint Registration ───────────────────────────────────────────────

    from backend.routes.auth         import auth_bp
    from backend.routes.dashboard    import dashboard_bp
    from backend.routes.suppliers    import suppliers_bp
    from backend.routes.products     import products_bp
    from backend.routes.inventory    import inventory_bp
    from backend.routes.orders       import orders_bp
    from backend.routes.shipments    import shipments_bp
    from backend.routes.warehouse    import warehouse_bp
    from backend.routes.risk         import risk_bp
    from backend.routes.optimization import optimization_bp
    from backend.routes.analytics    import analytics_bp
    from backend.routes.reports      import reports_bp
    from backend.routes.etl          import etl_bp
    from backend.routes.monte_carlo  import mc_bp
    from backend.routes.cost         import cost_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(suppliers_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(orders_bp)
    app.register_blueprint(shipments_bp)
    app.register_blueprint(warehouse_bp)
    app.register_blueprint(risk_bp)
    app.register_blueprint(optimization_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(etl_bp)
    app.register_blueprint(mc_bp)
    app.register_blueprint(cost_bp)

    # ─── Database Migrations (Profile Columns) ────────────────────────────────
    with app.app_context():
        try:
            from backend.models.database import execute_query
            for col, col_type in [
                ("full_name", "VARCHAR(100) DEFAULT NULL"),
                ("phone", "VARCHAR(50) DEFAULT NULL"),
                ("location", "VARCHAR(100) DEFAULT NULL"),
                ("department", "VARCHAR(100) DEFAULT NULL"),
                ("employee_id", "VARCHAR(50) DEFAULT NULL")
            ]:
                try:
                    execute_query(f"ALTER TABLE users ADD COLUMN {col} {col_type}", fetch=False)
                except Exception:
                    # Column already exists or table not ready
                    pass
        except Exception as e:
            app.logger.warning(f"Failed to verify user profile columns: {e}")

    # ─── Global Routes ────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return jsonify({
            "status": "online",
            "message": "Supply Chain Risk Analysis & Optimization Backend is running.",
            "version": "1.0.0",
            "endpoints": {
                "auth":         "/api/auth",
                "dashboard":    "/api/dashboard",
                "analytics":    "/api/analytics",
                "suppliers":    "/api/suppliers",
                "products":     "/api/products",
                "inventory":    "/api/inventory",
                "orders":       "/api/orders",
                "shipments":    "/api/shipments",
                "warehouses":   "/api/warehouses",
                "risk":         "/api/risk",
                "optimization": "/api/optimization",
                "reports":      "/api/reports",
                "etl":          "/api/etl",
                "monte_carlo":  "/api/monte-carlo"
            }
        }), 200

    # ─── Global Error Handlers ────────────────────────────────────────────────

    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "details": str(error)}), 400

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({"error": "Method not allowed"}), 405

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
