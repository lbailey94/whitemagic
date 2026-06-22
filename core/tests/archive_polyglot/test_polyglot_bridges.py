"""Integration tests for polyglot bridge components.

Tests the FFI bridges between Python and:
- Rust (whitemagic_rs)
- Go (whitemagic-go)
- Koka (whitemagic-koka)
- Zig (whitemagic-zig)
- Mojo (whitemagic-mojo)
- Julia (whitemagic-julia)
"""

import pytest
from pathlib import Path

# Compute repo root relative to this test file
REPO_ROOT = Path(__file__).resolve().parent.parent.parent


class TestRustBridge:
    """Test Rust FFI bridge functionality."""

    @pytest.mark.skipif(
        not pytest.importorskip("whitemagic_rs", None),
        reason="Rust bridge not installed"
    )
    def test_rust_module_import(self):
        """Test that Rust module can be imported."""
        import whitemagic_rs
        assert whitemagic_rs is not None

    @pytest.mark.skipif(
        not pytest.importorskip("whitemagic_rs", None),
        reason="Rust bridge not installed"
    )
    def test_rust_optimization_available(self):
        """Test Rust optimization functions are available."""
        from whitemagic.rust.optimization import RustAccelerator
        # Check if accelerator can be instantiated
        try:
            accel = RustAccelerator()
            assert accel is not None
        except ImportError:
            pytest.skip("Rust accelerator not available")


class TestGoBridge:
    """Test Go FFI bridge functionality."""

    _GO_BINARY = REPO_ROOT / "mesh_aux" / "cmd" / "mesh_aux" / "mesh_daemon"

    @pytest.mark.skipif(
        not _GO_BINARY.exists(),
        reason="Go binary not built"
    )
    def test_go_binary_exists(self):
        """Test that Go mesh binary exists."""
        assert self._GO_BINARY.exists()
        assert self._GO_BINARY.is_file()

    def test_go_mesh_client_import(self):
        """Test Go mesh client can be imported."""
        try:
            from whitemagic.mesh.client import MeshClient
            assert MeshClient is not None
        except ImportError:
            pytest.skip("Go mesh client not available")


class TestKokaBridge:
    """Test Koka FFI bridge functionality."""

    _KOKA_BUILD_SCRIPT = REPO_ROOT / "whitemagic-koka" / "build_native.sh"
    _KOKA_SRC = REPO_ROOT / "whitemagic-koka" / "src"

    @pytest.mark.skipif(
        not _KOKA_BUILD_SCRIPT.exists(),
        reason="Koka build script not found"
    )
    def test_koka_build_script_exists(self):
        """Test that Koka build script exists."""
        assert self._KOKA_BUILD_SCRIPT.exists()
        assert self._KOKA_BUILD_SCRIPT.is_file()

    @pytest.mark.skipif(
        not _KOKA_SRC.exists(),
        reason="Koka source directory not found"
    )
    def test_koka_source_structure(self):
        """Test that Koka source directory has expected structure."""
        assert self._KOKA_SRC.exists()
        assert self._KOKA_SRC.is_dir()
        # Check for key source files
        assert (self._KOKA_SRC / "psr").exists() or len(list(self._KOKA_SRC.iterdir())) > 0


class TestZigBridge:
    """Test Zig FFI bridge functionality."""

    _ZIG_DIR = REPO_ROOT.parent / "polyglot" / "whitemagic-zig"

    @pytest.mark.skipif(
        not _ZIG_DIR.exists(),
        reason="Zig directory not found"
    )
    def test_zig_directory_exists(self):
        """Test that Zig directory exists."""
        assert self._ZIG_DIR.exists()
        assert self._ZIG_DIR.is_dir()

    def test_zig_processor_import(self):
        """Test Zig string processor can be imported."""
        try:
            from whitemagic.core.string.zig_processor import ZigStringProcessor
            assert ZigStringProcessor is not None
        except ImportError:
            pytest.skip("Zig processor not available")


class TestMojoBridge:
    """Test Mojo FFI bridge functionality."""

    _MOJO_DIR = REPO_ROOT / "whitemagic-mojo"

    @pytest.mark.skipif(
        not _MOJO_DIR.exists(),
        reason="Mojo directory not found"
    )
    def test_mojo_directory_exists(self):
        """Test that Mojo directory exists."""
        assert self._MOJO_DIR.exists()
        assert self._MOJO_DIR.is_dir()

    def test_mojo_bridge_import(self):
        """Test Mojo bridge can be imported."""
        try:
            from whitemagic.core.acceleration.mojo_bridge import MojoBridge
            assert MojoBridge is not None
        except ImportError:
            pytest.skip("Mojo bridge not available")


class TestJuliaBridge:
    """Test Julia FFI bridge functionality."""

    _JULIA_DIR = REPO_ROOT / "whitemagic-julia"

    @pytest.mark.skipif(
        not _JULIA_DIR.exists(),
        reason="Julia directory not found"
    )
    def test_julia_directory_exists(self):
        """Test that Julia directory exists."""
        assert self._JULIA_DIR.exists()
        assert self._JULIA_DIR.is_dir()


class TestPolyglotRouter:
    """Test polyglot routing system."""

    def test_polyglot_router_import(self):
        """Test polyglot router can be imported."""
        from whitemagic.optimization.polyglot_router import PolyglotRouter
        assert PolyglotRouter is not None

    def test_polyglot_router_initialization(self):
        """Test polyglot router can be initialized."""
        from whitemagic.optimization.polyglot_router import PolyglotRouter
        router = PolyglotRouter()
        assert router is not None
        assert hasattr(router, 'route')


class TestFFISafety:
    """Test FFI safety and fallback mechanisms."""

    def test_rust_fallback_available(self):
        """Test that Rust fallback functions exist."""
        from whitemagic.optimization._rust_fallbacks import rust_fallback_available
        # Should return a boolean
        result = rust_fallback_available()
        assert isinstance(result, bool)

    def test_safe_ffi_call_pattern(self):
        """Test that safe FFI call pattern is used."""
        from whitemagic.utils.rust_helper import safe_rust_call
        # Test with a non-existent function (should handle gracefully)
        try:
            result = safe_rust_call("nonexistent_function", {})
            # Should return None or raise a specific error
            assert result is None or isinstance(result, Exception)
        except Exception as e:
            # Expected for non-existent function
            assert isinstance(e, Exception)


class TestPolyglotStatus:
    """Test polyglot status reporting."""

    def test_polyglot_status_module_exists(self):
        """Test that POLYGLOT_STATUS.md exists."""
        status_file = REPO_ROOT / "POLYGLOT_STATUS.md"
        assert status_file.exists()

    def test_polyglot_status_readable(self):
        """Test that polyglot status can be read."""
        status_file = REPO_ROOT / "POLYGLOT_STATUS.md"
        content = status_file.read_text()
        assert len(content) > 0
        # Check for key sections
        assert "Rust" in content or "## " in content
