"""
routes/reports.py
Report generation API endpoints.
Supports: PDF risk report, Excel multi-sheet report,
          monthly report, yearly report, supplier performance report.
"""

import os
from flask import Blueprint, send_file, jsonify, request
from flask_jwt_extended import jwt_required
from backend.config import Config
from backend.services.report_service import ReportService

reports_bp = Blueprint("reports", __name__, url_prefix="/api/reports")


@reports_bp.route("/pdf", methods=["GET"])
@jwt_required()
def download_pdf_report():
    """
    GET /api/reports/pdf
    Generates and downloads the comprehensive PDF Risk Analysis Report.
    Includes: KPI summary, supplier delays, inventory alerts, high-risk orders.
    """
    try:
        pdf_path = os.path.join(Config.UPLOAD_FOLDER, "supply_chain_report.pdf")
        ReportService.generate_pdf_report(pdf_path)

        if not os.path.exists(pdf_path):
            return jsonify({"error": "PDF generation failed"}), 500

        return send_file(
            pdf_path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="Supply_Chain_Risk_Report.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate PDF: {str(e)}"}), 500


@reports_bp.route("/excel", methods=["GET"])
@jwt_required()
def download_excel_report():
    """
    GET /api/reports/excel
    Generates and downloads a multi-sheet Excel report.
    Sheets: Summary, Supplier Performance, Inventory Alerts, High Risk Orders.
    """
    try:
        excel_path = os.path.join(Config.UPLOAD_FOLDER, "supply_chain_report.xlsx")
        ReportService.generate_excel_report(excel_path)

        if not os.path.exists(excel_path):
            return jsonify({"error": "Excel generation failed"}), 500

        return send_file(
            excel_path,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="Supply_Chain_Risk_Data.xlsx"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate Excel: {str(e)}"}), 500


@reports_bp.route("/risk-summary", methods=["GET"])
@jwt_required()
def download_risk_summary():
    """
    GET /api/reports/risk-summary
    Generates and downloads a focused Risk Summary PDF report.
    """
    try:
        path = os.path.join(Config.UPLOAD_FOLDER, "risk_summary_report.pdf")
        ReportService.generate_risk_summary_pdf(path)

        if not os.path.exists(path):
            return jsonify({"error": "Risk summary PDF generation failed"}), 500

        return send_file(
            path,
            mimetype="application/pdf",
            as_attachment=True,
            download_name="Risk_Summary_Report.pdf"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate risk summary: {str(e)}"}), 500


@reports_bp.route("/supplier-performance", methods=["GET"])
@jwt_required()
def download_supplier_performance():
    """
    GET /api/reports/supplier-performance
    Generates and downloads an Excel Supplier Performance report.
    """
    try:
        path = os.path.join(Config.UPLOAD_FOLDER, "supplier_performance_report.xlsx")
        ReportService.generate_supplier_performance_excel(path)

        if not os.path.exists(path):
            return jsonify({"error": "Supplier report generation failed"}), 500

        return send_file(
            path,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name="Supplier_Performance_Report.xlsx"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate supplier report: {str(e)}"}), 500


@reports_bp.route("/monthly", methods=["GET"])
@jwt_required()
def download_monthly_report():
    """
    GET /api/reports/monthly?year=2023&month=5
    Generates a monthly sales and performance Excel report.
    Defaults to the most recent complete month if not specified.
    """
    try:
        year = request.args.get("year", None, type=int)
        month = request.args.get("month", None, type=int)

        filename = f"monthly_report_{year or 'latest'}_{month or 'latest'}.xlsx"
        path = os.path.join(Config.UPLOAD_FOLDER, filename)
        ReportService.generate_monthly_report_excel(path, year=year, month=month)

        if not os.path.exists(path):
            return jsonify({"error": "Monthly report generation failed"}), 500

        return send_file(
            path,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"Monthly_Report_{year or 'latest'}_{month or 'latest'}.xlsx"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate monthly report: {str(e)}"}), 500


@reports_bp.route("/yearly", methods=["GET"])
@jwt_required()
def download_yearly_report():
    """
    GET /api/reports/yearly?year=2023
    Generates a yearly performance summary Excel report.
    """
    try:
        year = request.args.get("year", None, type=int)

        filename = f"yearly_report_{year or 'all'}.xlsx"
        path = os.path.join(Config.UPLOAD_FOLDER, filename)
        ReportService.generate_yearly_report_excel(path, year=year)

        if not os.path.exists(path):
            return jsonify({"error": "Yearly report generation failed"}), 500

        return send_file(
            path,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=f"Yearly_Report_{year or 'All_Years'}.xlsx"
        )
    except Exception as e:
        return jsonify({"error": f"Failed to generate yearly report: {str(e)}"}), 500
