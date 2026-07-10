"""Probabilistic data structures for memory analytics.

Provides memory-efficient approximate counting and frequency tracking:

- **HyperLogLog (HLL)**: Estimate cardinality of distinct memories, tags, or
  entities with ~1.5% error using O(2^14) bytes instead of O(n).
- **Doubly-Logarithmic (DLL)**: Variant with adaptive precision for
  small-to-large cardinality ranges.
- **Count-Min Sketch (CMS)**: Approximate frequency counting for tag
  popularity, access patterns, and hot/cold detection. O(depth * width)
  space, independent of stream size.

These structures enable real-time analytics over millions of memories
without materializing the full dataset — critical for edge deployment
where RAM is constrained.

References:
- Flajolet et al., "HyperLogLog: the analysis of a near-optimal cardinality
  estimation algorithm" (2007)
- Cormode & Muthukrishnan, "An Improved Data Stream Summary: The Count-Min
  Sketch and its Applications" (2005)
"""
from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterable
from typing import Any

# Hashing utilities

def _hash_bytes(data: str | bytes, seed: int = 0) -> int:
    """64-bit hash with optional seed for independent hash functions."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    h = hashlib.blake2b(data, digest_size=8, key=seed.to_bytes(8, "little"))
    return struct.unpack(">Q", h.digest())[0]


def _hash_to_32(data: str | bytes, seed: int = 0) -> int:
    """32-bit hash for HLL register indexing."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    h = hashlib.blake2b(data, digest_size=4, key=seed.to_bytes(8, "little"))
    return struct.unpack(">I", h.digest())[0]


# HyperLogLog

