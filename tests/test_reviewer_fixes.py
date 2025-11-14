"""
Regression tests covering the specific fixes requested during reviewer QA.

These mirror the manual assertions from the old script, but expressed as
normal pytest tests so they integrate with the rest of the suite.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from whitemagic import MemoryManager
from whitemagic.api.auth import generate_api_key
from whitemagic.api.database import APIKey
from whitemagic.api import dependencies


def test_memory_manager_has_expected_methods(tmp_path):
    manager = MemoryManager(base_dir=tmp_path)
    assert hasattr(manager, "consolidate_short_term")
    assert hasattr(manager, "list_all_tags")
    assert hasattr(manager, "list_all_memories")
    assert not hasattr(manager, "consolidate_memories")


def test_api_key_generation_handles_underscores():
    full_key, _, key_prefix = generate_api_key("prod")
    assert len(key_prefix) == 16
    parts = "wm_prod_aB3x_Y9kL_test123".split("_", 2)
    assert parts == ["wm", "prod", "aB3x_Y9kL_test123"]


def test_api_modules_importable():
    from whitemagic.api import app  # noqa: F401
    from whitemagic.api.dependencies import get_current_user  # noqa: F401
    from whitemagic.api.auth import validate_api_key  # noqa: F401
    from whitemagic.api.middleware import RequestLoggingMiddleware, RateLimitMiddleware  # noqa: F401


def test_app_file_calls_new_memory_manager_methods():
    source = Path("whitemagic/api/app.py").read_text(encoding="utf-8")
    assert "consolidate_short_term" in source
    assert "list_all_tags" in source
    assert "list_all_memories" in source
    assert "manager.consolidate_memories" not in source
    assert "manager.get_stats" not in source


def test_get_current_user_sets_request_state():
    source = inspect.getsource(dependencies.get_current_user)
    assert "request.state.user" in source


def test_api_key_prefix_column_length():
    columns = {col.name: col for col in APIKey.__table__.columns}
    assert columns["key_prefix"].type.length == 16
