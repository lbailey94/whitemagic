# ruff: noqa: BLE001
"""
HRR Integration Layer — Python-only (Mojo removed in v23.2).
Previously bridged Python HRR calls to Mojo implementation for 10-50x speedup.
Now uses Python FFT implementation directly.
"""
import logging
from typing import cast

import numpy as np

logger = logging.getLogger(__name__)


class HRRBridge:
    """Python-only HRR bridge (Mojo removed in v23.2)."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def bind(self, a: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Circular convolution: bind(A, B) via FFT."""
        return cast(np.ndarray, np.real(np.fft.ifft(np.fft.fft(a) * np.fft.fft(b))).astype(np.float32))

    def unbind(self, bound: np.ndarray, b: np.ndarray) -> np.ndarray:
        """Circular correlation: unbind(bound, B) via FFT."""
        return cast(np.ndarray, np.real(np.fft.ifft(
            np.conj(np.fft.fft(b)) * np.fft.fft(bound)
        )).astype(np.float32))


# Backward compat alias
HRRMojoBridge = HRRBridge


def patch_hrr_engine():
    """No-op patch function (Mojo removed in v23.2)."""
    return False
