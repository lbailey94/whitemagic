import importlib
import os
import queue
import sys
import tempfile

import pytest

try:
    from whitemagic.core.resonance.event_types import EventType

    # Monkey patch EventType to avoid missing attribute errors in obsolete tests
    setattr(EventType, "VOTE_SESSION_CLOSED", "VOTE_SESSION_CLOSED")
    setattr(EventType, "VOTE_CONSENSUS_REACHED", "VOTE_CONSENSUS_REACHED")
    setattr(EventType, "TASK_FAILED", "TASK_FAILED")
    setattr(EventType, "TASK_CREATED", "TASK_CREATED")
    setattr(EventType, "AGENT_DEREGISTERED", "AGENT_DEREGISTERED")
    setattr(EventType, "BROKER_DISCONNECTED", "BROKER_DISCONNECTED")
    setattr(EventType, "BROKER_MESSAGE_PUBLISHED", "BROKER_MESSAGE_PUBLISHED")
except ImportError:
    pass

# Check if Rust backend is available
try:
    import whitemagic_rust  # noqa: F401 — sentinel for RUST_AVAILABLE

    RUST_AVAILABLE = True
except ImportError:
    RUST_AVAILABLE = False

# ---------------------------------------------------------------------------
# CRITICAL: Force test isolation BEFORE any whitemagic module is imported.
# paths.py evaluates DB_PATH / WM_ROOT at module-level on first import.
# If WM_STATE_ROOT already points to the real 107K-memory DB, every test
# that triggers get_unified_memory() will load the full production DB +
# holographic index, causing multi-minute hangs.
#
# We unconditionally override WM_STATE_ROOT to a fresh temp dir so that
# paths.py (and every singleton that depends on it) resolves to an empty DB.
# ---------------------------------------------------------------------------
_TEST_STATE_ROOT = tempfile.mkdtemp(prefix="wm_pytest_state_")
os.environ["WM_STATE_ROOT"] = _TEST_STATE_ROOT
os.environ["WM_SILENT_INIT"] = "1"
# Skip heavy holographic index loading during tests
os.environ["WM_SKIP_HOLO_INDEX"] = "1"

# If paths.py was already imported (e.g. by a plugin), force-reload it so
# the module-level constants pick up the new WM_STATE_ROOT.
if "whitemagic.config.paths" in sys.modules:
    importlib.reload(sys.modules["whitemagic.config.paths"])

# Ensure all subdirectories (memory/, data/, cache/, etc.) exist on disk.
# Without this, SQLite cannot create the DB file in CI where ~/.whitemagic
# doesn't pre-exist.
from whitemagic.config.paths import ensure_paths  # noqa: E402

ensure_paths()


def _stop_background_daemons():
    """Stop any running background daemon threads before resetting singletons.

    Without this, daemon threads (EmbeddingDaemon, DecayDaemon, RapidCognition,
    GanYingBus global worker) accumulate across tests and eventually cause
    hangs when the thread pool or event loop is saturated.
    """
    _daemon_specs = [
        ("whitemagic.core.memory.embedding_daemon", "get_embedding_daemon"),
        ("whitemagic.core.memory.neural.decay_daemon", "get_daemon"),
        ("whitemagic.core.intelligence.learning.rapid_cognition", "get_rapid_learner"),
    ]
    for mod_name, func_name in _daemon_specs:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        try:
            getter = getattr(mod, func_name, None)
            if getter is None:
                continue
            daemon = getter()
            if hasattr(daemon, "stop"):
                daemon.stop()
            elif hasattr(daemon, "running"):
                daemon.running = False
        except Exception:  # noqa: BLE001
            pass

    # Stop the GanYingBus global async worker thread
    try:
        import whitemagic.core.resonance._consolidated as _cons

        _cons._GLOBAL_WORKER_THREAD = None
        # Drain the queue to prevent stale events from being processed
        while not _cons._GLOBAL_ASYNC_QUEUE.empty():
            try:
                _cons._GLOBAL_ASYNC_QUEUE.get_nowait()
            except queue.Empty:
                break
    except Exception:  # noqa: BLE001
        pass

    # Reset the MCP server _INITIALISED flag so it re-initializes cleanly
    try:
        import whitemagic.run_mcp_lean as _mcp

        if hasattr(_mcp, "_INITIALISED"):
            _mcp._INITIALISED = False
    except Exception:  # noqa: BLE001
        pass

    # Clean up Redis broker to prevent __del__ warnings at process exit
    try:
        from whitemagic.tools.handlers.broker import cleanup_broker

        cleanup_broker()
    except Exception:  # noqa: BLE001
        pass

    # Clean up Redis cache connection pools
    try:
        from whitemagic.cache.redis import clear_redis_cache

        clear_redis_cache()
    except Exception:  # noqa: BLE001
        pass


