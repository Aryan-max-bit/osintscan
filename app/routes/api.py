"""
REST API routes for username search, history, stats, and exports.
"""

import os
import re
from pathlib import Path

from flask import Blueprint, jsonify, request, send_from_directory

from app.extensions import limiter
from app.config import Config
from app.models import database as db
from app.services import checker, export, screenshot

api_bp = Blueprint("api", __name__, url_prefix="/api")


def _validate_username(username: str) -> tuple[bool, str]:
    """Basic username validation."""
    if not username or len(username) < 2:
        return False, "Username must be at least 2 characters."
    if len(username) > 32:
        return False, "Username must be 32 characters or fewer."
    if not re.match(r"^[a-zA-Z0-9._\-]+$", username):
        return False, "Username may only contain letters, numbers, dots, underscores, and hyphens."
    return True, ""


@api_bp.route("/health", methods=["GET"])
def health():
    """Health check endpoint for monitoring."""
    return jsonify({"status": "ok", "service": "osint-username-finder"})


@api_bp.route("/stats", methods=["GET"])
def stats():
    """Dashboard aggregate statistics."""
    try:
        return jsonify(db.get_dashboard_stats())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/history", methods=["GET"])
def history():
    """Recent search history."""
    limit = min(int(request.args.get("limit", 20)), 100)
    try:
        return jsonify({"history": db.get_search_history(limit)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/history/<int:search_id>", methods=["GET"])
def history_detail(search_id: int):
    """Single search with full results."""
    data = db.get_search_by_id(search_id)
    if not data:
        return jsonify({"error": "Search not found"}), 404
    return jsonify(data)


@api_bp.route("/search", methods=["POST"])
@limiter.limit(Config.RATE_LIMIT_SEARCH)
def search():
    """
    Main search endpoint.
    Body JSON: { "username": "...", "screenshots": true|false }
    """
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    want_screenshots = data.get("screenshots", Config.SCREENSHOTS_ENABLED)

    valid, msg = _validate_username(username)
    if not valid:
        return jsonify({"error": msg}), 400

    try:
        results = checker.check_username(username)

        if want_screenshots and Config.SCREENSHOTS_ENABLED:
            results = screenshot.capture_screenshots(username, results)

        search_id = db.save_search(username, results)

        summary = {
            "total": len(results),
            "found": sum(1 for r in results if r["status"] == "found"),
            "not_found": sum(1 for r in results if r["status"] == "not_found"),
            "errors": sum(1 for r in results if r["status"] == "error"),
        }

        return jsonify({
            "search_id": search_id,
            "username": username,
            "summary": summary,
            "results": results,
        })
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        return jsonify({"error": f"Search failed: {str(e)}"}), 500


@api_bp.route("/export/json", methods=["POST"])
def export_json_route():
    """Export provided results or load by search_id."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "unknown")
    results = data.get("results")
    search_id = data.get("search_id")

    if not results and search_id:
        stored = db.get_search_by_id(search_id)
        if not stored:
            return jsonify({"error": "Search not found"}), 404
        username = stored["search"]["username"]
        results = [
            {
                "site_name": r["site_name"],
                "url": r["url"],
                "status": r["status"],
                "response_time_ms": r["response_time_ms"],
                "screenshot_path": r.get("screenshot_path"),
            }
            for r in stored["results"]
        ]

    if not results:
        return jsonify({"error": "No results to export"}), 400

    try:
        meta = export.export_json(username, results, search_id)
        return jsonify(meta)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/export/pdf", methods=["POST"])
def export_pdf_route():
    """Generate PDF report."""
    data = request.get_json(silent=True) or {}
    username = data.get("username", "unknown")
    results = data.get("results")
    search_id = data.get("search_id")

    if not results and search_id:
        stored = db.get_search_by_id(search_id)
        if not stored:
            return jsonify({"error": "Search not found"}), 404
        username = stored["search"]["username"]
        results = [
            {
                "site_name": r["site_name"],
                "url": r["url"],
                "status": r["status"],
                "response_time_ms": r["response_time_ms"],
            }
            for r in stored["results"]
        ]

    if not results:
        return jsonify({"error": "No results to export"}), 400

    try:
        meta = export.export_pdf(username, results, search_id)
        return jsonify(meta)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/export/download/<filename>", methods=["GET"])
def download_export(filename: str):
    """Serve exported JSON/PDF files."""
    if ".." in filename or "/" in filename or "\\" in filename:
        return jsonify({"error": "Invalid filename"}), 400
    exports_dir = Path(Config.EXPORTS_DIR)
    filepath = exports_dir / filename
    if not filepath.exists():
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(
        str(exports_dir),
        filename,
        as_attachment=True,
    )


@api_bp.route("/sites/count", methods=["GET"])
def sites_count():
    """Return number of configured platforms."""
    try:
        sites = checker.load_sites()
        return jsonify({"count": len(sites)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
