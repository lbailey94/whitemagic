# ruff: noqa: BLE001
"""Tests for Phase 3 — gRPC client, WebSocket bridge, session management."""

from __future__ import annotations

import json
import os
import tempfile
import time

import pytest

_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"


class TestSessionManager:
    """Test session lifecycle and continuity."""

    def test_create_session(self):
        from whitemagic.core.consciousness.session_manager import get_session_manager
        sm = get_session_manager()
        result = sm.create_session(agent_id="test", agent_type="test")
        assert "session_id" in result
        assert result["session_id"].startswith("sess_")
        assert "continuity_context" in result

    def test_resume_session(self):
        from whitemagic.core.consciousness.session_manager import get_session_manager
        sm = get_session_manager()
        created = sm.create_session(agent_id="test", agent_type="test")
        sid = created["session_id"]
        sm.end_session(sid, summary="test summary")
        resumed = sm.resume_session(sid)
        assert resumed is not None
        assert resumed["session_id"] == sid
        assert "continuity_context" in resumed

    def test_end_session(self):
        from whitemagic.core.consciousness.session_manager import get_session_manager
        sm = get_session_manager()
        created = sm.create_session(agent_id="test", agent_type="test")
        sid = created["session_id"]
        assert sm.end_session(sid, summary="done") is True

    def test_end_nonexistent_session(self):
        from whitemagic.core.consciousness.session_manager import get_session_manager
        sm = get_session_manager()
        assert sm.end_session("nonexistent") is False

    def test_touch_session(self):
        from whitemagic.core.consciousness.session_manager import get_session_manager
        sm = get_session_manager()
        created = sm.create_session(agent_id="test", agent_type="test")
        sid = created["session_id"]
        sm.touch(sid)
        session = sm.get_session(sid)
        assert session is not None
        assert session.cycle_count == 1

    def test_list_sessions(self):
        from whitemagic.core.consciousness.session_manager import get_session_manager
        sm = get_session_manager()
        sm.create_session(agent_id="test1", agent_type="test")
        sm.create_session(agent_id="test2", agent_type="test")
        sessions = sm.list_sessions(limit=10)
        assert len(sessions) >= 2

    def test_get_current_session(self):
        from whitemagic.core.consciousness.session_manager import get_session_manager
        sm = get_session_manager()
        sm.create_session(agent_id="test", agent_type="test")
        current = sm.get_current_session()
        assert current is not None
        assert current.agent_id == "test"

    def test_continuity_context_first_session(self):
        from whitemagic.core.consciousness.session_manager import SessionManager
        sm = SessionManager()
        ctx = sm._build_continuity_context("test")
        # May or may not be first depending on test order
        assert "first_session" in ctx

    def test_session_persistence(self):
        from whitemagic.core.consciousness.session_manager import SessionManager
        sm1 = SessionManager()
        result = sm1.create_session(agent_id="persist_test", agent_type="test")
        sid = result["session_id"]
        sm1.end_session(sid, summary="persisted")

        sm2 = SessionManager()
        loaded = sm2.get_session(sid)
        assert loaded is not None
        assert loaded.summary == "persisted"


class TestCognitiveClient:
    """Test the gRPC cognitive client (without actual connection)."""

    def test_client_init(self):
        from whitemagic.mesh.cognitive_client import CognitiveClient
        client = CognitiveClient()
        assert client._socket_path == "/tmp/whitemagic/wm.sock"
        assert client._tcp_addr == "localhost:4730"

    def test_client_not_connected(self):
        from whitemagic.mesh.cognitive_client import CognitiveClient
        client = CognitiveClient()
        assert client.is_connected is False

    def test_client_connect_no_server(self):
        from whitemagic.mesh.cognitive_client import CognitiveClient
        client = CognitiveClient(socket_path="/tmp/nonexistent.sock")
        result = client.connect()
        # Should fail gracefully (TCP fallback also fails)
        assert result is False

    def test_client_close(self):
        from whitemagic.mesh.cognitive_client import CognitiveClient
        client = CognitiveClient()
        client.close()
        assert client.is_connected is False

    def test_daemon_status_not_connected(self):
        from whitemagic.mesh.cognitive_client import CognitiveClient
        client = CognitiveClient()
        result = client.daemon_status()
        assert result["status"] == "error"


class TestWebSocketBridge:
    """Test the WebSocket bridge (without actual server)."""

    def test_bridge_init(self):
        from whitemagic.mesh.ws_bridge import WebSocketBridge
        bridge = WebSocketBridge(port=9999)
        assert bridge._port == 9999
        assert bridge.is_running is False

    def test_bridge_client_count(self):
        from whitemagic.mesh.ws_bridge import WebSocketBridge
        bridge = WebSocketBridge()
        assert bridge.client_count == 0
