"""Phase 8 — Operational Tooling Tests.

Tests for all 6 work items:
1. Deterministic Replay
2. Fault Injection Harness
3. Migration & Integrity CLI
4. Runtime Health Surface
5. Property-based & Fuzz Testing
6. Plugin Boundary
"""
# ruff: noqa: BLE001
from __future__ import annotations

import json
import os
import random
import sqlite3
import tempfile
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# -- WI 1: Deterministic Replay --

class TestReplayRecorder:
    """Tests for ReplayRecorder and ReplayPlayer."""

    def test_record_and_replay_basic(self):
        from whitemagic.ops.replay import ExecutionTrace, ReplayPlayer, ReplayRecorder

        recorder = ReplayRecorder()
        with recorder.record("gnosis", query="test", user_id="alice"):
            recorder.set_result({"status": "success", "tool": "gnosis", "details": {"answer": 42}})

        trace = recorder.last_trace
        assert trace is not None
        assert trace.tool_name == "gnosis"
        assert trace.arguments == {"query": "test", "user_id": "alice"}
        assert trace.result_envelope["status"] == "success"

        player = ReplayPlayer()
        result = player.replay(trace)
        assert result["replayed"] is True
        assert result["replay_trace_id"] == trace.trace_id

    def test_record_context_manager_exception(self):
        from whitemagic.ops.replay import ReplayRecorder

        recorder = ReplayRecorder()
        with pytest.raises(ValueError, match="test error"):
            with recorder.record("search", query="fail"):
                raise ValueError("test error")

        trace = recorder.last_trace
        assert trace is not None
        assert trace.result_envelope["status"] == "error"
        assert "test error" in trace.result_envelope["message"]

    def test_trace_serialization(self):
        from whitemagic.ops.replay import ExecutionTrace, MiddlewareDecision

        trace = ExecutionTrace(
            trace_id="abc123",
            tool_name="test_tool",
            arguments={"x": 1},
            user_id="local",
            agent_id="default",
            galaxy="universal",
            policy_profile="default",
            requested_mode="full",
            middleware_decisions=[MiddlewareDecision(name="sanitizer", action="pass", duration_ms=0.5)],
            result_envelope={"status": "success"},
        )

        d = trace.to_dict()
        assert d["tool_name"] == "test_tool"
        assert len(d["middleware_decisions"]) == 1

        j = trace.to_json()
        parsed = json.loads(j)
        assert parsed["tool_name"] == "test_tool"

        restored = ExecutionTrace.from_dict(d)
        assert restored.tool_name == "test_tool"
        assert len(restored.middleware_decisions) == 1

    def test_replay_batch(self):
        from whitemagic.ops.replay import ExecutionTrace, ReplayPlayer

        traces = [
            ExecutionTrace(
                trace_id=f"t{i}",
                tool_name=f"tool_{i}",
                arguments={},
                user_id="local",
                agent_id="default",
                galaxy="default",
                policy_profile="default",
                requested_mode="full",
                result_envelope={"status": "success", "tool": f"tool_{i}"},
            )
            for i in range(3)
        ]

        player = ReplayPlayer()
        results = player.replay_batch(traces)
        assert len(results) == 3
        for r in results:
            assert r["replayed"] is True

    def test_persist_to_file(self):
        from whitemagic.ops.replay import ReplayRecorder

        with tempfile.TemporaryDirectory() as tmpdir:
            recorder = ReplayRecorder(replay_dir=tmpdir)
            with recorder.record("test_tool", x=1):
                recorder.set_result({"status": "success"})

            trace = recorder.last_trace
            trace_file = Path(tmpdir) / f"trace_{trace.trace_id}.json"
            assert trace_file.exists()
            data = json.loads(trace_file.read_text())
            assert data["tool_name"] == "test_tool"

    def test_middleware_decision_tracking(self):
        from whitemagic.ops.replay import MiddlewareDecision, ReplayRecorder

        recorder = ReplayRecorder()
        with recorder.record("test"):
            recorder.add_middleware_decision(
                MiddlewareDecision(name="sanitizer", action="pass", duration_ms=1.2)
            )
            recorder.add_middleware_decision(
                MiddlewareDecision(name="breaker", action="pass", duration_ms=0.3)
            )
            recorder.set_backend("python", native_fallback=False)
            recorder.set_result({"status": "success"})

        trace = recorder.last_trace
        assert len(trace.middleware_decisions) == 2
        assert trace.backend_choice == "python"
        assert trace.native_fallback is False

    def test_singleton_recorder(self):
        from whitemagic.ops.replay import get_recorder

        r1 = get_recorder()
        r2 = get_recorder()
        assert r1 is r2

    def test_is_replay_recording_env(self):
        from whitemagic.ops.replay import is_replay_recording

        with patch.dict(os.environ, {"WM_REPLAY_RECORD": "1"}):
            assert is_replay_recording() is True
        with patch.dict(os.environ, {"WM_REPLAY_RECORD": "0"}):
            assert is_replay_recording() is False


