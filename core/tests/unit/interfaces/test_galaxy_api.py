"""Tests for galaxy_api route."""

import pytest

from whitemagic.interfaces.api.routes.galaxy_api import _require_api_key


def test_require_api_key_open_when_not_required(monkeypatch):
    monkeypatch.setenv("WM_GALAXY_REQUIRE_KEY", "false")
    assert _require_api_key(None) is None
    assert _require_api_key("any") is None


def test_require_api_key_blocks_missing(monkeypatch):
    monkeypatch.setenv("WM_GALAXY_REQUIRE_KEY", "true")
    with pytest.raises(Exception) as exc:
        _require_api_key(None)
    assert "401" in str(exc.value) or "required" in str(exc.value)


def test_require_api_key_accepts_valid_format(monkeypatch):
    monkeypatch.setenv("WM_GALAXY_REQUIRE_KEY", "true")
    key = "wm_test_key_1234567890abcdef"
    assert _require_api_key(key) == key


def test_require_api_key_rejects_invalid(monkeypatch):
    monkeypatch.setenv("WM_GALAXY_REQUIRE_KEY", "true")
    with pytest.raises(Exception) as exc:
        _require_api_key("bad")
    assert "403" in str(exc.value) or "Invalid" in str(exc.value)
