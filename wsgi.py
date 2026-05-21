"""
WSGI entry point for production servers (Gunicorn, Render, etc.).

Usage:
    gunicorn --bind 0.0.0.0:8000 wsgi:app
    gunicorn --bind 0.0.0.0:$PORT wsgi:app   # Render
"""

from dotenv import load_dotenv

load_dotenv()

from app import create_app

app = create_app()
