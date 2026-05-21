"""
Application configuration loaded from environment variables.
Copy .env.example to .env and adjust values for your environment.
"""

import os
from pathlib import Path

# Base directory (project root)
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Central configuration for the OSINT Username Finder."""

    # Flask
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me-in-production")
    # Never enable debug on Render / production hosts
    _on_render = os.environ.get("RENDER", "").lower() in ("true", "1", "yes")
    _prod = os.environ.get("FLASK_ENV", "").lower() == "production"
    DEBUG = (
        os.getenv("FLASK_DEBUG", "false").lower() == "true"
        and not _on_render
        and not _prod
    )

    # Database (SQLite)
    DATABASE_PATH = os.getenv(
        "DATABASE_PATH",
        str(BASE_DIR / "instance" / "osint.db"),
    )

    # Async username checker
    MAX_CONCURRENT_REQUESTS = int(os.getenv("MAX_CONCURRENT_REQUESTS", "25"))
    REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "10"))
    USER_AGENT = os.getenv(
        "USER_AGENT",
        "OSINT-Username-Finder/1.0 (Educational Research Tool)",
    )

    # Rate limiting (requests per minute per IP)
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "10 per minute")
    RATE_LIMIT_SEARCH = os.getenv("RATE_LIMIT_SEARCH", "5 per minute")

    # Screenshots (Playwright — optional, slower)
    SCREENSHOTS_ENABLED = os.getenv("SCREENSHOTS_ENABLED", "true").lower() == "true"
    SCREENSHOTS_DIR = os.getenv(
        "SCREENSHOTS_DIR",
        str(BASE_DIR / "screenshots"),
    )
    SCREENSHOT_TIMEOUT = int(os.getenv("SCREENSHOT_TIMEOUT", "15000"))

    # Export files
    EXPORTS_DIR = os.getenv("EXPORTS_DIR", str(BASE_DIR / "exports"))

    # Sites definition file
    SITES_JSON = os.getenv(
        "SITES_JSON",
        str(BASE_DIR / "app" / "data" / "sites.json"),
    )
