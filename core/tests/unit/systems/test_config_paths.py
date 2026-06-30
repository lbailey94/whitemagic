"""Tests for whitemagic.config.paths — WM_STATE_ROOT fallback chain, path resolution."""

import os
import importlib

import pytest

pytestmark = pytest.mark.core  # State-root behavior is release-critical


def test_project_root_contains_pyproject(tmp_path):
    """PROJECT_ROOT should point to the directory containing pyproject.toml."""
    from whitemagic.config.paths import PROJECT_ROOT

    assert (PROJECT_ROOT / "pyproject.toml").exists()


def test_wm_root_is_directory():
    """WM_ROOT should resolve to an existing directory."""
    from whitemagic.config.paths import WM_ROOT

    assert WM_ROOT.is_dir() or WM_ROOT.parent.is_dir()


def test_wm_state_root_env_override(tmp_path):
    """WM_STATE_ROOT env var should override the default root."""
    custom = tmp_path / "custom_state"
    custom.mkdir()

    old = os.environ.get("WM_STATE_ROOT")
    os.environ["WM_STATE_ROOT"] = str(custom)
    try:
        import whitemagic.config.paths as paths_mod

        importlib.reload(paths_mod)
        assert paths_mod.WM_ROOT == custom
    finally:
        if old is not None:
            os.environ["WM_STATE_ROOT"] = old
        else:
            os.environ.pop("WM_STATE_ROOT", None)
        importlib.reload(paths_mod)


def test_db_path_derivation():
    """DB_PATH should be under MEMORY_DIR by default."""
    from whitemagic.config.paths import DB_PATH, MEMORY_DIR

    # When WM_DB_PATH is unset, DB should be under the memory directory
    if not os.environ.get("WM_DB_PATH"):
        assert str(DB_PATH).startswith(str(MEMORY_DIR))


def test_ensure_paths_creates_dirs(tmp_path):
    """ensure_paths() should create all required subdirectories."""
    old = os.environ.get("WM_STATE_ROOT")
    state = tmp_path / "fresh_state"
    os.environ["WM_STATE_ROOT"] = str(state)
    try:
        import whitemagic.config.paths as paths_mod

        importlib.reload(paths_mod)
        paths_mod.ensure_paths()
        for subdir in [
            "data",
            "memory",
            "cache",
            "sessions",
            "logs",
            "artifacts",
            "restoration",
        ]:
            assert (paths_mod.WM_ROOT / subdir).is_dir(), f"{subdir} not created"
    finally:
        if old is not None:
            os.environ["WM_STATE_ROOT"] = old
        else:
            os.environ.pop("WM_STATE_ROOT", None)
        importlib.reload(paths_mod)


def test_scripts_dir_is_pathlib():
    """SCRIPTS_DIR should be a Path object under PROJECT_ROOT."""
    from whitemagic.config.paths import SCRIPTS_DIR, PROJECT_ROOT

    assert SCRIPTS_DIR == PROJECT_ROOT / "scripts"


def test_no_repo_local_fallback(tmp_path, monkeypatch):
    """WM_ROOT must never resolve to inside the repo tree via implicit DB detection.

    Previously paths.py would detect memory/whitemagic.db inside PROJECT_ROOT and
    silently use the repo as the state root. That behaviour has been removed.
    Even if that file exists, the resolved root must not be PROJECT_ROOT.
    """
    import importlib
    import whitemagic.config.paths as paths_mod

    project_root = paths_mod.PROJECT_ROOT
    fake_db_dir = project_root / "memory"
    fake_db_dir.mkdir(exist_ok=True)
    fake_db = fake_db_dir / "whitemagic.db"
    created = False
    if not fake_db.exists():
        fake_db.touch()
        created = True

    monkeypatch.delenv("WM_STATE_ROOT", raising=False)
    monkeypatch.delenv("WM_CONFIG_ROOT", raising=False)
    try:
        importlib.reload(paths_mod)
        assert paths_mod.WM_ROOT != project_root, (
            "WM_ROOT must not resolve to PROJECT_ROOT via repo-local DB detection"
        )
    finally:
        if created:
            fake_db.unlink(missing_ok=True)
        importlib.reload(paths_mod)


@pytest.mark.skipif(
    not str(__import__("pathlib").Path(__file__).resolve()).startswith(
        str(__import__("pathlib").Path.home())
    ),
    reason="Default path resolution only valid when repo is under the user home directory",
)
def test_default_root_is_home_dotwhitemagic(monkeypatch):
    """When no env vars are set, WM_ROOT should default to ~/.whitemagic, not repo-relative."""
    import importlib
    from pathlib import Path
    import whitemagic.config.paths as paths_mod

    monkeypatch.delenv("WM_STATE_ROOT", raising=False)
    monkeypatch.delenv("WM_CONFIG_ROOT", raising=False)
    importlib.reload(paths_mod)

    expected = Path.home() / ".whitemagic"
    # The writable-probe may redirect to /tmp if ~/.whitemagic is unwritable,
    # but it must never land inside PROJECT_ROOT.
    assert not str(paths_mod.WM_ROOT).startswith(str(paths_mod.PROJECT_ROOT)), (
        f"WM_ROOT ({paths_mod.WM_ROOT}) must not be inside PROJECT_ROOT ({paths_mod.PROJECT_ROOT})"
    )
    # And the intended_root (pre-writability-check) should be ~/.whitemagic.
    assert paths_mod._intended_root == expected, (
        f"_intended_root should be {expected}, got {paths_mod._intended_root}"
    )
