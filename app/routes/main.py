"""
Frontend routes — serves the main SPA-style dashboard.
"""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Render the OSINT Username Finder dashboard."""
    return render_template("index.html")
