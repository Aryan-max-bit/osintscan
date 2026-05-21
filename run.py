"""
Entry point for the OSINT Username Finder application.

Start the server (from project folder):
    venv\\Scripts\\activate
    python run.py

Do NOT use "python app.py" — that file does not exist in this project.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from app import create_app
from app.config import Config

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    # 127.0.0.1 is safest for local dev on Windows (avoids some firewall quirks)
    host = os.getenv("HOST", "127.0.0.1")
    debug = Config.DEBUG
    # Windows + debug reloader often causes brief "can't be reached" during restarts
    use_reloader = debug and os.getenv("FLASK_USE_RELOADER", "false").lower() == "true"

    print("\n" + "=" * 50)
    print("  OSINT Username Finder")
    print("=" * 50)
    print(f"  Starting on http://127.0.0.1:{port}")
    print(f"  Also try:     http://localhost:{port}")
    print("  Stop server:  Ctrl+C in this terminal")
    print("=" * 50 + "\n")

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
            print(f"  Fix: set PORT=5001 in .env, then open http://127.0.0.1:5001")
            sys.exit(1)
        raise