# -- WI 2: Fault Injection --

class TestFaultInjection:
    """Tests for FaultInjector."""

    def test_database_lock_fault(self):
        from whitemagic.ops.fault_injection import FaultInjector, FaultType

        injector = FaultInjector()
        try:
            injector.inject(FaultType.DATABASE_LOCK)
            assert injector.is_fault_active(FaultType.DATABASE_LOCK)
            with pytest.raises(sqlite3.OperationalError):
                sqlite3.connect(":memory:")
        finally:
            injector.clear()
        assert not injector.is_fault_active(FaultType.DATABASE_LOCK)

    def test_missing_dependency_fault(self):
        from whitemagic.ops.fault_injection import FaultInjector, FaultType

        injector = FaultInjector()
        try:
            injector.inject(FaultType.MISSING_DEPENDENCY, target_module="nonexistent_module_xyz")
            assert injector.is_fault_active(FaultType.MISSING_DEPENDENCY)
        finally:
            injector.clear()

    def test_native_bridge_crash_fault(self):
        from whitemagic.ops.fault_injection import FaultInjector, FaultType

        injector = FaultInjector()
        try:
            injector.inject(FaultType.NATIVE_BRIDGE_CRASH)
            from whitemagic.core.acceleration.process_supervisor import ProcessSupervisor

            sup = ProcessSupervisor(name="test", cmd=["echo"])
            result = sup.call({"method": "ping"})
            assert result.ok is False
            assert result.fallback is True
        finally:
            injector.clear()

    def test_network_failure_fault(self):
        import socket

        from whitemagic.ops.fault_injection import FaultInjector, FaultType

        injector = FaultInjector()
        try:
            injector.inject(FaultType.NETWORK_FAILURE)
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            with pytest.raises(socket.timeout):
                s.connect(("127.0.0.1", 9999))
            s.close()
        finally:
            injector.clear()

    def test_clear_fault(self):
        from whitemagic.ops.fault_injection import FaultInjector, FaultType

        injector = FaultInjector()
        injector.inject(FaultType.DATABASE_LOCK)
        assert len(injector.active_faults) == 1
        injector.clear_fault(FaultType.DATABASE_LOCK)
        assert len(injector.active_faults) == 0

    def test_fault_records(self):
        from whitemagic.ops.fault_injection import FaultInjector, FaultType

        injector = FaultInjector()
        injector.inject(FaultType.DATABASE_LOCK, duration_s=1.0)
        injector.clear()
        assert len(injector.records) == 1
        assert injector.records[0].fault_type == FaultType.DATABASE_LOCK

    def test_fault_injected_context_manager(self):
        from whitemagic.ops.fault_injection import FaultType, fault_injected

        with fault_injected(FaultType.DATABASE_LOCK) as injector:
            assert injector.is_fault_active(FaultType.DATABASE_LOCK)
        assert not injector.is_fault_active(FaultType.DATABASE_LOCK)

    def test_all_fault_types_exist(self):
        from whitemagic.ops.fault_injection import FaultType

        expected = {
            "database_lock", "corrupt_schema", "missing_dependency",
            "native_bridge_crash", "malformed_tool_response",
            "cache_corruption", "network_failure",
        }
        actual = {ft.value for ft in FaultType}
        assert expected == actual


# -- WI 3: Migration CLI --

