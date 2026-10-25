"""Vercel Serverless Function entrypoint for FastAPI."""

import sys
from pathlib import Path

# Ensure root workspace is in sys.path
ROOT_DIR = Path(__file__).parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.web.server import app
