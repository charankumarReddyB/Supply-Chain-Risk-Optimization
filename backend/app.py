"""
app.py
Supply Chain Risk Analysis & Optimization - Flask Application Entry Point.
Registers all Blueprints and initializes extensions.
"""

import os
import sys
import logging

# Bootstrap sys.path to support both module and script executions
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(current_dir)
repo_root = os.path.abspath(os.path.join(backend_dir, ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

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

    # Enable CORS for all /api/* routes, allowing all origins for robust deployment
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Initialize JWT Manager (with production secret check at runtime startup)
    jwt_key = app.config.get("JWT_SECRET_KEY")
    if os.environ.get("FLASK_ENV", "development").lower() == "production":
        if not jwt_key or jwt_key == "fallback-dev-key-change-in-production":
            raise RuntimeError("JWT_SECRET_KEY environment variable must be set to a secure key in production.")
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

    # ─── Database Migrations & Auto-initialization ────────────────────────────
    with app.app_context():
        try:
            from backend.models.database import get_db_connection, execute_query
            
            # Check if database is reachable (with retries for database cold starts)
            db_reachable = False
            for attempt in range(5):
                try:
                    conn = get_db_connection()
                    conn.close()
                    db_reachable = True
                    break
                except Exception as conn_err:
                    app.logger.warning(f"Database connection attempt {attempt+1} failed: {conn_err}. Retrying in 3 seconds...")
                    import time
                    time.sleep(3)
            
            if not db_reachable:
                app.logger.warning("Database server is unreachable. Skipping auto-initialization and migrations.")

            if db_reachable:
                from backend.models.database import acquire_db_lock, release_db_lock

                def check_database_needs_init():
                    try:
                        # Check if users table exists and has data
                        res = execute_query("SELECT COUNT(*) as count FROM users")
                        if not res or res[0]["count"] == 0:
                            return True
                        # Check if products table exists and has data
                        res = execute_query("SELECT COUNT(*) as count FROM products")
                        if not res or res[0]["count"] == 0:
                            return True
                        # Check if orders table exists and has data
                        res = execute_query("SELECT COUNT(*) as count FROM orders")
                        if not res or res[0]["count"] == 0:
                            return True
                        # Check if fact_order table exists and has data
                        res = execute_query("SELECT COUNT(*) as count FROM fact_order")
                        if not res or res[0]["count"] == 0:
                            return True
                        return False
                    except Exception:
                        # If any table doesn't exist, we need initialization
                        return True

                needs_init = check_database_needs_init()
                if needs_init:
                    app.logger.info("Database is empty or missing core tables. Attempting to initialize...")
                    lock_acquired = False
                    for attempt in range(6):  # Wait up to 30 seconds
                        lock_acquired = acquire_db_lock()
                        if lock_acquired:
                            break
                        app.logger.info("Database initialization lock is held by another process. Waiting...")
                        import time
                        time.sleep(5)
                        # Re-check if the other process completed initialization
                        if not check_database_needs_init():
                            needs_init = False
                            break
                    
                    if lock_acquired and needs_init:
                        app.logger.info("Database is empty or missing core tables. Initializing in background to prevent port scan timeouts...")
                        def run_init_background(app_ctx):
                            with app_ctx:
                                try:
                                    from backend.utils.init_system import init_system
                                    init_system(skip_db_errors=False)
                                    app.logger.info("Database initialization and ETL seeding completed successfully!")
                                except Exception as init_err:
                                    app.logger.error(f"Failed to auto-initialize database on startup: {init_err}")
                                finally:
                                    release_db_lock()

                        import threading
                        threading.Thread(target=run_init_background, args=(app.app_context(),)).start()
                else:
                    app.logger.info("Database is already initialized. Running profile column migrations if needed...")
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
                            # Column already exists
                            pass

                # Check default admin credentials in production
                if os.environ.get("FLASK_ENV", "development").lower() == "production" and not needs_init:
                    try:
                        from werkzeug.security import check_password_hash
                        admin_user = execute_query("SELECT password_hash FROM users WHERE username = 'admin'")
                        if admin_user:
                            db_hash = admin_user[0]["password_hash"]
                            if check_password_hash(db_hash, "admin123"):
                                app.logger.warning(
                                    "\n"
                                    "======================================================================\n"
                                    "SECURITY WARNING: The 'admin' account is still using the default\n"
                                    "password ('admin123'). Please change it immediately in production!\n"
                                    "======================================================================\n"
                                )
                    except Exception as err:
                        app.logger.warning(f"Could not perform default credentials verification check: {err}")
        except Exception as e:
            app.logger.warning(f"Failed to verify database status or apply migrations: {e}")

    # ─── Global Routes ────────────────────────────────────────────────────────

    @app.route("/")
    def index():
        return jsonify({
            "status": "online",
            "message": "Supply Chain Risk Analysis & Optimization Backend is running.",
            "version": "1.0.1-v3",
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


# Create global app instance for WSGI servers like Gunicorn
app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
