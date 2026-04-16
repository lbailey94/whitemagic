"""Acceleration modules — SIMD, FFI, and polyglot-accelerated operations.

Note: Polyglot bridges (Elixir, Go, Haskell, Julia, Mojo) are optional dependencies.
If not installed, fallback implementations raise NotImplementedError with clear error messages.
These bridges are experimental and currently not in active development.
"""

from typing import Any

try:
    from .elixir_bridge import (
        elixir_bridge_status,
        elixir_cascade_execute,
        elixir_cascade_pipeline,
        has_elixir,
    )
except ImportError:
    has_elixir = False

    def elixir_bridge_status() -> dict[str, Any]:
        return {"status": "error", "message": "Elixir bridge not available or archived."}

    def elixir_cascade_execute(
        tool_name: str,
        args: dict[str, Any],
        timeout_ms: int = 30000,
        priority: str = "normal",
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Elixir bridge not available or archived.")

    def elixir_cascade_pipeline(
        tasks: list[dict[str, Any]],
        mode: str = "parallel",
        max_failures: int = -1,
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Elixir bridge not available or archived.")

try:
    from .go_mesh_bridge import (
        go_mesh_status,
        mesh_agent_status,
        mesh_distribute_task,
        mesh_sync_memory,
    )
except ImportError:
    def go_mesh_status() -> dict[str, Any]:
        return {"status": "error", "message": "Go mesh bridge not available."}

    def mesh_agent_status() -> dict[str, Any] | None:
        raise NotImplementedError("Go mesh bridge not available.")

    def mesh_distribute_task(
        task: dict[str, Any],
        strategy: str = "least_loaded",
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Go mesh bridge not available.")

    def mesh_sync_memory(
        memory_id: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Go mesh bridge not available.")

try:
    from .haskell_bridge import (
        haskell_bridge_status,
        haskell_check_boundaries,
        haskell_evaluate_rules,
        haskell_maturity_assess,
    )
except ImportError:
    def haskell_bridge_status() -> dict[str, Any]:
        return {"status": "error", "message": "Haskell bridge not available."}

    def haskell_check_boundaries(
        tool_name: str,
        description: str = "",
        args_str: str = "",
    ) -> list[dict[str, Any]] | None:
        raise NotImplementedError("Haskell bridge not available.")

    def haskell_evaluate_rules(
        tool_name: str,
        description: str = "",
        safety_level: str = "",
        category: str = "",
        profile: str = "default",
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Haskell bridge not available.")

    def haskell_maturity_assess(
        stage: int,
        tools_executed: int,
        session_count: int,
        dharma_score: float,
        harmony_score: float,
        consolidations: int = 0,
        agents_registered: int = 0,
        error_rate: float = 0.0,
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Haskell bridge not available.")

try:
    from .julia_bridge import (
        julia_batch_forecast,
        julia_bridge_status,
        julia_forecast_metric,
        julia_importance_distribution,
    )
except ImportError:
    def julia_batch_forecast(
        metrics: dict[str, list[float]],
        steps: int = 5,
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Julia bridge not available.")

    def julia_bridge_status() -> dict[str, Any]:
        return {"status": "error", "message": "Julia bridge not available."}

    def julia_forecast_metric(
        values: list[float],
        steps: int = 5,
        alpha: float = 0.3,
        beta: float = 0.1,
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Julia bridge not available.")

    def julia_importance_distribution(
        scores: list[float],
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Julia bridge not available.")

try:
    from .mojo_bridge import (
        mojo_batch_encode,
        mojo_neuro_score,
        mojo_quantize,
        mojo_status,
    )
except ImportError:
    def mojo_batch_encode(
        memories: list[dict[str, Any]],
    ) -> list[tuple[float, float, float, float, float]] | None:
        raise NotImplementedError("Mojo bridge not available.")

    def mojo_neuro_score(
        memories: list[dict[str, Any]],
    ) -> list[dict[str, Any]] | None:
        raise NotImplementedError("Mojo bridge not available.")

    def mojo_quantize(
        vectors: list[list[float]],
        mode: str = "int8",
    ) -> dict[str, Any] | None:
        raise NotImplementedError("Mojo bridge not available.")

    def mojo_status() -> dict[str, Any]:
        return {"status": "error", "message": "Mojo bridge not available."}

from .dispatch_bridge import DispatchBridge, get_dispatch
from .event_ring_bridge import EventRingBridge, get_event_ring
from .mojo_bridge import (
    mojo_batch_encode,
    mojo_neuro_score,
    mojo_quantize,
    mojo_status,
)

# Unified SIMD bridge (replaces 6 individual modules)
from .simd_unified import (
    # Vector batch operations
    batch_centroid,
    # Cosine operations
    batch_cosine,
    batch_normalize,
    batch_topk_cosine,
    cosine_similarity,
    # Distance operations
    cosine_similarity_zig,
    # Keyword extraction
    extract_keywords,
    # Constellation operations
    grid_density_scan,
    # Holographic 5D operations
    holographic_5d_centroid,
    holographic_5d_distance,
    holographic_5d_knn,
    pairwise_distance_matrix,
    simd_constellation_status,
    simd_distance_status,
    simd_holographic_status,
    simd_keywords_status,
    # Status functions
    simd_status,
    simd_vector_batch_status,
    top_k_nearest,
)
from .state_board_bridge import StateBoardBridge, get_state_board

__all__ = [
    # SIMD operations (always available)
    "cosine_similarity", "batch_cosine", "simd_status",
    "extract_keywords", "simd_keywords_status",
    "pairwise_distance_matrix", "cosine_similarity_zig", "top_k_nearest",
    "simd_distance_status",
    "holographic_5d_distance", "holographic_5d_knn", "holographic_5d_centroid",
    "simd_holographic_status",
    "grid_density_scan", "simd_constellation_status",
    "batch_topk_cosine", "batch_normalize", "batch_centroid",
    "simd_vector_batch_status",
    # Mojo (if available)
    "mojo_batch_encode", "mojo_quantize", "mojo_neuro_score", "mojo_status",
    # Core bridges (always available)
    "StateBoardBridge", "get_state_board",
    "EventRingBridge", "get_event_ring",
    "DispatchBridge", "get_dispatch",
    # Polyglot bridges (optional - may raise NotImplementedError)
    "haskell_check_boundaries", "haskell_maturity_assess",
    "haskell_evaluate_rules", "haskell_bridge_status",
    "elixir_cascade_execute", "elixir_cascade_pipeline",
    "elixir_bridge_status",
    "mesh_sync_memory", "mesh_agent_status", "mesh_distribute_task",
    "go_mesh_status",
    "julia_importance_distribution", "julia_forecast_metric",
    "julia_batch_forecast", "julia_bridge_status",
]