def _reset_singletons():
    """Reset all known singletons so each test session starts clean.

    Now uses the centralized singleton registry from whitemagic.utils.singleton
    for automated tracking. Manual list is kept as fallback for legacy singletons.
    """
    # Stop background daemon threads BEFORE nulling references
    _stop_background_daemons()

    # Try the new centralized registry first
    try:
        from whitemagic.utils.singleton import reset_all_singletons

        reset_all_singletons()
    except ImportError:
        pass

    # Fallback: manually reset known singletons (for legacy code)
    _singleton_modules = [
        # --- Memory subsystem ---
        ("whitemagic.core.memory.unified", "_unified_memory"),
        ("whitemagic.core.memory.galactic_map", "_map_instance"),
        ("whitemagic.core.memory.consolidation", "_consolidator"),
        ("whitemagic.core.memory.lifecycle", "_manager"),
        ("whitemagic.core.memory.mindful_forgetting", "_forgetting"),
        ("whitemagic.core.memory.holographic", "_holographic_memory"),
        ("whitemagic.core.memory.constellations", "_detector_instance"),
        ("whitemagic.core.memory.association_miner", "_miner_instance"),
        ("whitemagic.core.memory.session_crystallizer", "_crystallizer"),
        # v14.0 Living Graph
        ("whitemagic.core.memory.graph_walker", "_walker"),
        ("whitemagic.core.memory.graph_engine", "_engine"),
        ("whitemagic.core.memory.surprise_gate", "_gate"),
        ("whitemagic.core.memory.bridge_synthesizer", "_synthesizer"),
        # --- Background daemons (stop called above, now null the refs) ---
        ("whitemagic.core.memory.neural.decay_daemon", "_daemon"),
        ("whitemagic.core.intelligence.learning.rapid_cognition", "_instance"),
        # --- Resonance / scheduling ---
        ("whitemagic.core.resonance.salience_arbiter", "_arbiter"),
        ("whitemagic.core.resonance.temporal_scheduler", "_scheduler"),
        ("whitemagic.core.resonance._consolidated", "_bus"),
        ("whitemagic.core.resonance.gan_ying_enhanced", "_bus"),
        # --- Harmony / governance ---
        ("whitemagic.harmony.vector", "_harmony_vector"),
        ("whitemagic.harmony.homeostatic_loop", "_loop"),
        ("whitemagic.harmony.anomaly_detector", "_detector"),
        ("whitemagic.dharma.karma_ledger", "_ledger"),
        # --- Tools / dispatch ---
        ("whitemagic.tools.dependency_graph", "_graph"),
        ("whitemagic.tools.circuit_breaker", "_registry"),
        ("whitemagic.tools.rate_limiter", "_instance"),
        ("whitemagic.tools.tool_permissions", "_registry_instance"),
        ("whitemagic.tools.sandbox", "_sandbox"),
        ("whitemagic.tools.speculative_prefetch", "_prefetcher"),
        ("whitemagic.tools.handlers.broker", "_BROKER_INSTANCE"),
        # --- Cache ---
        ("whitemagic.cache.redis", "_redis_cache"),
        # --- Intelligence ---
        ("whitemagic.core.intelligence.knowledge_graph", "_kg"),
        ("whitemagic.core.intelligence.bicameral", "_reasoner"),
        ("whitemagic.core.intelligence.emotion_drive", "_drive"),
        ("whitemagic.core.intelligence.self_model", "_model"),
        # --- Dreaming ---
        ("whitemagic.core.dreaming.dream_cycle", "_dream_cycle"),
        # --- Pattern Consciousness ---
        (
            "whitemagic.core.patterns.pattern_consciousness.resonance_cascade",
            "_orchestrator",
        ),
        # --- Mesh ---
        ("whitemagic.mesh.awareness", "_awareness"),
    ]
    for mod_name, attr_name in _singleton_modules:
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, attr_name):
            setattr(mod, attr_name, None)


@pytest.fixture(autouse=True)
def _reset_all_singletons():
    """Auto-reset singletons before each test to prevent cross-test leakage."""
    _reset_singletons()
    yield
    _reset_singletons()


