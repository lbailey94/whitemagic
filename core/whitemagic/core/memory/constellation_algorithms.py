"""Constellation Clustering Algorithms.

Extracted from constellations.py for better separation of concerns.
Provides HDBSCAN and grid-based clustering for 5D holographic coordinates.
"""

import logging
import math
from collections import defaultdict
from typing import Any, cast

logger = logging.getLogger(__name__)

# Rust KD-tree fast path
try:
    import whitemagic_rust as _wr
    _RUST_KDTREE_AVAILABLE = True
except ImportError:
    _wr = None  # type: ignore[assignment]
    _RUST_KDTREE_AVAILABLE = False

# Optional dependencies for HDBSCAN clustering
_hdbscan: Any = None
_HDBSCAN_AVAILABLE = False
_np: Any = None
_NP_AVAILABLE = False

try:
    import hdbscan as _hdbscan
    import numpy as _np
    _HDBSCAN_AVAILABLE = True
    _NP_AVAILABLE = True
except ImportError:
    _hdbscan = None
    _np = None

# Rust acceleration
_rust_const: Any = None
_RUST_AVAILABLE = False

try:
    import whitemagic_rust as _wr
    _rust_const = getattr(_wr, "constellations", None)
    _RUST_AVAILABLE = _rust_const is not None
except ImportError:
    _rust_const = None


