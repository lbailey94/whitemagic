"""Tests for galaxy sync module (v23.2 Phase 3).

Tests are designed to work without a real Redis instance — they verify
the sync module's graceful degradation and channel naming logic.
"""

from unittest.mock import patch


class TestGalaxySyncChannelNaming:
    """Tests for Redis channel naming convention."""

    def test_user_channel(self):
        """Channel for a user without specific galaxy."""
        from whitemagic.core.memory.galaxy_sync import _galaxy_channel

        assert _galaxy_channel("alice") == "galaxy:alice"

    def test_user_galaxy_channel(self):
        """Channel for a specific user+galaxy."""
        from whitemagic.core.memory.galaxy_sync import _galaxy_channel

        assert _galaxy_channel("alice", "project-x") == "galaxy:alice:project-x"

    def test_local_user_channel(self):
        """Channel for the default local user."""
        from whitemagic.core.memory.galaxy_sync import _galaxy_channel

        assert _galaxy_channel("local") == "galaxy:local"
        assert _galaxy_channel("local", "default") == "galaxy:local:default"


class TestGalaxySyncDisabled:
    """Tests for graceful degradation when Redis is unavailable."""

    def test_is_sync_enabled_false_in_test_env(self, monkeypatch):
        """Sync is disabled when WM_SILENT_INIT=1 (test env)."""
        monkeypatch.setenv("WM_SILENT_INIT", "1")
        from whitemagic.core.memory.galaxy_sync import _is_sync_enabled

        assert _is_sync_enabled() is False

    def test_publish_returns_false_when_disabled(self, monkeypatch):
        """publish_galaxy_event returns False when sync is disabled."""
        monkeypatch.setenv("WM_SILENT_INIT", "1")
        from whitemagic.core.memory.galaxy_sync import publish_galaxy_event

        assert publish_galaxy_event("galaxy.created", "alice", "test") is False

    def test_start_listener_returns_none_when_disabled(self, monkeypatch):
        """start_galaxy_sync_listener returns None when sync is disabled."""
        monkeypatch.setenv("WM_SILENT_INIT", "1")
        from whitemagic.core.memory.galaxy_sync import start_galaxy_sync_listener

        assert start_galaxy_sync_listener("alice") is None

    def test_stop_listener_returns_false_when_disabled(self, monkeypatch):
        """stop_galaxy_sync_listener returns False when sync is disabled."""
        monkeypatch.setenv("WM_SILENT_INIT", "1")
        from whitemagic.core.memory.galaxy_sync import stop_galaxy_sync_listener

        assert stop_galaxy_sync_listener("alice") is False


class TestGalaxySyncPublish:
    """Tests for publish_galaxy_event with mocked Redis."""

    def test_publish_calls_broker_when_enabled(self, monkeypatch):
        """publish_galaxy_event attempts to publish when Redis is available."""
        # Don't set WM_SILENT_INIT — simulate Redis available via URL
        monkeypatch.delenv("WM_SILENT_INIT", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")

        from whitemagic.core.memory.galaxy_sync import publish_galaxy_event

        # Mock the _run to return immediately without actually running the coroutine
        async def _fake_run(coro):
            coro.close()
            return "msg_123"

        with patch("whitemagic.tools.handlers.broker._run", side_effect=_fake_run):
            with patch("whitemagic.tools.handlers.broker._get_broker") as mock_get:
                mock_get.return_value = None
                result = publish_galaxy_event("galaxy.created", "alice", "test-galaxy")
                assert result is True

    def test_publish_handles_errors_gracefully(self, monkeypatch):
        """publish_galaxy_event returns False on exception."""
        monkeypatch.delenv("WM_SILENT_INIT", raising=False)
        monkeypatch.setenv("REDIS_URL", "redis://localhost:6379")

        from whitemagic.core.memory.galaxy_sync import publish_galaxy_event

        with patch(
            "whitemagic.tools.handlers.broker._run",
            side_effect=Exception("Connection refused"),
        ):
            result = publish_galaxy_event("galaxy.created", "alice", "test")
            assert result is False


class TestBrokerRedisUrl:
    """Tests for REDIS_URL env var support in broker."""

    def test_resolve_redis_url_checks_env_vars(self, monkeypatch):
        """_resolve_redis_url checks env vars in priority order."""
        from whitemagic.tools.handlers.broker import _resolve_redis_url

        # No env vars set
        monkeypatch.delenv("WHITEMAGIC_REDIS_URL", raising=False)
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.delenv("REDISCLOUD_URL", raising=False)
        assert _resolve_redis_url() is None

        # WHITEMAGIC_REDIS_URL takes priority
        monkeypatch.setenv("WHITEMAGIC_REDIS_URL", "redis://wm:6379")
        monkeypatch.setenv("REDIS_URL", "redis://fallback:6379")
        assert _resolve_redis_url() == "redis://wm:6379"

        # REDIS_URL is second priority
        monkeypatch.delenv("WHITEMAGIC_REDIS_URL", raising=False)
        assert _resolve_redis_url() == "redis://fallback:6379"

        # REDISCLOUD_URL is third
        monkeypatch.delenv("REDIS_URL", raising=False)
        monkeypatch.setenv("REDISCLOUD_URL", "redis://cloud:6379")
        assert _resolve_redis_url() == "redis://cloud:6379"

    def test_broker_init_with_url(self):
        """_AsyncBroker stores URL parameter."""
        from whitemagic.tools.handlers.broker import _AsyncBroker

        broker = _AsyncBroker(url="redis://example:6380")
        assert broker._url == "redis://example:6380"
