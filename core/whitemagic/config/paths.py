"""Centralized path configuration for Whitemagic.

This module provides two distinct path concepts:
1. PROJECT_ROOT - where the code/repository lives (for scripts, archive, etc.)
2. WM_ROOT - where user state/data lives (configurable via env vars, defaults to ~/.whitemagic)

Policy (AI-first / OSS-friendly):
- Whitemagic should not write runtime state into the repo by default.
- Callers can explicitly set `WM_STATE_ROOT` to place state wherever they want.
"""
import os
import tempfile
from pathlib import Path
from typing import Any


def _is_writable(path: Path) -> bool:
    try:
        # NOTE: os.access() can return true in sandboxed environments even when
        # writes are blocked. Do a real create/delete probe.
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            return False
        with tempfile.NamedTemporaryFile(prefix=".wm_write_probe_", dir=path, delete=True) as fp:
            fp.write(b"probe")
            fp.flush()
        return True
    except (OSError, FileNotFoundError, PermissionError):
        return False


def get_project_root() -> Path:
    """Returns the project root directory (where pyproject.toml lives).

    This is the CODE location, not the state/data location.
    Use this for finding scripts, archive, and other repo-relative paths.
    """
    return Path(__file__).resolve().parent.parent.parent


# Project root (code location) - for finding scripts, archive, etc.
PROJECT_ROOT: Path = get_project_root()
SCRIPTS_DIR: Path = PROJECT_ROOT / "scripts"
ARCHIVE_DIR: Path = PROJECT_ROOT / "archive"


# Canonical Root for STATE/DATA
# Resolution order (first wins):
# 1. WM_STATE_ROOT env var  (explicit, preferred)
# 2. WM_CONFIG_ROOT env var (legacy alias, still supported)
# 3. ~/.whitemagic          (fallback for compatibility)
#
# NOTE: Repo-local state detection has been intentionally removed.
# Runtime state (memory DB, sessions, logs) must never live inside the
# repository tree. If you previously relied on an in-repo memory/whitemagic.db,
# set WM_STATE_ROOT to that directory explicitly.
_intended_root_path = (
    os.getenv("WM_STATE_ROOT")
    or os.getenv("WM_CONFIG_ROOT")
)

if _intended_root_path:
    _intended_root = Path(_intended_root_path).expanduser()
else:
    # Default to traditional home directory location
    _intended_root = Path.home().expanduser() / ".whitemagic"

WM_ROOT: Path
if not _is_writable(_intended_root):
    _tmp_fallback = Path(tempfile.gettempdir()) / "whitemagic_state"
    if _is_writable(_tmp_fallback):
        WM_ROOT = _tmp_fallback
    else:
        # STRICT MODE: Never fall back to CWD to prevent repo pollution.
        # In restricted environments, users MUST explicitly set WM_STATE_ROOT
        # to a writable location outside the repository.
        _opt_in_cwd = os.getenv("WM_FALLBACK_TO_CWD", "false").lower() in ("true", "1", "yes")
        if _opt_in_cwd:
            # Opt-in only: CWD fallback with explicit user acknowledgment
            WM_ROOT = Path.cwd() / ".whitemagic"
        else:
            raise RuntimeError(
                f"WhiteMagic cannot initialize state root: {_intended_root}\n"
                f"Temporary fallback also failed: {_tmp_fallback}\n\n"
                f"To resolve this issue, set one of the following environment variables\n"
                f"to a writable directory outside the repository:\n\n"
                f"  export WM_STATE_ROOT=/path/to/writable/location\n"
                f"  export WM_CONFIG_ROOT=/path/to/writable/location  (legacy alias)\n\n"
                f"Alternatively, for CI or restricted environments only:\n"
                f"  export WM_FALLBACK_TO_CWD=true  (allows .whitemagic in current directory)\n"
            )
else:
    WM_ROOT = _intended_root

