# ruff: noqa: BLE001
"""
WhiteMagic Storage Module — Multiple storage backends.

Provides SQLite (default, high performance) and JSON (legacy, portable) backends.
"""

from __future__ import annotations

from .sqlite_backend import SQLiteBackend, get_backend

__all__ = ["SQLiteBackend", "get_backend"]
