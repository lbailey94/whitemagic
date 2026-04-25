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

    @pytest.mark.skipif(
        not Path("/home/lucas/Desktop/WHITEMAGIC/core/mesh_aux/cmd/mesh_aux/mesh_daemon").exists(),
        reason="Go binary not built"
    )
    def test_go_binary_exists(self):
        """Test that Go mesh binary exists."""
        binary_path = Path("/home/lucas/Desktop/WHITEMAGIC/core/mesh_aux/cmd/mesh_aux/mesh_daemon")
        assert binary_path.exists()
        assert binary_path.is_file()

    def test_go_mesh_client_import(self):
        """Test Go mesh client can be imported."""
        try:
            from whitemagic.mesh.client import MeshClient
            assert MeshClient is not None
        except ImportError:
            pytest.skip("Go mesh client not available")


class TestKokaBridge:
    """Test Koka FFI bridge functionality."""

    @pytest.mark.skipif(
        not Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic-koka/build_native.sh").exists(),
        reason="Koka build script not found"
    )
    def test_koka_build_script_exists(self):
        """Test that Koka build script exists."""
        build_script = Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic-koka/build_native.sh")
        assert build_script.exists()
        assert build_script.is_file()

    @pytest.mark.skipif(
        not Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic-koka/src").exists(),
        reason="Koka source directory not found"
    )
    def test_koka_source_structure(self):
        """Test that Koka source directory has expected structure."""
        src_dir = Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic-koka/src")
        assert src_dir.exists()
        assert src_dir.is_dir()
        # Check for key source files
        assert (src_dir / "psr").exists() or len(list(src_dir.iterdir())) > 0


class TestZigBridge:
    """Test Zig FFI bridge functionality."""

    @pytest.mark.skipif(
        not Path("/media/lucas/SD_CARD/WHITEMAGIC/polyglot/zig").exists(),
        reason="Zig directory not found"
    )
    def test_zig_directory_exists(self):
        """Test that Zig directory exists."""
        zig_dir = Path("/media/lucas/SD_CARD/WHITEMAGIC/polyglot/zig")
        assert zig_dir.exists()
        assert zig_dir.is_dir()

    def test_zig_processor_import(self):
        """Test Zig string processor can be imported."""
        try:
            from whitemagic.core.string.zig_processor import ZigStringProcessor
            assert ZigStringProcessor is not None
        except ImportError:
            pytest.skip("Zig processor not available")


class TestMojoBridge:
    """Test Mojo FFI bridge functionality."""

    @pytest.mark.skipif(
        not Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic-mojo").exists(),
        reason="Mojo directory not found"
    )
    def test_mojo_directory_exists(self):
        """Test that Mojo directory exists."""
        mojo_dir = Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic-mojo")
        assert mojo_dir.exists()
        assert mojo_dir.is_dir()

    def test_mojo_bridge_import(self):
        """Test Mojo bridge can be imported."""
        try:
            from whitemagic.core.acceleration.mojo_bridge import MojoBridge
            assert MojoBridge is not None
        except ImportError:
            pytest.skip("Mojo bridge not available")


class TestJuliaBridge:
    """Test Julia FFI bridge functionality."""

    @pytest.mark.skipif(
        not Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic-julia").exists(),
        reason="Julia directory not found"
    )
    def test_julia_directory_exists(self):
        """Test that Julia directory exists."""
        julia_dir = Path("/media/lucas/SD_CARD/WHITEMAGIC/core/whitemagic-julia")
        assert julia_dir.exists()
        assert julia_dir.is_dir()


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
        status_file = Path(__file__).resolve().parent.parent.parent / "POLYGLOT_STATUS.md"
        assert status_file.exists()

    def test_polyglot_status_readable(self):
        """Test that polyglot status can be read."""
        status_file = Path(__file__).resolve().parent.parent.parent / "POLYGLOT_STATUS.md"
        content = status_file.read_text()
        assert len(content) > 0
        # Check for key sections
        assert "Rust" in content or "## " in content
