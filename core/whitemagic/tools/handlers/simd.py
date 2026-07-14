"""MCP handlers for Zig SIMD Acceleration."""

from typing import Any


def handle_simd_cosine(**kwargs: Any) -> dict[str, Any]:
    """Compute cosine similarity between two vectors using SIMD acceleration."""
    from whitemagic.core.acceleration import cosine_similarity

    a = kwargs.get("a", [])
    b = kwargs.get("b", [])
    if not a or not b:
        return {"status": "error", "error": "a and b vectors are required"}
    score = cosine_similarity(a, b)
    return {"status": "success", "similarity": round(score, 6), "dim": len(a)}


def handle_simd_batch(**kwargs: Any) -> dict[str, Any]:
    """Batch cosine similarity — compare query against multiple vectors."""
    from whitemagic.core.acceleration.simd_cosine import batch_cosine

    query = kwargs.get("query", [])
    vectors = kwargs.get("vectors", [])
    if not query or not vectors:
        return {"status": "error", "error": "query and vectors are required"}
    scores = batch_cosine(query, vectors)
    return {
        "status": "success",
        "scores": [round(s, 6) for s in scores],
        "count": len(scores),
    }


def handle_simd_status(**kwargs: Any) -> dict[str, Any]:
    """Get SIMD acceleration status — Zig library, lane width, backend."""
    from whitemagic.core.acceleration.simd_cosine import simd_status

    return {"status": "success", **simd_status()}


def handle_hexagram_simd_execute(**kwargs: Any) -> dict[str, Any]:
    """Execute 64-lane hexagram SIMD dispatch.

    Loads data into specified hexagram lanes and executes in parallel.
    Each lane applies its dispatch strategy (parallel, batch, stream, etc.).
    """
    try:
        import whitemagic_rs

        simd_fn = getattr(whitemagic_rs, "hexagram_simd_execute", None) or getattr(
            whitemagic_rs, "hexagram_simd_py_execute", None
        )
        if simd_fn is None:
            return {"status": "error", "error": "Rust hexagram_simd not available"}
        loads = kwargs.get("loads", {})
        if not loads:
            return {
                "status": "error",
                "error": "loads dict (hexagram_num → data) is required",
            }
        loads = {int(k): v for k, v in loads.items()}
        results = simd_fn(loads)
        return {"status": "success", "results": results, "lane_count": len(results)}
    except ImportError:
        return {"status": "error", "error": "whitemagic_rs not installed"}


def handle_hexagram_dispatch(**kwargs: Any) -> dict[str, Any]:
    """Get dispatch profile for a hexagram (King Wen number 1-64)."""
    try:
        import whitemagic_rs

        if not hasattr(whitemagic_rs, "hexagram_dispatch_info"):
            return {"status": "error", "error": "Rust hexagram_dispatch not available"}
        hexagram_num = kwargs.get("hexagram_num", 0)
        if hexagram_num < 1 or hexagram_num > 64:
            return {"status": "error", "error": "hexagram_num must be 1-64"}
        info = whitemagic_rs.hexagram_dispatch_info(hexagram_num)
        return {"status": "success", "hexagram": hexagram_num, "dispatch": info}
    except ImportError:
        return {"status": "error", "error": "whitemagic_rs not installed"}


def handle_hexagram_boltzmann_select(**kwargs: Any) -> dict[str, Any]:
    """Select a hexagram using Boltzmann distribution with temperature."""
    try:
        import whitemagic_rs

        if not hasattr(whitemagic_rs, "hexagram_boltzmann_select"):
            return {"status": "error", "error": "Rust boltzmann not available"}
        temperature = kwargs.get("temperature", 1.0)
        num = whitemagic_rs.hexagram_boltzmann_select(temperature)
        return {"status": "success", "hexagram": num, "temperature": temperature}
    except ImportError:
        return {"status": "error", "error": "whitemagic_rs not installed"}


