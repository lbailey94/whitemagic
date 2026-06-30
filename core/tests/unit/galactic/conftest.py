"""
Conftest for the galactic tests.

The top-level tests/conftest.py sets WM_STATE_ROOT to a temp dir, which
isolates most tests from the live substrate DB. The galactic tests are
the exception: they're integration tests against the actual substrate
at ~/.whitemagic/memory/whitemagic.db.

This conftest sets WM_MEMORY_DB to the live path for tests in this
directory so galactic._resolve_db_path() resolves to the real DB.
"""

import os
from pathlib import Path

import pytest

LIVE_SUBSTRATE_DB = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"


@pytest.fixture(autouse=True)
def use_live_substrate(monkeypatch):
    """Force tests in this directory to use the live substrate DB."""
    if LIVE_SUBSTRATE_DB.exists():
        monkeypatch.setenv("WM_MEMORY_DB", str(LIVE_SUBSTRATE_DB))
    monkeypatch.delenv("WM_STATE_ROOT", raising=False)
    yield
