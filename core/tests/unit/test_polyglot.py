"""Integration tests for polyglot holographic memory backends.

Tests the full stack: dispatch → handler → JSON stdio bridge → backend.
Skips gracefully if Julia/Elixir/Haskell are not available.
"""

import subprocess

import pytest


# --- Availability checks (cached at module level) ---

def _has_binary(name: str) -> bool:
    try:
        subprocess.run(
            [name, "--version"],
            capture_output=True,
            timeout=5,
            check=False,
        )
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


HAS_JULIA = _has_binary("julia")
HAS_ELIXIR = _has_binary("elixir")
HAS_HASKELL = _has_binary("runhaskell")


# --- Polyglot dispatcher availability ---

HAS_POLYGOLOT = True
try:
    from whitemagic.tools.handlers.polyglot import (
        handle_polyglot_memory_query,
        handle_polyglot_status,
    )
except ImportError:
    HAS_POLYGOLOT = False


class TestPolyglotStatus:
    """Test polyglot.status health check."""

    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_status_returns_success(self):
        result = handle_polyglot_status()
        assert result["status"] == "success"
        assert "backends" in result
        assert "health_score" in result
        assert 0.0 <= result["health_score"] <= 1.0

    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_status_has_expected_backends(self):
        result = handle_polyglot_status()
        backends = result["backends"]
        for name in ("julia", "elixir", "haskell", "rust"):
            assert name in backends
            assert "available" in backends[name]


class TestPolyglotMemoryQueryJulia:
    """Test polyglot.memory_query routed to Julia backend."""

    @pytest.mark.skipif(not HAS_JULIA, reason="julia not installed")
    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_julia_encode(self):
        result = handle_polyglot_memory_query(
            operation="encode",
            text="hello world",
            backend="julia",
        )
        assert result["status"] == "success"
        assert result["operation"] == "encode"
        assert "result" in result
        r = result["result"]
        assert "x" in r
        assert "y" in r
        assert "z" in r
        assert "w" in r
        assert "v" in r

    @pytest.mark.skipif(not HAS_JULIA, reason="julia not installed")
    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_julia_nearest_neighbors(self):
        result = handle_polyglot_memory_query(
            operation="nearest_neighbors",
            query="hello",
            texts=["hello world", "foo bar", "baz qux"],
            k=2,
            backend="julia",
        )
        assert result["status"] == "success"
        assert result["operation"] == "nearest_neighbors"
        r = result["result"]
        assert "results" in r
        assert len(r["results"]) == 2

    @pytest.mark.skipif(not HAS_JULIA, reason="julia not installed")
    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_julia_encode_deterministic(self):
        r1 = handle_polyglot_memory_query(
            operation="encode", text="same text", backend="julia"
        )
        r2 = handle_polyglot_memory_query(
            operation="encode", text="same text", backend="julia"
        )
        assert r1["result"] == r2["result"]


class TestPolyglotMemoryQueryElixir:
    """Test polyglot.memory_query routed to Elixir backend."""

    @pytest.mark.flaky(max_runs=3, min_passes=1)
    @pytest.mark.skipif(not HAS_ELIXIR, reason="elixir not installed")
    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_elixir_encode(self):
        result = handle_polyglot_memory_query(
            operation="encode",
            text="hello world",
            backend="elixir",
        )
        assert result["status"] == "success"
        r = result["result"]
        assert "x" in r
        assert "zone" in r

    @pytest.mark.flaky(max_runs=3, min_passes=1)
    @pytest.mark.skipif(not HAS_ELIXIR, reason="elixir not installed")
    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_elixir_nearest_neighbors(self):
        result = handle_polyglot_memory_query(
            operation="nearest_neighbors",
            query="hello",
            texts=["hello world", "foo bar", "baz qux"],
            k=2,
            backend="elixir",
        )
        assert result["status"] == "success"
        r = result["result"]
        assert "results" in r
        assert len(r["results"]) == 2


class TestPolyglotMemoryQueryHaskell:
    """Test polyglot.memory_query routed to Haskell backend."""

    @pytest.mark.skipif(not HAS_HASKELL, reason="runhaskell not available")
    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_haskell_encode(self):
        result = handle_polyglot_memory_query(
            operation="encode",
            text="hello world",
            backend="haskell",
        )
        assert result["status"] == "success"
        r = result["result"]
        assert "x" in r
        assert "zone" in r

    @pytest.mark.skipif(not HAS_HASKELL, reason="runhaskell not available")
    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_haskell_nearest_neighbors(self):
        result = handle_polyglot_memory_query(
            operation="nearest_neighbors",
            query="hello",
            texts=["hello world", "foo bar", "baz qux"],
            k=2,
            backend="haskell",
        )
        assert result["status"] == "success"
        r = result["result"]
        assert "results" in r
        assert len(r["results"]) == 2


class TestPolyglotMemoryQueryRust:
    """Test polyglot.memory_query routed to Rust backend."""

    def test_rust_encode(self):
        result = handle_polyglot_memory_query(
            operation="encode",
            text="hello world",
            backend="rust",
        )
        assert result["status"] == "success"
        r = result["result"]
        assert "x" in r
        assert "zone" in r

    def test_rust_nearest_neighbors(self):
        result = handle_polyglot_memory_query(
            operation="nearest_neighbors",
            query="hello",
            texts=["hello world", "foo bar", "baz qux"],
            k=2,
            backend="rust",
        )
        assert result["status"] == "success"
        r = result["result"]
        assert "results" in r
        assert len(r["results"]) == 2


class TestPolyglotMemoryQueryRustHRR:
    """Test Rust HRR operations."""

    def test_rust_encode_hrr(self):
        result = handle_polyglot_memory_query(
            operation="encode",
            text="hello world",
            backend="rust",
        )
        assert result["status"] == "success"

    def test_rust_dual_encode(self):
        # dual_encode is exposed via the bridge but not via the Python handler directly;
        # verify the backend is available through status
        result = handle_polyglot_status()
        assert result["status"] == "success"
        assert result["backends"]["rust"]["available"] is True


class TestPolyglotAutoFallback:
    """Test auto backend selection."""

    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_auto_backend_returns_success_for_any(self):
        # If ANY backend is available, auto should succeed
        status = handle_polyglot_status()
        available = [n for n, b in status["backends"].items() if b["available"]]
        if not available:
            pytest.skip("no polyglot backends available")

        result = handle_polyglot_memory_query(
            operation="encode",
            text="auto test",
            backend="auto",
        )
        assert result["status"] == "success"


class TestPolyglotSearch:
    """Test polyglot.search convenience tool."""

    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_search_rust_backend(self):
        from whitemagic.tools.handlers.polyglot import handle_polyglot_search
        result = handle_polyglot_search(
            query="hello",
            texts=["hello world", "foo bar", "baz qux"],
            k=2,
            backend="rust",
        )
        assert result["status"] == "success"
        assert "query_coord" in result
        assert "nearest_neighbors" in result


class TestPolyglotErrorHandling:
    """Test graceful degradation."""

    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_unknown_operation_returns_error(self):
        result = handle_polyglot_memory_query(
            operation="nonexistent_op",
            text="test",
            backend="julia",
        )
        assert result["status"] == "error"

    @pytest.mark.skipif(not HAS_POLYGOLOT, reason="polyglot handler unavailable")
    def test_missing_operation_returns_error(self):
        result = handle_polyglot_memory_query()
        assert result["status"] == "error"
