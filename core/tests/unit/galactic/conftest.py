"""
Conftest for the galactic tests.

The top-level tests/conftest.py sets WM_STATE_ROOT to a temp dir, which
isolates most tests from the live substrate DB. The galactic tests are
integration tests that need a realistic substrate schema with data.

Instead of using the live production DB in-place (which gets corrupted by
concurrent raw sqlite3.connect() calls from other tests during the full
suite run), we copy it to a temp directory once per session and run all
galactic tests against the copy in read-only mode.
"""

import os
import shutil
from pathlib import Path

import pytest

LIVE_SUBSTRATE_DB = Path.home() / ".whitemagic" / "memory" / "whitemagic.db"


@pytest.fixture(scope="session")
def _substrate_copy(tmp_path_factory):
    """Copy the live substrate DB to a temp dir once per session."""
    tmp_dir = tmp_path_factory.mktemp("galactic_substrate")
    tmp_db = tmp_dir / "whitemagic.db"
    if LIVE_SUBSTRATE_DB.exists():
        # Use SQLite backup API for a safe, consistent copy
        import sqlite3

        src = sqlite3.connect(str(LIVE_SUBSTRATE_DB))
        dst = sqlite3.connect(str(tmp_db))
        src.backup(dst)
        src.close()
        dst.close()
    return tmp_db


@pytest.fixture(autouse=True)
def use_live_substrate(monkeypatch, _substrate_copy):
    """Point galactic tests at a temp copy of the substrate DB."""
    if _substrate_copy.exists():
        monkeypatch.setenv("WM_MEMORY_DB", str(_substrate_copy))
    monkeypatch.delenv("WM_STATE_ROOT", raising=False)
    yield
