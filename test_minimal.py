"""
Minimal Flask test — use ONLY to verify localhost works.
Run:  venv\Scripts\python test_minimal.py
Open: http://127.0.0.1:5000

If this works but run.py does not, the issue is in the main app (imports/deps).
If this also fails, the issue is Python/network/firewall — not your OSINT code.
"""

from flask import Flask

app = Flask(__name__)


@app.route("/")
def home():
    return "<h1>Server Working</h1><p>Flask + localhost are OK.</p>"


@app.route("/ping")
def ping():
    return {"status": "ok"}


if __name__ == "__main__":
    print("\n>>> Minimal test server: http://127.0.0.1:5000\n")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False)
