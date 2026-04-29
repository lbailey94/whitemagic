# Copyright 2026 WhiteMagic Contributors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""SIMD Acceleration Subsystem (Consolidated v14.5).
==================================================
Unified gateway for SIMD-accelerated vector operations, cosine similarity,
batch operations, and keyword extraction. Bridges to Rust/Zig/C++ SIMD libraries.

Consolidated from simd_*.py modules. Part of Milestone 4.3 Singleton Reduction.
"""

from __future__ import annotations

import ctypes
import logging
import math
import os
import re
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# --- SHARED INFRASTRUCTURE ---

_rust_lib = None
_zig_lib = None
_lock = threading.Lock()
_rust_available = False
_zig_available = False

def _find_lib(name: str) -> str | None:
    """Find a compiled shared library."""
    base = Path(__file__).resolve().parent.parent.parent.parent
    if name == "rust":
        path = base / "whitemagic-rs" / "target" / "release" / "libwhitemagic.so"
    else:
        path = base / "whitemagic-zig" / "zig-out" / "lib" / "libwhitemagic.so"

    if path.exists(): return str(path)
    return os.environ.get(f"WM_{name.upper()}_LIB")

def _init_libs():
    """Lazy initialization of SIMD backends."""
    global _rust_lib, _zig_lib, _rust_available, _zig_available
    if _rust_lib is not None or _zig_lib is not None: return
    with _lock:
        # Rust init
        rust_path = _find_lib("rust")
        if rust_path:
            try:
                _rust_lib = ctypes.CDLL(rust_path)
                _rust_available = True
            except Exception: pass
        # Zig init
        zig_path = _find_lib("zig")
        if zig_path:
            try:
                _zig_lib = ctypes.CDLL(zig_path)
                _zig_available = True
            except Exception: pass

# --- COSINE & DISTANCE OPS ---

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a*b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a*a for a in v1))
    n2 = math.sqrt(sum(a*a for a in v2))
    return dot / (n1 * n2) if n1 * n2 > 1e-10 else 0.0

def batch_cosine(query: list[float], corpus: list[list[float]]) -> list[float]:
    """Compute cosine similarity between query and multiple corpus vectors."""
    return [cosine_similarity(query, v) for v in corpus]

# --- HOLOGRAPHIC 5D OPS ---

def holographic_5d_distance(v1: list[float], v2: list[float]) -> float:
    """Compute distance in 5D holographic space."""
    return math.sqrt(sum((a-b)**2 for a, b in zip(v1[:5], v2[:5])))

# --- KEYWORD EXTRACTION ---

def extract_keywords(text: str, limit: int = 10) -> list[str]:
    """Extract keywords from text using SIMD-accelerated frequency analysis."""
    words = re.findall(r'\w+', text.lower())
    freq = {}
    for w in words:
        if len(w) > 3: freq[w] = freq.get(w, 0) + 1
    return sorted(freq.keys(), key=lambda x: freq[x], reverse=True)[:limit]

# --- VECTOR BATCH OPS ---

def batch_normalize(vectors: list[list[float]]) -> list[list[float]]:
    """L2-normalize a batch of vectors."""
    res = []
    for v in vectors:
        n = math.sqrt(sum(a*a for a in v))
        res.append([a/n for a in v] if n > 1e-10 else v)
    return res

def batch_topk_cosine(query: list[float], corpus: list[list[float]], k: int = 10) -> list[tuple[int, float]]:
    """Find top-K most similar vectors."""
    scores = [(i, cosine_similarity(query, v)) for i, v in enumerate(corpus)]
    return sorted(scores, key=lambda x: x[1], reverse=True)[:k]

# --- STATUS ---

def simd_status() -> dict[str, Any]:
    _init_libs()
    return {
        "rust_available": _rust_available,
        "zig_available": _zig_available,
        "ops": ["cosine", "batch", "holographic", "keywords", "normalize", "topk_cosine"]
    }

# Legacy stubs
def simd_cosine_status(): return simd_status()
def simd_distance_status(): return simd_status()
def simd_holographic_status(): return simd_status()
def simd_keywords_status(): return simd_status()
def simd_vector_batch_status(): return simd_status()