class TestMigrationCLI:
    """Tests for MigrationCLI."""

    def test_inspect_empty_galaxy(self, tmp_path):
        from whitemagic.ops.migration_cli import MigrationCLI

        cli = MigrationCLI(state_root=str(tmp_path))
        results = cli.inspect(galaxy="nonexistent", user_id="test")
        assert len(results) == 1
        assert results[0].name == "nonexistent"
        assert not results[0].integrity_ok

    def test_inspect_real_db(self, tmp_path):
        from whitemagic.ops.migration_cli import MigrationCLI

        # Create a test galaxy DB
        galaxy_dir = tmp_path / "users" / "test" / "galaxies" / "universal"
        galaxy_dir.mkdir(parents=True)
        db_path = galaxy_dir / "whitemagic.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE memories (id TEXT, content TEXT, tags TEXT, importance REAL)")
        conn.execute("INSERT INTO memories VALUES ('1', 'test', 'tag1', 0.5)")
        conn.execute("CREATE TABLE schema_meta (key TEXT, value TEXT)")
        conn.execute("INSERT INTO schema_meta VALUES ('version', '24.3.1')")
        conn.commit()
        conn.close()

        cli = MigrationCLI(state_root=str(tmp_path))
        results = cli.inspect(galaxy="universal", user_id="test")
        assert len(results) == 1
        assert results[0].name == "universal"
        assert results[0].memory_count == 1
        assert results[0].integrity_ok
        assert results[0].schema_version == "24.3.1"

    def test_validate_all_galaxies(self, tmp_path):
        from whitemagic.ops.migration_cli import MigrationCLI

        cli = MigrationCLI(state_root=str(tmp_path))
        result = cli.validate(user_id="test")
        assert result.user_id == "test"
        assert result.galaxies_checked >= 0

    def test_repair_dry_run(self, tmp_path):
        from whitemagic.ops.migration_cli import MigrationCLI

        galaxy_dir = tmp_path / "users" / "test" / "galaxies" / "universal"
        galaxy_dir.mkdir(parents=True)
        db_path = galaxy_dir / "whitemagic.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE memories (id TEXT)")
        conn.commit()
        conn.close()

        cli = MigrationCLI(state_root=str(tmp_path))
        result = cli.repair("universal", user_id="test", dry_run=True)
        assert result.operation == "repair"
        assert result.dry_run is True
        assert result.success

    def test_reindex_dry_run(self, tmp_path):
        from whitemagic.ops.migration_cli import MigrationCLI

        galaxy_dir = tmp_path / "users" / "test" / "galaxies" / "universal"
        galaxy_dir.mkdir(parents=True)
        db_path = galaxy_dir / "whitemagic.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE memories (id TEXT)")
        conn.commit()
        conn.close()

        cli = MigrationCLI(state_root=str(tmp_path))
        result = cli.reindex("universal", user_id="test", dry_run=True)
        assert result.operation == "reindex"
        assert result.dry_run is True

    def test_export_import(self, tmp_path):
        from whitemagic.ops.migration_cli import MigrationCLI

        galaxy_dir = tmp_path / "users" / "test" / "galaxies" / "universal"
        galaxy_dir.mkdir(parents=True)
        db_path = galaxy_dir / "whitemagic.db"

        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE memories (id TEXT, content TEXT, tags TEXT, importance REAL)")
        conn.execute("INSERT INTO memories VALUES ('1', 'hello', 'tag1', 0.8)")
        conn.commit()
        conn.close()

        cli = MigrationCLI(state_root=str(tmp_path))
        export_path = tmp_path / "export.json"
        result = cli.export("universal", str(export_path), user_id="test")
        assert result.success
        assert result.items_affected == 1
        assert export_path.exists()

        data = json.loads(export_path.read_text())
        assert data["galaxy"] == "universal"
        assert len(data["memories"]) == 1

    def test_rollback(self, tmp_path):
        from whitemagic.ops.migration_cli import MigrationCLI

        galaxy_dir = tmp_path / "users" / "test" / "galaxies" / "universal"
        galaxy_dir.mkdir(parents=True)
        db_path = galaxy_dir / "whitemagic.db"

        # Create original DB
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE memories (id TEXT, content TEXT)")
        conn.execute("INSERT INTO memories VALUES ('1', 'original')")
        conn.commit()
        conn.close()

        # Create snapshot
        snapshot_path = tmp_path / "snapshot.db"
        import shutil
        shutil.copy2(str(db_path), str(snapshot_path))

        # Modify the DB
        conn = sqlite3.connect(str(db_path))
        conn.execute("INSERT INTO memories VALUES ('2', 'modified')")
        conn.commit()
        conn.close()

        # Rollback
        cli = MigrationCLI(state_root=str(tmp_path))
        result = cli.rollback(str(snapshot_path), galaxy="universal", user_id="test")
        assert result.success

        # Verify rollback
        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT * FROM memories").fetchall()
        conn.close()
        assert len(rows) == 1
        assert rows[0][1] == "original"


# -- WI 4: Runtime Health Surface --