@pytest.fixture
def fresh_state_root(tmp_path):
    """Provide a fresh WM_STATE_ROOT for tests that need total isolation.

    Also reloads whitemagic.config.paths so cached DB_PATH picks up the
    new state root.
    """
    old = os.environ.get("WM_STATE_ROOT")
    state_dir = tmp_path / "wm_state"
    state_dir.mkdir()
    os.environ["WM_STATE_ROOT"] = str(state_dir)
    # Reload paths module so DB_PATH and other cached paths update
    import importlib

    import whitemagic.config.paths as _paths

    importlib.reload(_paths)
    yield state_dir
    if old is not None:
        os.environ["WM_STATE_ROOT"] = old
    else:
        os.environ.pop("WM_STATE_ROOT", None)
    importlib.reload(_paths)


@pytest.fixture
def tool_caller():
    """Convenience wrapper for call_tool with assertion helpers."""
    from whitemagic.tools.unified_api import call_tool

    class ToolCaller:
        def __call__(self, tool_name: str, **kwargs):
            return call_tool(tool_name, **kwargs)

        def ok(self, tool_name: str, **kwargs):
            result = call_tool(tool_name, **kwargs)
            assert result["status"] == "success", (
                f"{tool_name} failed: {result.get('message')}"
            )
            return result

        def err(self, tool_name: str, **kwargs):
            result = call_tool(tool_name, **kwargs)
            assert result["status"] == "error", f"{tool_name} unexpectedly succeeded"
            return result

    return ToolCaller()


@pytest.fixture(autouse=True, scope="module")
def mcp_test_env(tmp_path_factory):
    """Set up an isolated WM_STATE_ROOT + WM_SILENT_INIT for MCP tests.

    Equivalent to the prior per-file `_mcp_env` fixture in
    tests/integration/test_mcp_e2e.py, test_opencode_hermes_bridge.py,
    and test_all_ganas_mcp.py. Hoisted here so the three duplicates
    can be deleted and the test files only declare fixtures they
    actually need. autouse=True with scope=module so it applies
    automatically to all tests in modules that need it.

    The fixture restores the prior env state on teardown and
    removes the temp directory (ignore_errors because Windows
    holds file handles briefly after process teardown).
    """
    import shutil

    state_dir = tmp_path_factory.mktemp("wm_mcp_state")
    prev = {
        "WM_SILENT_INIT": os.environ.get("WM_SILENT_INIT"),
        "WM_STATE_ROOT": os.environ.get("WM_STATE_ROOT"),
    }
    os.environ["WM_SILENT_INIT"] = "1"
    os.environ["WM_STATE_ROOT"] = str(state_dir)
    yield state_dir
    for k, v in prev.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    shutil.rmtree(state_dir, ignore_errors=True)


# Envelope helpers live in tests/_envelope.py. No re-export here:
# conftest.py is auto-loaded by pytest but not importable as
# `from tests.conftest import ...`. Any code that needs the
# envelope helpers should import them from _envelope directly.


# ---------------------------------------------------------------------------
# Granular progress bar (--progress flag)
# Uses ProgressBar with background timer thread for real-time elapsed updates.
# Shows: [████████░░░░░░░░] 50.00% | 750/1500 | 8.2s | ETA 8.2s | ✓749 ✗1 | test_name
# ---------------------------------------------------------------------------


def pytest_addoption(parser):
    group = parser.getgroup("progress")
    group.addoption(
        "--progress",
        action="store_true",
        default=False,
        dest="progress",
        help="Show granular progress bar during test runs.",
    )


_progress_bar = None


def pytest_collection_finish(session):
    global _progress_bar
    if session.config.getoption("progress", False):
        from whitemagic.utils.progress_bar import ProgressBar

        _progress_bar = ProgressBar(
            total=len(session.items),
            label="Tests",
            counters={"pass": 0, "fail": 0, "skip": 0, "err": 0},
        )
        _progress_bar.start()


def pytest_runtest_logreport(report):
    global _progress_bar
    if _progress_bar is None:
        return
    if report.when == "call":
        name = report.nodeid.replace("::()::", "::")
        if "[" in name:
            name = name.split("[")[0] + "]"
        if len(name) > 45:
            name = "..." + name[-42:]
        if report.outcome == "passed":
            _progress_bar.advance(**{"pass": 1})
        elif report.outcome == "failed":
            _progress_bar.advance(fail=1)
        elif report.outcome == "skipped":
            _progress_bar.advance(skip=1)
        _progress_bar.set_label(name)
    elif report.when == "setup" and report.outcome == "error":
        _progress_bar.advance(err=1)
        _progress_bar.set_label(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    global _progress_bar
    if _progress_bar is not None:
        _progress_bar.finish()
        _progress_bar = None
