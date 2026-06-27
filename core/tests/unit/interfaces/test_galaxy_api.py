"""Tests for galaxy_api route — multi-user isolation (v23.2)."""

from whitemagic.interfaces.api.routes.galaxy_api import _resolve_user_id


def test_resolve_user_id_defaults_to_local():
    """When no header is provided, user ID defaults to 'local'."""
    assert _resolve_user_id(None) == "local"
    assert _resolve_user_id("") == "local"


def test_resolve_user_id_uses_provided_id():
    """When a valid user ID is provided, it is used (sanitized)."""
    assert _resolve_user_id("alice") == "alice"
    assert _resolve_user_id("bob-123") == "bob-123"
    assert _resolve_user_id("user_test") == "user_test"


def test_resolve_user_id_sanitizes_unsafe_chars():
    """Unsafe characters in user IDs are replaced with underscores."""
    assert _resolve_user_id("alice/../../../etc") == "alice__________etc"
    assert _resolve_user_id("user@domain") == "user_domain"


def test_resolve_user_id_truncates_long_ids():
    """User IDs longer than 64 chars are truncated."""
    long_id = "a" * 100
    result = _resolve_user_id(long_id)
    assert len(result) == 64
