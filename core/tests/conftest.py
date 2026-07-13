import importlib
import os
import queue
import sys
import tempfile
from unittest.mock import MagicMock, patch

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
# Each xdist worker gets its own state root to prevent SQLite contention.
_xdist_worker = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
_TEST_STATE_ROOT = tempfile.mkdtemp(prefix=f"wm_pytest_state_{_xdist_worker}_")
os.environ["WM_STATE_ROOT"] = _TEST_STATE_ROOT
os.environ["WM_SILENT_INIT"] = "1"
# Skip heavy holographic index loading during tests
os.environ["WM_SKIP_HOLO_INDEX"] = "1"
# PostgreSQL integration tests (skipped gracefully if unavailable)
os.environ.setdefault("WM_PG_PASSWORD", "whitemagic")
# Polyglot subprocess checks are gated per-test via skipif decorators.

# Suppress noisy INFO logs from SQLite schema migrations during tests
import logging as _logging  # noqa: E402

_logging.getLogger("whitemagic.core.memory.sqlite_backend").setLevel(_logging.WARNING)
_logging.getLogger("whitemagic.core.memory.embeddings").setLevel(_logging.WARNING)

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

    # Drain the GanYingBus global async queue to prevent stale events.
    # IMPORTANT: Do NOT null _GLOBAL_WORKER_THREAD — the thread is a daemon
    # and will keep running. Nullning it causes _ensure_global_worker() to
    # create a NEW thread on the next test, leading to thread accumulation
    # and eventual hang from thread saturation.
    try:
        import whitemagic.core.resonance._consolidated as _cons

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
        # --- Consciousness subsystem ---
        ("whitemagic.core.consciousness.citta_cycle", "_cycle"),
        ("whitemagic.core.consciousness.citta_cycle", "_always_on"),
        ("whitemagic.core.consciousness.citta_cycle", "_replay_delivered"),
        ("whitemagic.core.consciousness.coherence", "_coherence"),
        ("whitemagic.core.consciousness.coherence", "_smarana"),
        ("whitemagic.core.consciousness.guna_balance", "_guna_balance"),
        ("whitemagic.core.consciousness.consciousness_loop", "_loop"),
        ("whitemagic.core.consciousness.possibility_explorer", "_explorer"),
        ("whitemagic.core.consciousness.meta_galaxy", "_meta_galaxy"),
        ("whitemagic.core.consciousness.knowledge_gap_loop", "_kg_loop"),
        ("whitemagic.core.consciousness.prediction_calibration", "_calibration"),
        ("whitemagic.core.consciousness.apotheosis_engine", "_apotheosis_engine"),
        # --- Evolution ---
        ("whitemagic.core.evolution.recursive_loop", "_loop"),
        # --- Intelligence / inference ---
        ("whitemagic.core.inference.router", "_router"),
        # --- Memory / scanning ---
        ("whitemagic.core.memory.codebase_scanner", "_scanner"),
        # --- Pattern Consciousness ---
        (
            "whitemagic.core.patterns.pattern_consciousness.resonance_cascade",
            "_orchestrator",
        ),
        # --- Mesh ---
        ("whitemagic.mesh.awareness", "_awareness"),
        # --- Intelligence / Session / Monitoring ---
        ("whitemagic.core.intelligence.researcher", "_researcher"),
        ("whitemagic.core.intelligence.omni.skill_forge", "_forge"),
        ("whitemagic.core.memory.session_recorder", "_recorder"),
        ("whitemagic.core.monitoring.tool_usage_tracker", "_tracker"),
        # --- Cache ---
        ("whitemagic.core.cache.unified_cache_bridge", "_unified_cache"),
        # --- PRAT resonance state ---
        ("whitemagic.tools.prat_resonance", "_state"),
    ]
    for mod_name, attr_name in _singleton_modules:
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, attr_name):
            setattr(mod, attr_name, None)

    # Reset class-level _instance singletons (__new__-based pattern)
    # These aren't caught by the module-level _var = None pattern above
    for mod_name, cls_name in (
        ("whitemagic.core.consciousness.dharma", "DharmaProtocol"),
        ("whitemagic.core.nervous_system", "NervousSystem"),
    ):
        mod = sys.modules.get(mod_name)
        if mod and hasattr(mod, cls_name):
            cls = getattr(mod, cls_name)
            if hasattr(cls, "_instance"):
                cls._instance = None


@pytest.fixture(autouse=True, scope="module")
def _reset_all_singletons():
    """Auto-reset singletons once per module to prevent cross-module leakage.

    Module scope avoids reinitializing expensive singletons (SQLite schema,
    Karma ledger, Harmony Vector, Cascade Protocols) between every test.
    Tests needing fresh state within a module can use the fresh_state_root
    fixture or call _reset_singletons() explicitly.
    """
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


@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
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
# Global ML engine mock — prevents loading FastEmbed/MiniLM/sentence-transformers
# in unit tests. Per AGENTS.md test purity rules, unit tests must never load ML
# models. Tests that genuinely need the engine can override this mock by
# patching `get_embedding_engine` themselves with a more specific mock.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_heavy_engines(request):
    """Mock embedding engine to prevent ML model loading in unit tests.

    Returns fake 384-dim vectors so VSA/HRR/compression tests work
    without loading FastEmbed/MiniLM (~2-3s per load).
    """
    import whitemagic.core.memory.embeddings as _emb_mod

    _FAKE_DIM = 384

    def _fake_encode(text, **kwargs):
        if isinstance(text, str):
            return [0.0] * _FAKE_DIM
        return [[0.0] * _FAKE_DIM for _ in text]

    def _fake_encode_batch(texts, **kwargs):
        return [[0.0] * _FAKE_DIM for _ in texts]

    _mock_embedding = MagicMock()
    _mock_embedding.available.return_value = True
    _mock_embedding.encode.side_effect = _fake_encode
    _mock_embedding.encode_batch.side_effect = _fake_encode_batch
    _mock_embedding.search_similar.return_value = []
    _mock_embedding.search_similar_by_vector.return_value = []
    _mock_embedding.embedding_dim = _FAKE_DIM

    # Set the singleton directly — get_embedding_engine() checks _engine_instances dict
    _old_instances = getattr(_emb_mod, "_engine_instances", None)
    _emb_mod._engine_instances = {"local": _mock_embedding}

    # Also patch the function for modules that import it at module level
    p = patch(
        "whitemagic.core.memory.embeddings.get_embedding_engine",
        return_value=_mock_embedding,
    )
    p.start()
    yield
    p.stop()
    _emb_mod._engine_instances = _old_instances if _old_instances is not None else {}


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
