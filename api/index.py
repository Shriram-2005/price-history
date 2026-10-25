"""Vercel Serverless Function entrypoint for FastAPI."""

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.web.server import app

@app.middleware("http")
async def normalize_vercel_path(request, call_next):
    """Normalizes path across Vercel serverless rewrites."""
    path = request.scope.get("path", "")
    if path.startswith("/api/index.py"):
        sub = path[len("/api/index.py"):]
        request.scope["path"] = sub if sub else "/"
    return await call_next(request)
