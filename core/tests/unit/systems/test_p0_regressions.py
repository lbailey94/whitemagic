import importlib
import sys
from types import SimpleNamespace

import pytest
from click.testing import CliRunner

import whitemagic.cli.cli_app as cli_app

try:
    from starlette.routing import Match
    from whitemagic.interfaces.api.routes import tools_gateway
    _HAS_API = True
except ImportError:
    _HAS_API = False


def _first_route_endpoint(path: str, method: str = "GET"):
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "root_path": "",
        "scheme": "http",
        "headers": [],
        "query_string": b"",
    }
    for route in tools_gateway.router.routes:
        match, _ = route.matches(scope)
        if match == Match.FULL:
            return getattr(route, "endpoint", None)
    return None


@pytest.mark.skipif(not _HAS_API, reason="fastapi/starlette not installed (requires [api] extra)")
def test_tools_health_route_precedes_dynamic_tool_lookup():
    endpoint = _first_route_endpoint("/api/tools/health")
    assert endpoint is tools_gateway.tools_health


@pytest.mark.skip("P0 regression tests need update for current CLI")
def test_recall_cli_accepts_memories_shape(monkeypatch):
    def fake_call_tool(tool_name, **kwargs):
        assert tool_name == "search_memories"
        return {
            "status": "success",
            "details": {
                "memories": [
                    {"id": "m-1", "content": "hello from memory"},
                ]
            },
        }

    monkeypatch.setattr("whitemagic.tools.unified_api.call_tool", fake_call_tool)

    runner = CliRunner()
    result = runner.invoke(cli_app.main, ["recall", "hello"])

    assert result.exit_code == 0
    assert "Found 1 memories" in result.output
    assert "m-1" in result.output


def test_stats_command_does_not_raise_name_error(monkeypatch):
    class FakeMemory:
        def get_stats(self):
            return {
                "total_memories": 1,
                "by_type": {"short_term": 1},
                "total_tags": 1,
            }

        def get_tag_counts(self, limit=10):
            return [("audit", 1)]

    monkeypatch.setattr(cli_app, "HAS_CORE", True)
    monkeypatch.setattr(cli_app, "get_memory", lambda: FakeMemory())

    runner = CliRunner()
    result = runner.invoke(cli_app.main, ["stats"])

    assert result.exit_code == 0
    assert "Memory Statistics" in result.output


def test_no_hiding_reconstruct_uses_safe_parsing(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "whitemagic.core.gan_ying",
        SimpleNamespace(get_bus=lambda: object(), Event=object, EventType=object),
    )
    no_hiding = importlib.import_module("whitemagic.core.memory.no_hiding")

    fake_memories = [
        SimpleNamespace(content="{'focus': 'deep'}"),
        SimpleNamespace(content="{'danger': __import__('os').system('echo hacked')}"),
    ]

    class FakeUnified:
        def search(self, query):
            return fake_memories

    monkeypatch.setattr(no_hiding, "get_unified_memory", lambda: FakeUnified())
    monkeypatch.setattr(no_hiding, "get_bus", lambda: object())

    controller = no_hiding.NoHidingMemoryController()
    reconstructed = controller.reconstruct("entity-x")

    assert reconstructed is not None
    assert reconstructed["traits"] == {"focus": "deep"}


