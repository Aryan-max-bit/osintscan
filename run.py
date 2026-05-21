"""
Entry point for the OSINT Username Finder application.

Local development:
    venv\\Scripts\\activate
    python run.py

Production (Render / PaaS) — use Gunicorn (see render.yaml):
    gunicorn --bind 0.0.0.0:$PORT run:app
"""

import os
import sys

from dotenv import load_dotenv

# Load .env for local dev only; Render injects env vars directly
load_dotenv()

from app import create_app
from app.config import Config

app = create_app()


def is_render() -> bool:
    """True when running on Render.com (sets RENDER=true)."""
    return os.environ.get("RENDER", "").lower() in ("true", "1", "yes")


def is_production() -> bool:
    """True for cloud deployment (Render, etc.)."""
    return is_render() or os.environ.get("FLASK_ENV", "").lower() == "production"


def get_port() -> int:
    """
    Port for the HTTP server.
    Render injects PORT; local default is 5000 (from .env or fallback).
    """
    return int(os.environ.get("PORT", "5000"))


def get_host() -> str:
    """
    Bind address:
    - Render / production: 0.0.0.0 (required for external traffic)
    - Local dev: 127.0.0.1 (override with HOST in .env)
    """
    if is_production():
        return "0.0.0.0"
    return os.getenv("HOST", "127.0.0.1")


if __name__ == "__main__":
    port = get_port()
    host = get_host()
    debug = Config.DEBUG and not is_production()
    use_reloader = (
        debug
        and os.getenv("FLASK_USE_RELOADER", "false").lower() == "true"
        and not is_production()
    )

    print("\n" + "=" * 50)
    print("  OSINT Username Finder")
    print("=" * 50)
    print(f"  Mode:   {'production' if is_production() else 'local dev'}")
    print(f"  Bind:   {host}:{port}")
    if host == "127.0.0.1":
        print(f"  Open:   http://127.0.0.1:{port}")
        print(f"          http://localhost:{port}")
    else:
        print(f"  Open:   http://0.0.0.0:{port} (all interfaces)")
    print("  Stop:   Ctrl+C")
    print("=" * 50 + "\n")

    if is_production():
        print(
            "NOTE: On Render, use the Gunicorn start command from render.yaml, "
            "not 'python run.py'.\n"
        )

    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            use_reloader=use_reloader,
        )
    except OSError as e:
        if "address already in use" in str(e).lower() or getattr(e, "winerror", None) == 10048:
            print(f"\nERROR: Port {port} is already in use.")
            print("  Fix: set PORT=5001 in .env, then restart.")
            sys.exit(1)
        raise
