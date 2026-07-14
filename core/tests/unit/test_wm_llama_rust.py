# ruff: noqa: BLE001
"""Tests for wm-llama Rust FFI crate (Phase 5)."""

from __future__ import annotations

import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="wm_test_")
os.environ["WM_STATE_ROOT"] = _tmp
os.environ["WM_SILENT_INIT"] = "1"


class TestWmLlamaCrate:
    """Test that the wm-llama Rust crate exists and is structured correctly."""

    def test_crate_directory_exists(self):
        from pathlib import Path
        crate_path = Path(__file__).resolve().parents[3] / "polyglot" / "whitemagic-rs" / "crates" / "wm-llama"
        assert crate_path.exists(), "wm-llama crate directory should exist"
        assert (crate_path / "Cargo.toml").exists(), "Cargo.toml should exist"
        assert (crate_path / "src" / "lib.rs").exists(), "lib.rs should exist"

    def test_crate_in_workspace(self):
        from pathlib import Path
        workspace_toml = Path(__file__).resolve().parents[3] / "polyglot" / "whitemagic-rs" / "Cargo.toml"
        content = workspace_toml.read_text()
        assert "wm-llama" in content, "wm-llama should be in workspace members"

    def test_crate_has_pyo3_feature(self):
        from pathlib import Path
        crate_toml = Path(__file__).resolve().parents[3] / "polyglot" / "whitemagic-rs" / "crates" / "wm-llama" / "Cargo.toml"
        content = crate_toml.read_text()
        assert "pyo3" in content, "Cargo.toml should have pyo3 dependency"
        assert "extension-module" in content, "Should have extension-module feature"

    def test_lib_rs_has_functions(self):
        from pathlib import Path
        lib_rs = Path(__file__).resolve().parents[3] / "polyglot" / "whitemagic-rs" / "crates" / "wm-llama" / "src" / "lib.rs"
        content = lib_rs.read_text()
        # Check for key functions
        assert "estimate_tokens" in content
        assert "approximate_tokenize" in content
        assert "check_prompt_budget" in content
        assert "cosine_similarity" in content
        assert "batch_cosine_similarity" in content
        assert "top_k" in content
        assert "pseudo_embed" in content
        assert "cache_model_info" in content
        assert "get_cached_model_info" in content
        assert "batch_estimate_tokens" in content

    def test_lib_rs_has_cfg_guards(self):
        from pathlib import Path
        lib_rs = Path(__file__).resolve().parents[3] / "polyglot" / "whitemagic-rs" / "crates" / "wm-llama" / "src" / "lib.rs"
        content = lib_rs.read_text()
        assert 'cfg(feature = "pyo3")' in content, "Should have cfg guards for pyo3 feature"

    def test_lib_rs_has_inner_functions(self):
        from pathlib import Path
        lib_rs = Path(__file__).resolve().parents[3] / "polyglot" / "whitemagic-rs" / "crates" / "wm-llama" / "src" / "lib.rs"
        content = lib_rs.read_text()
        # Inner functions should exist for testing without pyo3
        assert "estimate_tokens_inner" in content
        assert "cosine_similarity_inner" in content
        assert "top_k_inner" in content

    def test_lib_rs_has_tests(self):
        from pathlib import Path
        lib_rs = Path(__file__).resolve().parents[3] / "polyglot" / "whitemagic-rs" / "crates" / "wm-llama" / "src" / "lib.rs"
        content = lib_rs.read_text()
        assert "#[test]" in content, "Should have Rust tests"
        assert "test_estimate_tokens" in content
        assert "test_cosine_similarity" in content
        assert "test_top_k" in content

    def test_lib_rs_has_pymodule(self):
        from pathlib import Path
        lib_rs = Path(__file__).resolve().parents[3] / "polyglot" / "whitemagic-rs" / "crates" / "wm-llama" / "src" / "lib.rs"
        content = lib_rs.read_text()
        assert "#[pymodule]" in content, "Should have pymodule definition"
        assert "fn wm_llama" in content, "Should have wm_llama module function"


class TestDualModelManagerSingleton:
    """Test the DualModelManager singleton from Phase 4."""

    def test_get_dual_model_manager_none_without_env(self):
        import os

        from whitemagic.inference import llama_cpp as _lc
        old_bg = os.environ.pop("WM_LLAMA_BG_MODEL", None)
        old_fg = os.environ.pop("WM_LLAMA_FG_MODEL", None)
        _lc._dual_manager = None
        try:
            assert _lc.get_dual_model_manager() is None
        finally:
            if old_bg:
                os.environ["WM_LLAMA_BG_MODEL"] = old_bg
            if old_fg:
                os.environ["WM_LLAMA_FG_MODEL"] = old_fg
            _lc._dual_manager = None

    def test_router_has_dual_model_import(self):
        from pathlib import Path
        router_path = Path(__file__).resolve().parents[3] / "core" / "whitemagic" / "inference" / "router.py"
        content = router_path.read_text()
        assert "get_dual_model_manager" in content, "Router should import dual model manager"
        assert "is_background" in content, "Router should support background flag"