@pytest.mark.asyncio
async def test_conductor_live_monitoring_writes_heartbeat(tmp_path, monkeypatch):
    import asyncio
    import json
    import threading

    import whitemagic.orchestration.conductor as conductor_mod

    monkeypatch.setattr(conductor_mod, "WM_ROOT", tmp_path)
    monkeypatch.setattr(conductor_mod, "_LIVE_STATUS_REFRESH_SECONDS", 0.05)
    monkeypatch.setattr(conductor_mod, "emit_event", lambda *args, **kwargs: None)

    start_event = asyncio.Event()
    release_event = asyncio.Event()

    class FakeArmy:
        async def parallel_explore(self, iteration_prompt, clones_per_iteration):
            start_event.set()
            await release_event.wait()
            return SimpleNamespace(
                content="<complete>",
                confidence=0.99,
                strategy="live-monitoring",
                clone_id="clone-1",
            )

    monkeypatch.setattr(conductor_mod, "AsyncThoughtCloneArmy", lambda: FakeArmy())

    orchestrator = conductor_mod.ConductorOrchestrator(
        conductor_mod.ConductorConfig(max_iterations=1, clones_per_iteration=1),
    )

    task = asyncio.create_task(orchestrator.conduct("finish this task"))
    await asyncio.wait_for(start_event.wait(), timeout=5)

    live_path = conductor_mod.get_conductor_live_status_path()
    assert live_path.exists()

    first = json.loads(live_path.read_text(encoding="utf-8"))
    assert first["active"] is True
    assert first["phase"] in {"starting", "iteration-1-exploring"}
    assert first["progress"]["total_iterations"] == 0

    first_update = first["last_update"]
    await asyncio.sleep(0.15)

    second = json.loads(live_path.read_text(encoding="utf-8"))
    assert second["last_update"] != first_update
    assert second["active"] is True

    release_event.set()
    result = await asyncio.wait_for(task, timeout=2)
    final = json.loads(live_path.read_text(encoding="utf-8"))

    assert result.is_complete is True
    assert final["active"] is False
    assert final["phase"] == "completed"
    assert final["progress"]["total_iterations"] == 1
    assert final["progress"]["completed"] is True


def test_continuous_status_reads_live_monitoring_payload(tmp_path, monkeypatch):
    import json

    import whitemagic.orchestration.conductor as conductor_mod

    monkeypatch.setattr(conductor_mod, "WM_ROOT", tmp_path)

    live_payload = {
        "active": True,
        "phase": "iteration-1-exploring",
        "status": "running",
        "pid": 4321,
        "started_at": "2026-04-05T21:00:00",
        "last_update": "2026-04-05T21:00:05",
        "current_iteration": 1,
        "current_confidence": 0.91,
        "current_strategy": "live-monitoring",
        "current_preview": "Working through the current task",
        "session_path": str(tmp_path / "conductor" / "session_20260405_210000.json"),
        "progress": {
            "status": "in_progress",
            "total_iterations": 3,
            "tokens_used": 27,
            "completed": False,
        },
    }
    live_path = conductor_mod.get_conductor_live_status_path()
    live_path.parent.mkdir(parents=True, exist_ok=True)
    live_path.write_text(json.dumps(live_payload), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli_app.main, ["continuous-status"])

    assert result.exit_code == 0
    assert "Live Conductor Status" in result.output
    assert "Active: yes" in result.output
    assert "Phase: iteration-1-exploring" in result.output
    assert "Current iteration: 1" in result.output
    assert "Tokens used: 27" in result.output
    assert "Current confidence: 0.91" in result.output
    assert "Session export:" in result.output


def test_continuous_status_falls_back_to_latest_session(tmp_path, monkeypatch):
    import json

    import whitemagic.orchestration.conductor as conductor_mod

    monkeypatch.setattr(conductor_mod, "WM_ROOT", tmp_path)

    session_path = conductor_mod.get_conductor_state_dir() / "session_20260405_210000.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_payload = {
        "config": {"max_iterations": 2},
        "progress": {
            "status": "complete",
            "total_iterations": 2,
            "tokens_used": 12,
            "avg_confidence": 0.98,
            "max_confidence": 0.99,
            "completed": True,
        },
    }
    session_path.write_text(json.dumps(session_payload), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli_app.main, ["continuous-status"])

    assert result.exit_code == 0
    assert "Latest Conductor Session" in result.output
    assert "Status: complete" in result.output
    assert "Iterations completed: 2" in result.output
    assert "Tokens used: 12" in result.output