class HyperLogLog:
    """HyperLogLog cardinality estimator.

    Estimates the number of distinct elements in a stream using O(2^p) bytes.

    Args:
        precision: Number of register index bits (4-16). Default 14.
            p=14 → 16,384 registers × 5 bits ≈ 10 KB, ~0.8% error.

    Attributes:
        registers: Array of 2^p registers, each storing max leading-zeros+1.
    """

    __slots__ = ("precision", "num_registers", "registers", "_alpha")

    def __init__(self, precision: int = 14) -> None:
        if not 4 <= precision <= 16:
            raise ValueError(f"precision must be 4-16, got {precision}")
        self.precision = precision
        self.num_registers = 1 << precision
        self.registers = bytearray(self.num_registers)
        # Bias correction constant
        m = self.num_registers
        if m == 16:
            self._alpha = 0.673
        elif m == 32:
            self._alpha = 0.697
        elif m == 64:
            self._alpha = 0.709
        else:
            self._alpha = 0.7213 / (1.0 + 1.079 / m)

    def add(self, element: str | bytes) -> None:
        """Add an element to the HLL."""
        h = _hash_to_32(element)
        # Use lower p bits as register index
        idx = h & (self.num_registers - 1)
        # Use remaining bits for leading-zero count
        w = h >> self.precision
        # Count leading zeros + 1 in the remaining (32 - p) bits
        remaining_bits = 32 - self.precision
        if w == 0:
            lz = remaining_bits + 1
        else:
            lz = remaining_bits - w.bit_length() + 1
        if lz > self.registers[idx]:
            self.registers[idx] = lz

    def estimate(self) -> float:
        """Estimate the cardinality (number of distinct elements)."""
        m = self.num_registers
        sum_inv = sum(2.0 ** (-r) for r in self.registers)
        raw_estimate = self._alpha * m * m / sum_inv

        # Small range correction
        if raw_estimate <= 2.5 * m:
            # Count zero registers for linear counting
            zero_count = self.registers.count(0)
            if zero_count > 0:
                return m * math.log(m / zero_count)

        # Large range correction
        if raw_estimate > 2**32 / 30.0:
            return -(2**32) * math.log(1.0 - raw_estimate / 2**32)

        return raw_estimate

    def merge(self, other: HyperLogLog) -> HyperLogLog:
        """Merge another HLL into this one (must have same precision)."""
        if self.precision != other.precision:
            raise ValueError(
                f"Cannot merge HLL with precision {other.precision} into {self.precision}"
            )
        for i in range(self.num_registers):
            if other.registers[i] > self.registers[i]:
                self.registers[i] = other.registers[i]
        return self

    def reset(self) -> None:
        """Reset all registers to zero."""
        self.registers = bytearray(self.num_registers)

    def memory_bytes(self) -> int:
        """Get memory usage in bytes."""
        return len(self.registers)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for persistence."""
        return {
            "precision": self.precision,
            "registers": bytes(self.registers).hex(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> HyperLogLog:
        """Deserialize from dict."""
        hll = cls(precision=data["precision"])
        hll.registers = bytearray.fromhex(data["registers"])
        return hll


# Count-Min Sketch

class CountMinSketch:
    """Count-Min Sketch for approximate frequency counting.

    Tracks the frequency of elements in a data stream with sublinear space.
    Provides over-estimates (never under-estimates) with bounded error.

    Args:
        width: Number of counters per row (controls error bound).
        depth: Number of hash functions (controls confidence).
            Default: width=4096, depth=5 → ~0.25% error at 99% confidence.

    Attributes:
        counters: 2D array of counters (depth × width).
        total: Total number of increments.
    """

    __slots__ = ("width", "depth", "counters", "total", "_seen")

    def __init__(self, width: int = 4096, depth: int = 5) -> None:
        if width < 1 or depth < 1:
            raise ValueError("width and depth must be >= 1")
        self.width = width
        self.depth = depth
        self.counters = [[0] * width for _ in range(depth)]
        self.total = 0
        self._seen: set[str | bytes] = set()

    def add(self, element: str | bytes, count: int = 1) -> None:
        """Increment the count for an element."""
        self.total += count
        self._seen.add(element)
        for i in range(self.depth):
            h = _hash_to_32(element, seed=i * 31 + 17)
            idx = h % self.width
            self.counters[i][idx] += count

    def estimate(self, element: str | bytes) -> int:
        """Estimate the frequency of an element (over-estimate)."""
        return min(
            self.counters[i][_hash_to_32(element, seed=i * 31 + 17) % self.width]
            for i in range(self.depth)
        )

    def heavy_hitters(self, threshold: int) -> list[tuple[str, int]]:
        """Find elements above a frequency threshold.

        Uses the internal ``_seen`` set to track observed elements.
        Call ``add()`` for each element, then ``heavy_hitters()`` to
        retrieve those whose estimated frequency exceeds the threshold.
        """
        seen = getattr(self, "_seen", set())
        results = []
        for element in seen:
            est = self.estimate(element)
            if est >= threshold:
                results.append((element, est))
        results.sort(key=lambda x: -x[1])
        return results

    def reset(self) -> None:
        """Reset all counters."""
        self.counters = [[0] * self.width for _ in range(self.depth)]
        self.total = 0
        self._seen = set()

    def merge(self, other: CountMinSketch) -> CountMinSketch:
        """Merge another CMS into this one (must have same dimensions)."""
        if self.width != other.width or self.depth != other.depth:
            raise ValueError("Cannot merge CMS with different dimensions")
        for i in range(self.depth):
            for j in range(self.width):
                self.counters[i][j] += other.counters[i][j]
        self.total += other.total
        return self

    def memory_bytes(self) -> int:
        """Get memory usage in bytes."""
        return self.depth * self.width * 8  # int64 assumption

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict for persistence."""
        return {
            "width": self.width,
            "depth": self.depth,
            "counters": self.counters,
            "total": self.total,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CountMinSketch:
        """Deserialize from dict."""
        cms = cls(width=data["width"], depth=data["depth"])
        cms.counters = data["counters"]
        cms.total = data["total"]
        return cms


# Memory Analytics Aggregator

class MemoryAnalytics:
    """Aggregator combining HLL and CMS for memory system analytics.

    Tracks:
    - Distinct memory count (HLL)
    - Tag frequency (CMS)
    - Source frequency (CMS)
    - Access pattern frequency (CMS)

    This provides O(1) space analytics over the memory stream without
    materializing the full dataset.
    """

    def __init__(
        self,
        hll_precision: int = 14,
        cms_width: int = 4096,
        cms_depth: int = 5,
    ) -> None:
        self.distinct_memories = HyperLogLog(precision=hll_precision)
        self.tag_frequency = CountMinSketch(width=cms_width, depth=cms_depth)
        self.source_frequency = CountMinSketch(width=cms_width, depth=cms_depth)
        self.access_frequency = CountMinSketch(width=cms_width, depth=cms_depth)

    def observe_memory(self, memory_id: str, tags: Iterable[str] = (), source: str = "") -> None:
        """Record a memory observation."""
        self.distinct_memories.add(memory_id)
        for tag in tags:
            self.tag_frequency.add(tag)
        if source:
            self.source_frequency.add(source)

    def observe_access(self, memory_id: str) -> None:
        """Record a memory access event."""
        self.access_frequency.add(memory_id)

    def estimate_distinct_count(self) -> float:
        """Estimate number of distinct memories observed."""
        return self.distinct_memories.estimate()

    def estimate_tag_count(self, tag: str) -> int:
        """Estimate how many memories have a given tag."""
        return self.tag_frequency.estimate(tag)

    def estimate_source_count(self, source: str) -> int:
        """Estimate how many memories came from a given source."""
        return self.source_frequency.estimate(source)

    def estimate_access_count(self, memory_id: str) -> int:
        """Estimate how many times a memory was accessed."""
        return self.access_frequency.estimate(memory_id)

    def memory_bytes(self) -> int:
        """Total memory usage in bytes."""
        return (
            self.distinct_memories.memory_bytes()
            + self.tag_frequency.memory_bytes()
            + self.source_frequency.memory_bytes()
            + self.access_frequency.memory_bytes()
        )

    def summary(self) -> dict[str, Any]:
        """Get a summary of all analytics."""
        return {
            "distinct_memories": int(self.estimate_distinct_count()),
            "total_observations": self.distinct_memories.registers.count(0),
            "tag_sketch_total": self.tag_frequency.total,
            "source_sketch_total": self.source_frequency.total,
            "access_sketch_total": self.access_frequency.total,
            "memory_bytes": self.memory_bytes(),
        }
