"""
AI Company OS - CEO Control Center

Entry point for the web dashboard.  Starts a local FastAPI server at
http://127.0.0.1:8000.

Usage:
    python apps/dashboard/main.py
or:
    set PYTHONPATH=C:\\Projects\\AI-Company-OS
    .venv\\Scripts\\python.exe apps/dashboard/main.py
"""

import os
import sys

# Ensure the project root is on the Python path when run directly.
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from apps.dashboard.routes import create_router

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="AI Company OS - CEO Control Center",
        description="Real-time dashboard for monitoring AI Company OS operations",
        version="1.0.0",
    )

    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    templates = Jinja2Templates(directory=_TEMPLATES_DIR)

    router = create_router(templates)
    app.include_router(router)

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "apps.dashboard.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
    )
