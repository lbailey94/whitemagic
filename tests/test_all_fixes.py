"""
Regression tests that mirror the manual checklist from TEST_ALL_FIXES.md.

Each test is intentionally small and focused on a single guarantee that used
to break during reviewer fixes: method names, middleware wiring, webhook
logging, etc. Keeping them as normal pytest tests means they run (and fail)
like the rest of the suite instead of relying on print statements or sys.exit.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from whitemagic import MemoryManager
from whitemagic.api.database import APIKey, Quota, UsageRecord, User
from whitemagic.api.rate_limit import (
    PLAN_LIMITS,
    RateLimiter,
    check_quota_limits,
    update_quota_in_db,
)

APP_PATH = Path("whitemagic/api/app.py")
MIDDLEWARE_PATH = Path("whitemagic/api/middleware.py")
MCP_TEST_PATH = Path("tests/test_mcp_integration.py")


def test_memory_manager_methods(tmp_path):
    manager = MemoryManager(base_dir=tmp_path)
    listing = manager.list_all_memories()
    assert isinstance(listing, dict)
    assert "short_term" in listing and "long_term" in listing
    assert hasattr(manager, "consolidate_short_term")
    assert hasattr(manager, "list_all_tags")


def test_app_uses_asyncio_to_thread():
    source = APP_PATH.read_text(encoding="utf-8")
    assert "import asyncio" in source
    assert "asyncio.to_thread" in source


def test_rate_limit_middleware_registered():
    source = APP_PATH.read_text(encoding="utf-8")
    assert "app.add_middleware(RateLimitMiddleware)" in source


def test_usage_logging_writes_records():
    source = MIDDLEWARE_PATH.read_text(encoding="utf-8")
    assert "UsageRecord" in source
    assert "session.add(usage)" in source


def test_quota_updates_invoked():
    source = MIDDLEWARE_PATH.read_text(encoding="utf-8")
    assert "update_quota_in_db" in source


# Whop integration tests removed - feature deprecated
# Tests for webhook_logging and webhook_secret were here


def test_mcp_tests_close_process_pipes():
    source = MCP_TEST_PATH.read_text(encoding="utf-8")
    assert "process.stdin.close()" in source
    assert "process.stdout.close()" in source
    assert "process.stderr.close()" in source


def test_database_models_have_expected_fields():
    assert hasattr(User, "plan_tier")
    assert hasattr(APIKey, "key_prefix")
    assert hasattr(Quota, "requests_today")
    assert hasattr(UsageRecord, "endpoint")


def test_rate_limiter_symbols_exist():
    assert isinstance(PLAN_LIMITS, dict)
    assert callable(update_quota_in_db)
    assert callable(check_quota_limits)
    assert hasattr(RateLimiter, "check_rate_limit")
