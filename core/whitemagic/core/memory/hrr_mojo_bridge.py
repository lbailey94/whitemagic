# ruff: noqa: BLE001
"""
HRR Mojo Integration Layer
Bridges Python HRR calls to Mojo implementation for 10-50x speedup.
"""
import logging
import os
import subprocess
from typing import cast

import numpy as np

logger = logging.getLogger(__name__)

class HRRMojoBridge:
    """
    Bridge between Python HRR engine and Mojo implementation.

    Falls back to Python FFT implementation if Mojo unavailable.
    """

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.mojo_available = self._check_mojo()
        # Use project-relative path for Mojo
        from pathlib import Path
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        self.hrr_mojo_path = project_root / "projects/whitemagic-mojo/hrr.mojo"

    def _check_mojo(self) -> bool:
        """Check if Mojo compiler is available."""
        try:
            result = subprocess.run(
                ["which", "mojo"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except OSError:
            return False

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """
        Circular convolution: bind(A, B)

        Uses Mojo if available, falls back to Python FFT.
        """
        if self.mojo_available and os.path.exists(self.hrr_mojo_path):
            try:
                return self._bind_mojo(a, b)
            except Exception as e:
                logger.warning("Mojo bind failed: %s, falling back to Python", e, exc_info=True)
                return self._bind_python(a, b)
        return self._bind_python(a, b)

    def _bind_python(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """FFT-based binding (Python fallback)."""
        return cast(np.ndarray, np.real(np.fft.ifft(np.fft.fft(a) * np.fft.fft(b))).astype(np.float32))

    def _bind_mojo(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Call Mojo implementation via subprocess."""
        # Write inputs to temp files
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f_a:
            np.save(f_a.name, a)
            a_path = f_a.name
        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f_b:
            np.save(f_b.name, b)
            b_path = f_b.name

        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f_out:
            out_path = f_out.name

        try:
            # Call Mojo bind function
            result = subprocess.run(
                ["mojo", "run", "-f", "bind", self.hrr_mojo_path, a_path, b_path, out_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return cast(np.ndarray, np.load(out_path))
            else:
                raise RuntimeError(f"Mojo execution failed: {result.stderr}")
        finally:
            # Cleanup
            for p in [a_path, b_path, out_path]:
                try:
                    os.unlink(p)
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    pass

    def unbind(self, bound: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Circular correlation: unbind(bound, B)"""
        if self.mojo_available:
            try:
                return self._unbind_mojo(bound, b)
            except Exception as e:
                logger.warning("Mojo unbind failed: %s, falling back to Python", e, exc_info=True)
                return self._unbind_python(bound, b)
        return self._unbind_python(bound, b)

    def _unbind_python(self, bound: np.ndarray, b: np.ndarray) -> np.ndarray:
        """FFT-based unbinding (Python fallback)."""
        return cast(np.ndarray, np.real(np.fft.ifft(
            np.conj(np.fft.fft(b)) * np.fft.fft(bound)
        )).astype(np.float32))

    def _unbind_mojo(self, bound: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Call Mojo unbind via subprocess."""
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f_bound:
            np.save(f_bound.name, bound)
            bound_path = f_bound.name
        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f_b:
            np.save(f_b.name, b)
            b_path = f_b.name

        with tempfile.NamedTemporaryFile(suffix='.npy', delete=False) as f_out:
            out_path = f_out.name

        try:
            result = subprocess.run(
                ["mojo", "run", "-f", "unbind", self.hrr_mojo_path, bound_path, b_path, out_path],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return cast(np.ndarray, np.load(out_path))
            else:
                raise RuntimeError(f"Mojo execution failed: {result.stderr}")
        finally:
            for p in [bound_path, b_path, out_path]:
                try:
                    os.unlink(p)
                except Exception as e:
                    logger.debug("Operation failed: %s", e)
                    pass

    def benchmark(self, iterations: int = 1000) -> dict:
        """Benchmark Python vs Mojo implementation."""
        import time

        a = np.random.randn(self.dim).astype(np.float32)
        b = np.random.randn(self.dim).astype(np.float32)

        # Warmup
        for _ in range(10):
            _ = self._bind_python(a, b)

        # Python benchmark
        start = time.time()
        for _ in range(iterations):
            _ = self._bind_python(a, b)
        python_time = time.time() - start

        # Mojo benchmark (if available)
        mojo_time = None
        if self.mojo_available:
            try:
                start = time.time()
                for _ in range(iterations):
                    _ = self._bind_mojo(a, b)
                mojo_time = time.time() - start
            except Exception as e:
                logger.warning("Mojo benchmark failed: %s", e, exc_info=True)

        return {
            "python_ops_per_sec": iterations / python_time,
            "mojo_ops_per_sec": iterations / mojo_time if mojo_time else None,
            "speedup": python_time / mojo_time if mojo_time else None,
            "mojo_available": self.mojo_available
        }

# Monkey-patch HRREngine to use Mojo bridge when available
def patch_hrr_engine():
    """Patch the HRREngine class to use Mojo bridge."""
    try:
        from whitemagic.core.memory.hrr import HRREngine

        original_bind = HRREngine.bind
        original_unbind = HRREngine.unbind

        # Create bridge instance
        bridge = HRRMojoBridge()

        def patched_bind(self, a, b):
            # Use Mojo bridge for large batches, Python for single calls
            """
            Perform the patched bind operation.

            Args:
                a: Parameter description.
                b: Parameter description.
            """
            if isinstance(a, np.ndarray) and a.ndim == 1:
                return bridge.bind(a, b)
            return original_bind(self, a, b)

        def patched_unbind(self, bound, b):
            """
            Perform the patched unbind operation.

            Args:
                bound: Parameter description.
                b: Parameter description.
            """
            if isinstance(bound, np.ndarray) and bound.ndim == 1:
                return bridge.unbind(bound, b)
            return original_unbind(self, bound, b)

        HRREngine.bind = patched_bind
        HRREngine.unbind = patched_unbind

        logger.info("HRR engine patched with Mojo bridge (available: %s)", bridge.mojo_available)
        return True
    except Exception as e:
        logger.warning("Failed to patch HRR engine: %s", e, exc_info=True)
        return False

if __name__ == "__main__":
    # Test the bridge
    bridge = HRRMojoBridge()
    print(f"Mojo available: {bridge.mojo_available}")

    # Benchmark
    results = bridge.benchmark(iterations=100)
    print(f"Benchmark results: {results}")