class TestHealthSurface:
    """Tests for HealthSurface."""

    def test_collect_returns_report(self):
        from whitemagic.ops.health_surface import HealthSurface

        surface = HealthSurface()
        report = surface.collect()

        assert "status" in report
        assert report["status"] in ("healthy", "degraded", "critical")
        assert "components" in report
        assert "summary" in report
        assert report["summary"]["total_components"] == 6

    def test_components_present(self):
        from whitemagic.ops.health_surface import HealthSurface

        surface = HealthSurface()
        report = surface.collect()

        expected = {
            "middleware_latency", "memory_backends", "cache_isolation",
            "native_bridges", "degraded_capabilities", "pending_migrations",
        }
        assert expected == set(report["components"].keys())

    def test_last_report_cached(self):
        from whitemagic.ops.health_surface import HealthSurface

        surface = HealthSurface()
        report1 = surface.collect()
        assert surface.last_report == report1

    def test_singleton(self):
        from whitemagic.ops.health_surface import get_health_surface

        s1 = get_health_surface()
        s2 = get_health_surface()
        assert s1 is s2

    def test_middleware_latency_component(self):
        from whitemagic.ops.health_surface import HealthSurface

        surface = HealthSurface()
        report = surface.collect()
        comp = report["components"]["middleware_latency"]
        assert comp["status"] in ("healthy", "degraded", "down", "unknown")

    def test_native_bridges_component(self):
        from whitemagic.ops.health_surface import HealthSurface

        surface = HealthSurface()
        report = surface.collect()
        comp = report["components"]["native_bridges"]
        assert "bridges" in comp["details"]
        assert comp["details"]["total"] == 6


# -- WI 5: Property-based & Fuzz Testing --

class TestPropertyBasedFuzz:
    """Property-based and fuzz tests for operational tooling.

    Uses simple random generation (no external hypothesis dependency required).
    """

    def _random_string(self, length: int = 10) -> str:
        import random
        import string
        return "".join(random.choices(string.ascii_letters + string.digits, k=length))

    def test_trace_roundtrip_property(self):
        """Trace serialization → deserialization preserves data."""
        import random

        from whitemagic.ops.replay import ExecutionTrace, MiddlewareDecision

        for _ in range(50):
            n_mw = random.randint(0, 5)
            trace = ExecutionTrace(
                trace_id=self._random_string(8),
                tool_name=self._random_string(random.randint(1, 20)),
                arguments={"k": self._random_string(5)},
                user_id="local",
                agent_id="default",
                galaxy="default",
                policy_profile="default",
                requested_mode="full",
                middleware_decisions=[
                    MiddlewareDecision(
                        name=self._random_string(5),
                        action=random.choice(["pass", "short_circuit", "error"]),
                        duration_ms=random.uniform(0, 10),
                    )
                    for _ in range(n_mw)
                ],
                result_envelope={"status": random.choice(["success", "error"])},
            )

            d = trace.to_dict()
            restored = ExecutionTrace.from_dict(d)
            assert restored.tool_name == trace.tool_name
            assert restored.user_id == trace.user_id
            assert len(restored.middleware_decisions) == n_mw
            assert restored.result_envelope["status"] == trace.result_envelope["status"]

    def test_fault_inject_clear_idempotent(self):
        """Clearing faults multiple times is safe."""
        from whitemagic.ops.fault_injection import FaultInjector, FaultType

        injector = FaultInjector()
        injector.inject(FaultType.DATABASE_LOCK)
        injector.clear()
        injector.clear()  # Should not raise
        assert len(injector.active_faults) == 0

    def test_migration_cli_nonexistent_path_safe(self):
        """MigrationCLI handles nonexistent paths gracefully."""
        from whitemagic.ops.migration_cli import MigrationCLI

        cli = MigrationCLI(state_root="/nonexistent/path/xyz")
        results = cli.inspect(user_id="test")
        assert isinstance(results, list)

    def test_health_surface_collect_idempotent(self):
        """Health surface can be collected multiple times safely."""
        from whitemagic.ops.health_surface import HealthSurface

        surface = HealthSurface()
        for _ in range(10):
            report = surface.collect()
            assert report["summary"]["total_components"] == 6

    def test_extension_point_register_unregister(self):
        """Extension points handle register/unregister correctly."""
        from whitemagic.core.plugin import (
            EP_TOOLS,
            clear_extension_points,
            get_extension_point,
        )

        clear_extension_points()
        ep = get_extension_point(EP_TOOLS)
        cb = MagicMock()
        ep.register("test_plugin", cb)
        assert len(ep.get_registrations()) == 1

        ep.unregister("test_plugin")
        assert len(ep.get_registrations()) == 0

        clear_extension_points()

    def test_plugin_registry_lifecycle(self):
        """Plugin registry tracks state transitions."""
        from whitemagic.core.plugin import PluginInfo, PluginState, get_registry, reset_registry

        reset_registry()
        registry = get_registry()
        info = PluginInfo(name="test", version="1.0.0", state=PluginState.DISCOVERED)
        registry.register(info)

        assert registry.get("test") is not None
        assert registry.set_state("test", PluginState.ACTIVE)
        assert registry.get("test").state == PluginState.ACTIVE
        assert len(registry.active()) == 1
        assert registry.unregister("test")
        assert registry.get("test") is None

        reset_registry()

    def test_fuzz_tool_name_replay(self):
        """Replay handles arbitrary tool names without crashing."""
        from whitemagic.ops.replay import ExecutionTrace, ReplayPlayer

        player = ReplayPlayer()
        for _ in range(20):
            trace = ExecutionTrace(
                trace_id=self._random_string(8),
                tool_name=self._random_string(random.randint(0, 50)),
                arguments={},
                user_id="local",
                agent_id="default",
                galaxy="default",
                policy_profile="default",
                requested_mode="full",
                result_envelope={"status": "success"},
            )
            result = player.replay(trace)
            assert result["replayed"] is True

    def test_fuzz_migration_galaxy_names(self):
        """Migration CLI handles arbitrary galaxy names."""
        import random

        from whitemagic.ops.migration_cli import MigrationCLI

        with tempfile.TemporaryDirectory() as tmpdir:
            cli = MigrationCLI(state_root=tmpdir)
            for _ in range(10):
                name = self._random_string(random.randint(1, 30))
                result = cli.inspect(galaxy=name, user_id="test")
                assert isinstance(result, list)
                assert len(result) == 1