def distance_5d(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Euclidean distance in 5D space. Uses Rust when available."""
    if _RUST_AVAILABLE:
        try:
            return cast(float, _rust_const.py_distance_5d(
                (a[0], a[1], a[2], a[3], a[4]),
                (b[0], b[1], b[2], b[3], b[4]),
            ))
        except Exception:
            pass  # Fall back to Python
    # Zig SIMD fallback
    try:
        from whitemagic.core.acceleration.simd_holographic import (
            holographic_5d_distance,
        )
        return float(holographic_5d_distance(a, b, (1.0, 1.0, 1.0, 1.0, 1.0)))
    except Exception:
        pass
    return math.sqrt(sum((ai - bi) ** 2 for ai, bi in zip(a, b)))


def detect_hdbscan(
    coords: list[tuple[float, ...]],
    min_cluster_size: int = 5,
) -> tuple[list[list[int]], list[float]]:
    """Cluster using HDBSCAN — variable-density with noise rejection.

    Returns (groups, stabilities) where groups is a list of member-index
    lists and stabilities is per-cluster persistence score (0-1).
    """
    if not _HDBSCAN_AVAILABLE or not _NP_AVAILABLE:
        raise ImportError("HDBSCAN and numpy are required for HDBSCAN clustering")

    data = _np.array(coords, dtype=_np.float64)
    clusterer = _hdbscan.HDBSCAN(
        min_cluster_size=max(min_cluster_size, 5),
        min_samples=max(min_cluster_size // 2, 2),
        metric="euclidean",
    )
    labels = clusterer.fit_predict(data)

    # Group indices by label (-1 = noise → skip)
    label_to_indices: dict[int, list[int]] = defaultdict(list)
    for idx, label in enumerate(labels):
        if label >= 0:
            label_to_indices[label].append(idx)

    # Extract per-cluster stability from HDBSCAN's probabilities
    groups: list[list[int]] = []
    stabilities: list[float] = []
    for label in sorted(label_to_indices.keys()):
        members = label_to_indices[label]
        groups.append(members)
        if hasattr(clusterer, "probabilities_") and clusterer.probabilities_ is not None:
            avg_prob = float(_np.mean(clusterer.probabilities_[members]))
        else:
            avg_prob = 0.5
        stabilities.append(avg_prob)

    logger.info(
        f"HDBSCAN: {len(groups)} clusters, "
        f"{sum(1 for lbl in labels if lbl == -1)} noise points",
    )
    return groups, stabilities


def detect_kdtree(
    coords: list[tuple[float, ...]],
    ids: list[str] | None = None,
    min_members: int = 3,
    max_radius: float = 0.5,
) -> tuple[list[list[int]], list[float]]:
    """Fast KD-tree constellation detection via Rust PyConstellationDetector.

    Automatically uses the O(n log n) KD-tree path for 5D coordinates,
    falling back to the O(n²) brute-force path for other dimensions.

    Returns (groups, stabilities) where groups are lists of member-indices
    and stabilities are 0-1 scores based on cluster tightness.
    """
    if not _RUST_KDTREE_AVAILABLE:
        raise ImportError("whitemagic_rust required for KD-tree clustering")
    if len(coords) == 0:
        return [], []

    det = _wr.PyConstellationDetector(min_members, max_radius)
    id_list = ids or [str(i) for i in range(len(coords))]

    for i, c in enumerate(coords):
        det.add_point(id_list[i], list(c))

    constellations = det.detect_constellations()

    groups: list[list[int]] = []
    stabilities: list[float] = []
    for c in constellations:
        indices = []
        for member_id in c.members:
            try:
                indices.append(id_list.index(member_id))
            except ValueError:
                pass
        if indices:
            groups.append(indices)
            # Stability: tighter radius = higher stability
            stability = max(0.0, 1.0 - c.radius / max_radius) if max_radius > 0 else 0.5
            stabilities.append(stability)

    logger.info(f"KD-tree: {len(groups)} constellations from {len(coords)} points")
    return groups, stabilities


def detect_grid(
    coords: list[tuple[float, ...]],
    bins: int = 8,
    min_size: int = 5,
    max_constellations: int = 30,
) -> tuple[list[list[int]], list[float]]:
    """Grid-based density scan fallback.

    Returns (groups, stabilities) — stabilities are always 0.0 for grid.
    """
    # Try Rust implementation first
    if _RUST_AVAILABLE and len(coords) > 0:
        try:
            # Convert to format expected by Rust
            coords_5d = [(c[0], c[1], c[2], c[3], c[4]) for c in coords]
            groups_rust = _rust_const.py_detect_grid(
                coords_5d, bins, min_size, max_constellations
            )
            return groups_rust, [0.0] * len(groups_rust)
        except Exception:
            pass  # Fall back to Python

    # Compute axis ranges
    ranges = {}
    for i, axis in enumerate(["x", "y", "z", "w", "v"]):
        vals = [c[i] for c in coords]
        ranges[axis] = (min(vals), max(vals))

    # Assign to grid cells
    cells: dict[tuple, list[int]] = defaultdict(list)
    for idx, c in enumerate(coords):
        key = cell_key(c[0], c[1], c[2], c[3], c[4], ranges, bins)
        cells[key].append(idx)

    # Dense cells
    dense_cells = {k: v for k, v in cells.items() if len(v) >= min_size}
    if not dense_cells:
        return [], []

    # Merge adjacent
    merged = merge_adjacent(dense_cells)

    groups: list[list[int]] = []
    for cell_group in merged:
        member_indices = []
        for cell in cell_group:
            member_indices.extend(dense_cells[cell])
        groups.append(member_indices)

    return groups, [0.0] * len(groups)


def bin_value(value: float, axis_min: float, axis_max: float, bins: int) -> int:
    """Map a value to a bin index."""
    if axis_max <= axis_min:
        return 0
    normalized = (value - axis_min) / (axis_max - axis_min)
    return min(bins - 1, max(0, int(normalized * bins)))


def cell_key(
    x: float, y: float, z: float, w: float, v: float,
    ranges: dict[str, tuple[float, float]],
    bins: int = 8,
) -> tuple[int, int, int, int, int]:
    """Map a 5D point to a grid cell."""
    return (
        bin_value(x, *ranges["x"], bins),
        bin_value(y, *ranges["y"], bins),
        bin_value(z, *ranges["z"], bins),
        bin_value(w, *ranges["w"], bins),
        bin_value(v, *ranges["v"], bins),
    )


def merge_adjacent(
    dense_cells: dict[tuple, list[int]],
) -> list[list[tuple]]:
    """Merge adjacent dense cells into groups (simple flood-fill)."""
    visited: set[tuple] = set()
    groups: list[list[tuple]] = []

    for cell_key in dense_cells:
        if cell_key in visited:
            continue

        # Flood-fill from this cell
        group = []
        queue = [cell_key]
        while queue:
            current = queue.pop()
            if current in visited:
                continue
            visited.add(current)
            group.append(current)

            # Check all 5D neighbors (±1 on each axis)
            for dim in range(5):
                for delta in (-1, 1):
                    neighbor_list = list(current)
                    neighbor_list[dim] += delta
                    neighbor = tuple(neighbor_list)
                    if neighbor in dense_cells and neighbor not in visited:
                        queue.append(neighbor)

        groups.append(group)

    return groups


def detect_semantic(
    embeddings: list[list[float]],
    ids: list[str] | None = None,
    similarity_threshold: float = 0.75,
    min_members: int = 3,
) -> tuple[list[list[int]], list[float]]:
    """Cluster memories by semantic embedding similarity.

    Uses cosine similarity (dot product for pre-normalized vectors) to build
    a similarity graph, then extracts connected components as clusters.

    Args:
        embeddings: List of embedding vectors (should be normalized).
        ids: Optional memory IDs (used for logging only).
        similarity_threshold: Cosine similarity threshold for edge creation.
        min_members: Minimum cluster size to return.

    Returns:
        (groups, stabilities) where groups are lists of member-indices
        and stabilities are average intra-cluster similarity scores.
    """
    n = len(embeddings)
    if n == 0:
        return [], []

    # Build similarity graph adjacency list
    adjacency: dict[int, set[int]] = {i: set() for i in range(n)}

    if _NP_AVAILABLE and n > 1:
        data = _np.array(embeddings, dtype=_np.float32)
        # Normalize for true cosine similarity
        norms = _np.linalg.norm(data, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        data = data / norms
        # Batch compute similarity matrix (upper triangle)
        sim_matrix = data @ data.T
        # Threshold and build adjacency
        mask = sim_matrix >= similarity_threshold
        for i in range(n):
            neighbors = _np.where(mask[i])[0].tolist()
            adjacency[i] = {j for j in neighbors if j != i}
    else:
        # Pure Python fallback
        for i in range(n):
            vec_i = embeddings[i]
            norm_i = math.sqrt(sum(v * v for v in vec_i)) or 1.0
            for j in range(i + 1, n):
                vec_j = embeddings[j]
                norm_j = math.sqrt(sum(v * v for v in vec_j)) or 1.0
                dot = sum(a * b for a, b in zip(vec_i, vec_j))
                sim = dot / (norm_i * norm_j)
                if sim >= similarity_threshold:
                    adjacency[i].add(j)
                    adjacency[j].add(i)

    # Connected components (BFS)
    visited = set()
    groups: list[list[int]] = []
    stabilities: list[float] = []

    for start in range(n):
        if start in visited:
            continue
        component = []
        queue = [start]
        while queue:
            node = queue.pop()
            if node in visited:
                continue
            visited.add(node)
            component.append(node)
            for neighbor in adjacency[node]:
                if neighbor not in visited:
                    queue.append(neighbor)

        if len(component) >= min_members:
            # Compute stability as average pairwise similarity within component
            if _NP_AVAILABLE and len(component) > 1:
                idxs = _np.array(component, dtype=_np.int64)
                sub_matrix = sim_matrix[_np.ix_(idxs, idxs)]
                # Exclude diagonal
                mask_off = ~_np.eye(len(component), dtype=bool)
                avg_sim = float(sub_matrix[mask_off].mean()) if mask_off.any() else 1.0
            else:
                avg_sim = 1.0
            groups.append(component)
            stabilities.append(avg_sim)

    logger.info(
        f"Semantic: {len(groups)} clusters from {n} embeddings "
        f"(threshold={similarity_threshold})",
    )
    return groups, stabilities
