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

# Pre-configure logging so the baseline state includes WhiteMagic handlers.
# Without this, the first test that imports a module calling get_logger()
# triggers setup_logging(), which adds handlers to the root logger and
# pytest-hygiene reports the delta as a leak.
from whitemagic.logging_config import setup_logging  # noqa: E402

setup_logging(level="WARNING")


def _stop_background_daemons():
    """Stop any running background daemon threads before resetting singletons.

    Uses the centralized WorkerRegistry to stop all registered workers,
    then falls back to the manual list for legacy unregistered daemons.
    """
    # Phase 1: Stop all workers registered with the WorkerRegistry
    try:
        from whitemagic.core.worker_registry import stop_all_workers

        stop_all_workers(timeout=5.0)
    except Exception:  # noqa: BLE001
        pass

    # Phase 2: Legacy daemons not yet registered with WorkerRegistry
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

    Delegates to the centralized SingletonRegistry which handles both
    factory-based singletons and legacy module-attribute singletons.
    """
    # Stop background daemon threads BEFORE nulling references
    _stop_background_daemons()

    # Reset all singletons via the centralized registry
    from whitemagic.utils.singleton_registry import reset_all_singletons

    reset_all_singletons()


@pytest.fixture(autouse=True, scope="module")
def _reset_all_singletons():
    """Auto-reset singletons once per module to prevent cross-module leakage.

    Module scope avoids reinitializing expensive singletons (SQLite schema,
    Karma ledger, Harmony Vector, Cascade Protocols) between every test.
    Tests needing fresh state within a module can use the fresh_state_root
    fixture or call _reset_singletons() explicitly.

    Resets on both setup and teardown so that pytest-randomly interleaving
    tests across modules doesn't leak state in either direction.
    """
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


# ---------------------------------------------------------------------------
# Hygiene cleanup — restores global state mutated by import-time side effects.
#
# pytest-hygiene --hygiene-strict detects leaks of logging handlers, sys.path
# entries, warnings.filters, and non-daemon threads.  These leaks occur because
# importing whitemagic modules triggers setup_logging(), sys.path.append() for
# polyglot bridges, and warnings.filterwarnings() calls.  The fixture below
# snapshots these global states before each test and restores them after.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _hygiene_global_state_cleanup():
    """Save/restore global state to satisfy pytest-hygiene --hygiene-strict.

    Handles four categories of import-time side effects:
    1. Logging: root logger level + handlers
    2. sys.path: module search path entries
    3. warnings.filters: warning filter list
    4. Threads: tool-dispatch executor threads
    """
    import logging
    import warnings

    root_logger = logging.getLogger()
    _saved_level = root_logger.level
    _saved_handlers = list(root_logger.handlers)
    _saved_path = list(sys.path)
    _saved_filters = list(warnings.filters)

    yield

    # Restore logging state
    root_logger.setLevel(_saved_level)
    root_logger.handlers = _saved_handlers

    # Restore sys.path
    sys.path[:] = _saved_path

    # Restore warnings filters
    warnings.filters[:] = _saved_filters

    # Shutdown the tool-dispatch ThreadPoolExecutor to kill leaked threads,
    # then recreate it so subsequent tests can use it.
    try:
        from concurrent.futures import ThreadPoolExecutor

        from whitemagic.tools import unified_api

        unified_api._TOOL_DISPATCH_EXECUTOR.shutdown(
            wait=False, cancel_futures=True
        )
        unified_api._TOOL_DISPATCH_EXECUTOR = ThreadPoolExecutor(
            max_workers=8, thread_name_prefix="tool-dispatch"
        )
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Repo-state guard — detects tests that modify the working tree.
#
# Artifact-producing suites (security scans, codegen, benchmarks) can
# accidentally write to the repo instead of tmp_path. This fixture
# snapshots the git status before and after each module and warns
# if new untracked or modified files appear.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True, scope="module")
def _repo_state_guard():
    """Snapshot git status before/after each module to detect unintended
    working-tree modifications by artifact-producing tests."""
    import subprocess

    def _git_status():
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True, text=True, timeout=5,
                cwd=os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            )
            return set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()
        except Exception:
            return set()

    before = _git_status()
    yield
    after = _git_status()
    new_changes = after - before
    # Filter out __pycache__ and .pyc changes (pytest artifact)
    real_changes = {
        c for c in new_changes
        if "__pycache__" not in c and ".pyc" not in c and ".pytest_cache" not in c
    }
    if real_changes:
        import warnings
        warnings.warn(
            f"Test module modified the working tree ({len(real_changes)} files): "
            + ", ".join(sorted(real_changes)[:5]),
            stacklevel=2,
        )


# ---------------------------------------------------------------------------
# Suppress "ValueError: I/O operation on closed file" from daemon threads
# (homeostatic_loop, embedding_daemon, etc.) that may still be mid-iteration
# when the interpreter closes logging handlers during pytest teardown.
# ---------------------------------------------------------------------------
import logging as _teardown_logging  # noqa: E402

_teardown_logging.raiseExceptions = False