def handle_hexagram_interaction_score(**kwargs: Any) -> dict[str, Any]:
    """Compute HRR cosine similarity between two hexagrams (King Wen 1-64)."""
    kw1 = kwargs.get("hexagram_a", kwargs.get("kw1", 0))
    kw2 = kwargs.get("hexagram_b", kwargs.get("kw2", 0))
    if not (1 <= kw1 <= 64) or not (1 <= kw2 <= 64):
        return {"status": "error", "error": "hexagram_a and hexagram_b must be 1-64"}
    from whitemagic.core.intelligence.hexagram_vectors import get_hexagram_vectors

    hv = get_hexagram_vectors()
    score = hv.interaction_score(kw1, kw2)
    return {
        "status": "success",
        "hexagram_a": kw1,
        "hexagram_b": kw2,
        "similarity": round(score, 6),
    }


def handle_hexagram_synergies(**kwargs: Any) -> dict[str, Any]:
    """Find synergistic hexagram pairs by HRR similarity.

    Args:
        threshold: Minimum cosine similarity (default 0.3)
        top_k: Return top K pairs instead of threshold-based (optional)
    """
    from whitemagic.core.intelligence.hexagram_vectors import get_hexagram_vectors

    hv = get_hexagram_vectors()
    top_k = kwargs.get("top_k")
    if top_k is not None:
        pairs = hv.top_synergies(int(top_k))
    else:
        threshold = kwargs.get("threshold", 0.3)
        pairs = hv.detect_synergies(float(threshold))
    return {
        "status": "success",
        "pairs": pairs,
        "count": len(pairs),
    }


def handle_hexagram_superpose(**kwargs: Any) -> dict[str, Any]:
    """Superpose two hexagram HRR vectors (combine influences).

    Args:
        hexagram_a, hexagram_b: King Wen numbers (1-64)
    """
    kw1 = kwargs.get("hexagram_a", kwargs.get("kw1", 0))
    kw2 = kwargs.get("hexagram_b", kwargs.get("kw2", 0))
    if not (1 <= kw1 <= 64) or not (1 <= kw2 <= 64):
        return {"status": "error", "error": "hexagram_a and hexagram_b must be 1-64"}
    from whitemagic.core.intelligence.hexagram_vectors import get_hexagram_vectors

    hv = get_hexagram_vectors()
    vector = hv.superpose(kw1, kw2)
    return {
        "status": "success",
        "hexagram_a": kw1,
        "hexagram_b": kw2,
        "vector": vector,
        "dimension": len(vector),
    }


def handle_hexagram_vector(**kwargs: Any) -> dict[str, Any]:
    """Get the HRR vector for a single hexagram (King Wen 1-64)."""
    kw = kwargs.get("hexagram_num", kwargs.get("king_wen", 0))
    if not (1 <= kw <= 64):
        return {"status": "error", "error": "hexagram_num must be 1-64"}
    from whitemagic.core.intelligence.hexagram_vectors import get_hexagram_vectors

    hv = get_hexagram_vectors()
    vector = hv.get_vector(kw)
    return {
        "status": "success",
        "hexagram": kw,
        "vector": vector,
        "dimension": len(vector),
    }


def handle_hexagram_nearest(**kwargs: Any) -> dict[str, Any]:
    """Find nearest hexagrams to a given vector in HRR space.

    Args:
        vector: A float vector (any dimensionality, padded/truncated to 64)
        top_k: Number of nearest hexagrams (default 5)
    """
    vector = kwargs.get("vector", [])
    if not vector:
        return {"status": "error", "error": "vector is required"}
    top_k = kwargs.get("top_k", 5)
    from whitemagic.core.intelligence.hexagram_vectors import get_hexagram_vectors

    hv = get_hexagram_vectors()
    nearest = hv.nearest_hexagrams(vector, k=int(top_k))
    return {
        "status": "success",
        "nearest": nearest,
        "count": len(nearest),
    }
