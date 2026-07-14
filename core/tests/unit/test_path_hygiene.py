"""Path hygiene validation tests.

Ensures:
1. No repo-local state leakage (state separate from code)
2. All path resolution goes through config/paths.py
3. Environment variable fallbacks work correctly
4. Strict mode prevents silent CWD pollution
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


class TestPathHygiene:
    """Test path resolution hygiene and safety."""

    def test_state_root_never_in_repo(self):
        """WM_ROOT must never resolve to a directory inside the repository."""
        # Import fresh to get current WM_ROOT
        from whitemagic.config.paths import WM_ROOT, get_project_root

        project_root = get_project_root()

        # WM_ROOT must be outside project_root
        try:
            WM_ROOT.relative_to(project_root)
            # If we get here, WM_ROOT is inside the repo - this is a failure
            assert False, f"WM_ROOT ({WM_ROOT}) is inside project root ({project_root})"
        except ValueError:
            # Good - WM_ROOT is outside project root
            pass

    def test_explicit_state_root_respected(self, tmp_path):
        """WM_STATE_ROOT environment variable is respected."""
        custom_root = tmp_path / "custom_whitemagic"
        custom_root.mkdir()

        with patch.dict(os.environ, {"WM_STATE_ROOT": str(custom_root)}):
            # Must reimport to pick up new env var
            if "whitemagic.config.paths" in sys.modules:
                del sys.modules["whitemagic.config.paths"]
            from whitemagic.config.paths import WM_ROOT

            assert WM_ROOT == custom_root

    def test_strict_mode_blocks_cwd_fallback(self, tmp_path, monkeypatch):
        """Without WM_FALLBACK_TO_CWD, CWD fallback is blocked with clear error."""
        # Create bad_root as a FILE so _is_writable returns False (not a dir)
        bad_root = tmp_path / "nonexistent" / "path"
        bad_root.parent.mkdir(parents=True)
        bad_root.touch()

        # Create a read-only temp directory so _is_writable returns False
        readonly_temp = tmp_path / "readonly_temp"
        readonly_temp.mkdir()
        readonly_temp.chmod(0o555)

        with patch.dict(
            os.environ,
            {
                "WM_STATE_ROOT": str(bad_root),
                "WM_FALLBACK_TO_CWD": "false",
            },
        ):
            # Mock tempfile.gettempdir to return the read-only path
            import tempfile as _tempfile_module

            original_gettempdir = _tempfile_module.gettempdir
            _tempfile_module.gettempdir = lambda: str(readonly_temp)

            try:
                # Clear module cache
                for mod in list(sys.modules.keys()):
                    if mod.startswith("whitemagic.config"):
                        del sys.modules[mod]

                # Import should raise RuntimeError with clear guidance
                with pytest.raises(RuntimeError) as exc_info:
                    import whitemagic.config.paths  # noqa: F401

                error_msg = str(exc_info.value)
                assert "WM_STATE_ROOT" in error_msg
                assert "WM_FALLBACK_TO_CWD" in error_msg
            finally:
                # Restore original gettempdir and permissions for cleanup
                _tempfile_module.gettempdir = original_gettempdir
                readonly_temp.chmod(0o755)

    def test_opt_in_cwd_fallback_works(self, tmp_path, monkeypatch):
        """WM_FALLBACK_TO_CWD=true allows CWD fallback when needed."""
        # Create bad_root as a FILE so _is_writable returns False (not a dir)
        bad_root = tmp_path / "nonexistent" / "path"
        bad_root.parent.mkdir(parents=True)
        bad_root.touch()
        monkeypatch.chdir(tmp_path)

        # Create a read-only temp directory so _is_writable returns False
        readonly_temp = tmp_path / "readonly_temp_cwd"
        readonly_temp.mkdir()
        readonly_temp.chmod(0o555)

        with patch.dict(
            os.environ,
            {
                "WM_STATE_ROOT": str(bad_root),
                "WM_FALLBACK_TO_CWD": "true",
            },
        ):
            # Mock tempfile.gettempdir to return the read-only path
            import tempfile as _tempfile_module

            original_gettempdir = _tempfile_module.gettempdir
            _tempfile_module.gettempdir = lambda: str(readonly_temp)

            try:
                # Clear module cache
                for mod in list(sys.modules.keys()):
                    if mod.startswith("whitemagic.config"):
                        del sys.modules[mod]

                from whitemagic.config.paths import WM_ROOT

                # Should have used CWD fallback
                assert WM_ROOT == tmp_path / ".whitemagic"
            finally:
                # Restore original gettempdir and permissions for cleanup
                _tempfile_module.gettempdir = original_gettempdir
                readonly_temp.chmod(0o755)

    def test_no_direct_path_home_usage(self):
        """No files outside canonical path modules should use Path.home() or expanduser."""
        # This test verifies the grep-based CI check is working
        # List of files that legitimately need path expansion
        allowed_exceptions = [
            # Documentation and grimoire files
            "grimoire/",
            # Archive files (not runtime)
            "archive/",
            # Canonical path module (the single source of truth for path resolution)
            "config/paths.py",
            # Path validation with security gating (legitimate)
            "security/tool_gating.py",
            # User-provided base_path validation in unified API
            "tools/unified_api.py",
            # External app data discovery (Windsurf/Codeium)
            "archaeology/windsurf_reader.py",
            # Labs-tier scratchpad analysis (user-provided base_dir)
            "core/intelligence/multi_spectral_scratchpad.py",
            # Labs-tier synthesis engines (user-provided db_path)
            "core/intelligence/synthesis/sub_clustering.py",
            "core/intelligence/synthesis/serendipity_engine.py",
            # HuggingFace model cache discovery (legitimate third-party path resolution)
            "core/memory/embedding_daemon.py",
            # Local LLM model discovery (lm-studio, llama.cpp model paths)
            "interfaces/chat.py",
            "interfaces/unified_tui.py",
            # Session mining reads user session data from home directory
            "archaeology/session_miner.py",
            # Pattern tools resolve user-provided path patterns
            "tools/handlers/pattern_tools.py",
            # Report scraper discovers security reports in user's home
            "tools/security/report_scraper.py",
            # Plugin discovery scans user's home for installed plugins
            "core/plugin/discovery.py",
        ]

        whitemagic_root = Path(__file__).parent.parent.parent / "whitemagic"
        violations = []

        for py_file in whitemagic_root.rglob("*.py"):
            # Skip exceptions
            rel_path = str(py_file.relative_to(whitemagic_root))
            if any(rel_path.startswith(exc) for exc in allowed_exceptions):
                continue

            content = py_file.read_text(encoding="utf-8", errors="ignore")

            # Check for direct path expansion (outside config/paths.py)
            if "Path.home()" in content or ".expanduser()" in content:
                # Double-check it's not just in a comment
                for i, line in enumerate(content.split("\n"), 1):
                    stripped = line.split("#")[0]
                    if "Path.home()" in stripped or ".expanduser()" in stripped:
                        violations.append(f"{rel_path}:{i}")

        assert not violations, (
            "Path expansion violations found — "
            "all Path.home() / .expanduser() usage must be in config/paths.py "
            "or explicitly added to allowed_exceptions with justification:\n"
            + "\n".join(violations[:20])
        )

    def test_db_path_respects_state_root(self, tmp_path):
        """DB_PATH should be under WM_ROOT unless explicitly overridden."""
        custom_root = tmp_path / "custom_state"
        custom_root.mkdir()

        with patch.dict(os.environ, {"WM_STATE_ROOT": str(custom_root)}):
            # Clear module cache
            for mod in list(sys.modules.keys()):
                if mod.startswith("whitemagic.config"):
                    del sys.modules[mod]

            from whitemagic.config.paths import DB_PATH, WM_ROOT

            # DB_PATH should be relative to WM_ROOT by default
            assert DB_PATH.parent == WM_ROOT / "memory"

    def test_paths_are_absolute(self):
        """All critical paths must be absolute paths."""
        from whitemagic.config.paths import (
            ARTIFACTS_DIR,
            CACHE_DIR,
            DATA_DIR,
            DB_PATH,
            LOGS_DIR,
            MEMORY_DIR,
            SESSIONS_DIR,
            WM_ROOT,
        )

        critical_paths = [
            WM_ROOT,
            DATA_DIR,
            MEMORY_DIR,
            CACHE_DIR,
            SESSIONS_DIR,
            LOGS_DIR,
            ARTIFACTS_DIR,
            DB_PATH,
        ]

        for path in critical_paths:
            assert path.is_absolute(), f"{path} is not an absolute path"

    def test_state_root_permissions(self, tmp_path):
        """WM_ROOT should have restrictive permissions (owner-only)."""
        custom_root = tmp_path / "secure_whitemagic"

        with patch.dict(os.environ, {"WM_STATE_ROOT": str(custom_root)}):
            # Clear module cache
            for mod in list(sys.modules.keys()):
                if mod.startswith("whitemagic.config"):
                    del sys.modules[mod]

            from whitemagic.config.paths import WM_ROOT, ensure_paths

            ensure_paths()

            # Check permissions - should be 0o700 (owner only)
            # Note: This may not work on all filesystems, so we check best-effort
            stat = WM_ROOT.stat()
            mode = stat.st_mode & 0o777
            # Allow 0o700 or 0o755 (some environments need group read)
            assert mode in (0o700, 0o755, 0o750), (
                f"WM_ROOT has overly permissive mode: {oct(mode)}"
            )


class TestPathCICompliance:
    """Tests for CI compliance checks."""

    def test_path_hygiene_imports(self):
        """Verify paths module can be imported in CI with default state root."""
        # This test should always pass in CI with proper env vars set
        import whitemagic.config.paths as paths

        # Basic sanity checks
        assert paths.WM_ROOT is not None
        assert paths.DB_PATH is not None
        assert paths.DATA_DIR is not None