# -- WI 6: Plugin Boundary --

class TestPluginBoundary:
    """Tests for the plugin boundary system."""

    def test_plugin_base_class(self):
        from whitemagic.core.plugin import Plugin, PluginManifest

        class MyPlugin(Plugin):
            def __init__(self):
                self.manifest = PluginManifest(
                    name="test", version="1.0.0", author="tester",
                )
                self.activated = False

            def activate(self):
                self.activated = True

        p = MyPlugin()
        p.activate()
        assert p.activated
        assert p.manifest.name == "test"
        p.deactivate()  # Should not raise

    def test_plugin_manifest_defaults(self):
        from whitemagic.core.plugin import PluginManifest

        m = PluginManifest(name="test", version="1.0.0")
        assert m.author == "Unknown"
        assert m.license == "MIT"
        assert m.requires == []
        assert m.extension_points == []

    def test_extension_point_registration(self):
        from whitemagic.core.plugin import (
            EP_HANDLERS,
            EP_TOOLS,
            clear_extension_points,
            get_extension_point,
            list_extension_points,
        )

        clear_extension_points()
        tools_ep = get_extension_point(EP_TOOLS)
        handlers_ep = get_extension_point(EP_HANDLERS)

        cb1 = MagicMock()
        cb2 = MagicMock()
        tools_ep.register("plugin_a", cb1, priority=1)
        tools_ep.register("plugin_b", cb2, priority=2)

        assert len(tools_ep.get_registrations()) == 2
        assert len(tools_ep.get_callbacks()) == 2

        # Unregister one plugin
        tools_ep.unregister("plugin_a")
        assert len(tools_ep.get_registrations()) == 1

        # List all extension points
        all_eps = list_extension_points()
        assert EP_TOOLS in all_eps
        assert EP_HANDLERS in all_eps

        clear_extension_points()

    def test_plugin_registry_operations(self):
        from whitemagic.core.plugin import (
            PluginInfo,
            PluginState,
            get_registry,
            reset_registry,
        )

        reset_registry()
        registry = get_registry()

        info = PluginInfo(
            name="test_plugin",
            version="2.0.0",
            state=PluginState.DISCOVERED,
            extension_points=["tools"],
        )
        registry.register(info)

        assert registry.get("test_plugin") is not None
        assert registry.get("nonexistent") is None
        assert len(registry.all()) == 1
        assert len(registry.active()) == 0

        registry.set_state("test_plugin", PluginState.ACTIVE)
        assert len(registry.active()) == 1
        assert len(registry.by_state(PluginState.ACTIVE)) == 1

        reset_registry()

    def test_plugin_loader_load_nonexistent(self):
        from whitemagic.core.plugin import PluginLoader, reset_registry

        reset_registry()
        loader = PluginLoader()
        result = loader.load("nonexistent.module.xyz")
        assert result is None
        reset_registry()

    def test_plugin_loader_load_real(self):
        from whitemagic.core.plugin import (
            Plugin,
            PluginLoader,
            PluginManifest,
            get_registry,
            reset_registry,
        )

        reset_registry()

        # Create a temporary plugin module
        import sys
        import types

        mod = types.ModuleType("test_plugin_mod")

        class TestPlugin(Plugin):
            def __init__(self):
                self.manifest = PluginManifest(name="test_mod", version="1.0.0")
            def activate(self):
                pass

        def create_plugin():
            return TestPlugin()

        mod.create_plugin = create_plugin
        sys.modules["test_plugin_mod"] = mod

        loader = PluginLoader()
        plugin = loader.load("test_plugin_mod")
        assert plugin is not None
        assert plugin.manifest.name == "test_mod"

        # Check registry
        info = get_registry().get("test_mod")
        assert info is not None

        # Activate
        assert loader.activate(plugin)
        assert get_registry().get("test_mod").state.value == "active"

        # Deactivate
        assert loader.deactivate(plugin)
        assert get_registry().get("test_mod").state.value == "inactive"

        del sys.modules["test_plugin_mod"]
        reset_registry()

    def test_plugin_discovery_scans_directory(self, tmp_path):
        from whitemagic.core.plugin import PluginDiscovery, clear_extension_points

        # Create a fake plugin file
        plugin_file = tmp_path / "my_plugin.py"
        plugin_file.write_text("""
from whitemagic.core.plugin import Plugin, PluginManifest

class MyPlugin(Plugin):
    def __init__(self):
        self.manifest = PluginManifest(name="my", version="1.0.0")
    def activate(self):
        pass

def create_plugin():
    return MyPlugin()
""")

        discovery = PluginDiscovery()
        results = discovery.scan([str(tmp_path)])
        assert len(results) == 1
        assert "my_plugin" in results[0]

    def test_plugin_discovery_skips_non_plugins(self, tmp_path):
        from whitemagic.core.plugin import PluginDiscovery

        # Create a non-plugin file
        (tmp_path / "not_a_plugin.py").write_text("x = 42\n")
        (tmp_path / "_private.py").write_text("create_plugin = None\n")

        discovery = PluginDiscovery()
        results = discovery.scan([str(tmp_path)])
        assert len(results) == 0

    def test_known_extension_points_initialized(self):
        from whitemagic.core.plugin import (
            EP_GOVERNANCE_POLICIES,
            EP_HANDLERS,
            EP_NATIVE_ACCELERATORS,
            EP_RETRIEVAL_STAGES,
            EP_TOOLS,
            clear_extension_points,
            get_extension_point,
        )

        clear_extension_points()
        # Re-import to trigger initialization
        import importlib
        import whitemagic.core.plugin.extension_point as ep_mod
        importlib.reload(ep_mod)

        # Known EPs should be created with default versions
        for name in [EP_TOOLS, EP_HANDLERS, EP_RETRIEVAL_STAGES, EP_GOVERNANCE_POLICIES, EP_NATIVE_ACCELERATORS]:
            ep = ep_mod.get_extension_point(name)
            assert ep.name == name
            assert ep.version == "1.0.0"

        clear_extension_points()

    def test_plugin_package_imports_cleanly(self):
        """The plugin package __init__ should import without errors."""
        import whitemagic.core.plugin as pkg

        assert hasattr(pkg, "Plugin")
        assert hasattr(pkg, "PluginManifest")
        assert hasattr(pkg, "ExtensionPoint")
        assert hasattr(pkg, "PluginRegistry")
        assert hasattr(pkg, "PluginInfo")
        assert hasattr(pkg, "PluginState")
        assert hasattr(pkg, "PluginLoader")
        assert hasattr(pkg, "PluginDiscovery")
        assert hasattr(pkg, "get_registry")
        assert hasattr(pkg, "EP_TOOLS")
        assert hasattr(pkg, "EP_HANDLERS")
        assert hasattr(pkg, "EP_RETRIEVAL_STAGES")
        assert hasattr(pkg, "EP_GOVERNANCE_POLICIES")
        assert hasattr(pkg, "EP_NATIVE_ACCELERATORS")
