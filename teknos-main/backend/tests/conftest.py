"""
conftest.py — Shared pytest fixtures for SafeWatch AI tests.

Sets up sys.path so tests can import from backend/app without installing.
"""
import sys
from pathlib import Path

# Add backend/ to path so `from app.xxx import yyy` works
BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