# Subdirectories
DATA_DIR: Path = WM_ROOT / "data"
MEMORY_DIR: Path = WM_ROOT / "memory"
CACHE_DIR: Path = WM_ROOT / "cache"
SESSIONS_DIR: Path = WM_ROOT / "sessions"
LOGS_DIR: Path = WM_ROOT / "logs"
ARTIFACTS_DIR: Path = WM_ROOT / "artifacts"
RESTORE_DIR: Path = WM_ROOT / "restoration"
DHARMA_DIR: Path = WM_ROOT / "dharma"
BENCHMARKS_DIR: Path = WM_ROOT / "benchmarks"
EXTENSIONS_DIR: Path = WM_ROOT / "extensions"
TASKS_DIR: Path = WM_ROOT / "tasks"
AUTODIDACTIC_DIR: Path = WM_ROOT / "autodidactic"
SECURITY_DIR: Path = WM_ROOT / "security"
LEARNING_DIR: Path = WM_ROOT / "learning"
KNOWLEDGE_DIR: Path = WM_ROOT / "knowledge"
PAYMENTS_DIR: Path = WM_ROOT / "payments"
KEYS_DIR: Path = WM_ROOT / "keys"
PIPELINE_DIR: Path = WM_ROOT / "pipeline_state"
PROGRESS_LOGS_DIR: Path = LOGS_DIR / "progress"
AGENTS_DIR: Path = WM_ROOT / "agents"
VOTES_DIR: Path = WM_ROOT / "votes"
PIPELINES_DIR: Path = WM_ROOT / "pipelines"
PLUGINS_DIR: Path = WM_ROOT / "plugins"
PROMPTS_DIR: Path = WM_ROOT / "prompts"
IDENTITY_DIR: Path = WM_ROOT / "identity"
INTAKE_DIR: Path = WM_ROOT / "inbox"
SANGHA_DIR: Path = WM_ROOT / "sangha"
GRATITUDE_DIR: Path = WM_ROOT / "gratitude"
WISDOM_DIR: Path = WM_ROOT / "wisdom"
ECONOMY_DIR: Path = WM_ROOT / "economy"

# Files
USER_PROFILE_PATH: Path = WM_ROOT / "user_profile.json"
CONFIG_PATH: Path = WM_ROOT / "config.json"
UPDATE_CHECK_PATH: Path = WM_ROOT / ".update_check"
SYNC_REGISTRY_PATH: Path = WM_ROOT / "sync_registry.json"
GARDEN_REGISTRY_PATH: Path = WM_ROOT / "garden_file_registry.json"

_db_env = (os.getenv("WM_DB_PATH") or "").strip()
DB_PATH: Path
if _db_env:
    _p = Path(_db_env).expanduser()
    if not _p.is_absolute():
        # Treat relative DB paths as relative to the state root.
        _p = (WM_ROOT / _p)
    DB_PATH = _p.resolve()
else:
    DB_PATH = MEMORY_DIR / "whitemagic.db"

# Cold storage DB (v13.3.2) — deep_archive + scavenged memories
COLD_DB_PATH: Path = MEMORY_DIR / "whitemagic_cold.db"

def get_state_root() -> Path:
    """Returns the effective state root (WM_ROOT)."""
    return WM_ROOT


def ensure_paths() -> Any:
    """Ensure all core directories exist."""
    import logging
    log = logging.getLogger(__name__)
    if not os.getenv("WM_SILENT_INIT"):
        log.info(f"Ensuring paths exist at {WM_ROOT}...")
    for path in [
        WM_ROOT,
        DATA_DIR,
        MEMORY_DIR,
        CACHE_DIR,
        SESSIONS_DIR,
        LOGS_DIR,
        ARTIFACTS_DIR,
        RESTORE_DIR,
        DHARMA_DIR,
        BENCHMARKS_DIR,
        EXTENSIONS_DIR,
        TASKS_DIR,
        AUTODIDACTIC_DIR,
        SECURITY_DIR,
        LEARNING_DIR,
        KNOWLEDGE_DIR,
        PAYMENTS_DIR,
        KEYS_DIR,
        PIPELINE_DIR,
        PROGRESS_LOGS_DIR,
        AGENTS_DIR,
        VOTES_DIR,
        PIPELINES_DIR,
        PLUGINS_DIR,
        PROMPTS_DIR,
        IDENTITY_DIR,
        INTAKE_DIR,
        SANGHA_DIR,
        GRATITUDE_DIR,
        ECONOMY_DIR,
        WISDOM_DIR,
    ]:
        path.mkdir(parents=True, exist_ok=True)
    # Restrict state root to owner-only (protects memory DB, ledger, secrets)
    try:
        WM_ROOT.chmod(0o700)
    except OSError:
        pass  # Best-effort; some filesystems don't support chmod
    # DB path may be overridden (e.g., containers); ensure its parent exists.
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    if not os.getenv("WM_SILENT_INIT"):
        log.info("Paths verified.")
