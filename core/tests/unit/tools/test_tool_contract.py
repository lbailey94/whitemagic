import json
from uuid import uuid4

import pytest


@pytest.fixture(autouse=True)
def _isolated_state_root(monkeypatch, tmp_path):
    """Isolate DB state to prevent order-dependent failures."""
    monkeypatch.setenv("WM_STATE_ROOT", str(tmp_path))
    monkeypatch.setenv("WM_SILENT_INIT", "1")
    # Patch DB paths to use isolated temp dir
    import whitemagic.config.paths as _paths
    monkeypatch.setattr(_paths, "WM_ROOT", tmp_path)
    monkeypatch.setattr(_paths, "MEMORY_DIR", tmp_path / "memory")
    monkeypatch.setattr(_paths, "DB_PATH", tmp_path / "memory" / "whitemagic.db")
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    # Reset unified memory singleton so it picks up new paths
    import whitemagic.core.memory.unified as _unified
    # Close existing instances to release SQLite connections
    for inst in list(_unified._unified_memory_instances.values()):
        try:
            inst.close()
        except Exception:
            pass
    _unified._unified_memory_instances.clear()
    # Reset self-model so error-rate predictions from previous tests
    # don't cause the guardian to block write tools
    try:
        import whitemagic.core.intelligence.self_model as _sm
        _sm._instance = None
    except ImportError:
        pass
    # Reset galactic module cached connections
    try:
        import whitemagic.core.galactic as _galactic
        monkeypatch.setattr(_galactic, "DEFAULT_DB_PATH", tmp_path / "memory" / "whitemagic.db")
        if hasattr(_galactic, "_db_conn"):
            _galactic._db_conn = None
        if hasattr(_galactic, "_db_path_cache"):
            _galactic._db_path_cache = None
    except ImportError:
        pass
    yield
    for inst in list(_unified._unified_memory_instances.values()):
        try:
            inst.close()
        except Exception:
            pass
    _unified._unified_memory_instances.clear()


def _assert_envelope_shape(out: dict) -> None:
    expected = {
        "status",
        "tool",
        "request_id",
        "idempotency_key",
        "message",
        "error_code",
        "details",
        "retryable",
        "writes",
        "artifacts",
        "metrics",
        "side_effects",
        "warnings",
        "timestamp",
        "envelope_version",
        "tool_contract_version",
    }
    missing = expected.difference(out.keys())
    assert not missing, f"missing envelope keys: {sorted(missing)}"
    assert isinstance(out["status"], str)
    assert isinstance(out["tool"], str)
    assert isinstance(out["request_id"], str)
    assert isinstance(out["details"], dict)

    # Must always be JSON-serializable.
    json.dumps(out)


def test_capabilities_returns_envelope():
    from whitemagic.tools.unified_api import call_tool

    out = call_tool("capabilities", include_tools=False, include_env=False)
    _assert_envelope_shape(out)
    assert out["status"] == "success"
    assert out["tool"] == "capabilities"


def test_invalid_params_returns_error_envelope():
    from whitemagic.tools.unified_api import call_tool

    out = call_tool("manifest", format="not-a-real-format")
    _assert_envelope_shape(out)
    assert out["status"] == "error"
    assert out["error_code"] == "invalid_params"


def test_idempotency_replay_create_memory():
    from whitemagic.tools.unified_api import call_tool

    key = f"pytest-{uuid4()}"
    first = call_tool(
        "create_memory",
        title="pytest idempotency",
        content="hello",
        type="short_term",
        tags=["pytest"],
        idempotency_key=key,
    )
    _assert_envelope_shape(first)
    assert first["status"] == "success"
    mem_id_1 = first["details"]["memory_id"]

    second = call_tool(
        "create_memory",
        title="pytest idempotency",
        content="hello",
        type="short_term",
        tags=["pytest"],
        idempotency_key=key,
    )
    _assert_envelope_shape(second)
    assert second["status"] == "success"
    assert second["details"]["memory_id"] == mem_id_1
    assert second.get("side_effects", {}).get("idempotency_replay") is True


def test_memory_alias_crud_contract():
    from whitemagic.tools.unified_api import call_tool

    created = call_tool(
        "create_memory",
        title="pytest memory alias crud",
        content="memory alias crud initial",
        type="short_term",
        tags=["pytest", "alias"],
    )
    _assert_envelope_shape(created)
    assert created["status"] == "success"
    memory_id = created["details"]["memory_id"]

    read = call_tool("read_memory", memory_id=memory_id)
    _assert_envelope_shape(read)
    assert read["status"] == "success"
    assert read["details"]["content"] == "memory alias crud initial"

    updated = call_tool(
        "memory_update",
        memory_id=memory_id,
        content="memory alias crud updated",
        add_tags=["updated"],
    )
    _assert_envelope_shape(updated)
    assert updated["status"] == "success"
    assert updated["details"]["content"] == "memory alias crud updated"
    assert "updated" in updated["details"]["tags"]

    deleted = call_tool("memory_delete", memory_id=memory_id)
    _assert_envelope_shape(deleted)
    assert deleted["status"] == "success"
    assert deleted["details"]["action"] == "archived"

    missing = call_tool("memory_read", memory_id=memory_id)
    _assert_envelope_shape(missing)
    assert missing["status"] == "error"
    assert missing["error_code"] != "tool_not_found"


def test_now_override_sets_timestamp_verbatim():
    from whitemagic.tools.unified_api import call_tool

    ts = "2026-01-01T00:00:00Z"
    out = call_tool("capabilities", include_tools=False, include_env=False, now=ts)
    _assert_envelope_shape(out)
    assert out["timestamp"] == ts
