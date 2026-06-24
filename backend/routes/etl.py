"""
routes/etl.py
ETL Pipeline management endpoints.
Provides API access to run the ETL pipeline, check ETL logs,
and retrieve data warehouse status.
"""

import os
import time
import threading
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required
from backend.models.database import execute_query
from backend.middleware.auth_middleware import admin_required

etl_bp = Blueprint("etl", __name__, url_prefix="/api/etl")

# Track running ETL state in memory
_etl_status = {"running": False, "last_result": None}


def _run_etl_in_background():
    """Executes ETL pipeline in a background thread and records result in DB."""
    from backend.etl.run_etl import run_etl_pipeline
    start = time.time()
    log_id = None
    try:
        # Insert in-progress log
        execute_query(
            "INSERT INTO etl_logs (status, records_processed) VALUES (%s, %s)",
            ("RUNNING", 0), fetch=False
        )
        log_rows = execute_query("SELECT LAST_INSERT_ID() as lid")
        log_id = log_rows[0]["lid"] if log_rows else None

        run_etl_pipeline()

        duration = round(time.time() - start, 2)
        if log_id:
            execute_query(
                """UPDATE etl_logs SET status=%s, duration_seconds=%s
                   WHERE id=%s""",
                ("SUCCESS", duration, log_id), fetch=False
            )
        _etl_status["last_result"] = {"status": "SUCCESS", "duration": duration}

    except Exception as e:
        duration = round(time.time() - start, 2)
        if log_id:
            execute_query(
                """UPDATE etl_logs SET status=%s, duration_seconds=%s, error_message=%s
                   WHERE id=%s""",
                ("FAILED", duration, str(e)[:500], log_id), fetch=False
            )
        _etl_status["last_result"] = {"status": "FAILED", "error": str(e)}

    finally:
        _etl_status["running"] = False


@etl_bp.route("/run", methods=["POST"])
@admin_required
def run_etl():
    """
    POST /api/etl/run
    Triggers the full ETL pipeline asynchronously in a background thread.
    Returns immediately with a 202 Accepted response.
    """
    if _etl_status["running"]:
        return jsonify({"message": "ETL pipeline is already running"}), 409

    _etl_status["running"] = True
    thread = threading.Thread(target=_run_etl_in_background, daemon=True)
    thread.start()

    return jsonify({
        "message": "ETL pipeline started. Check /api/etl/status for progress."
    }), 202


@etl_bp.route("/status", methods=["GET"])
@jwt_required()
def get_etl_status():
    """
    GET /api/etl/status
    Returns the current ETL run status and the last execution result.
    """
    return jsonify({
        "running": _etl_status["running"],
        "last_result": _etl_status["last_result"]
    }), 200


@etl_bp.route("/logs", methods=["GET"])
@jwt_required()
def get_etl_logs():
    """
    GET /api/etl/logs?limit=20
    Returns recent ETL execution logs from the database.
    """
    try:
        limit = request.args.get("limit", 20, type=int)
        logs = execute_query(
            f"SELECT * FROM etl_logs ORDER BY run_at DESC LIMIT {int(limit)}"
        )
        for log in logs:
            if log.get("run_at"):
                log["run_at"] = str(log["run_at"])
        return jsonify(logs), 200
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve ETL logs: {str(e)}"}), 500


@etl_bp.route("/generate-data", methods=["POST"])
@admin_required
def generate_mock_data():
    """
    POST /api/etl/generate-data
    Body: { "num_records": int (default 18500) }
    Generates the mock DataCo CSV dataset.
    """
    try:
        data = request.get_json(silent=True) or {}
        num_records = int(data.get("num_records", 18500))
        from backend.etl.generate_mock_data import generate_data
        generate_data(num_records)
        return jsonify({"message": f"Generated {num_records} records in dataset CSV"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to generate data: {str(e)}"}), 500
