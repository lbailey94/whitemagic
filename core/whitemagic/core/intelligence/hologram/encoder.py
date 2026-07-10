# ruff: noqa: BLE001
"""Holographic Coordinate Encoder v2.0.
===================================

Converts Memory objects into 6D coordinate vectors [x, y, z, w, v, u].

Axis Definitions:
-----------------
X-Axis (Logic <-> Emotion):
    -1.0: Pure Emotion (High joy/fear/anger, low strategic confidence)
     0.0: Balanced / Neutral
    +1.0: Pure Logic (High strategic confidence, low emotional intensity)

Y-Axis (Micro <-> Macro):
    -1.0: Micro / Concrete (Logs, raw data, specific events)
     0.0: Mid-level (Summaries, chapters)
    +1.0: Macro / Abstract (Patterns, principles, wisdom, archetypes)

Z-Axis (Time / Chronos):
    -1.0: Ancient History (Deep archive)
     0.0: Present Moment
    +1.0: Future Vision (Plans, prophecies)

W-Axis (Importance / Gravity):
    0.0: Trivial (Noise)
    1.0: Critical (Signal)
    >1.0: High Gravity (Black Hole / Attractor) - Driven by Joy/Resonance.

V-Axis (Vitality / Galactic Distance):
    1.0: Core (Active spotlight, high retention, frequently accessed)
    0.5: Mid-Band (Moderate relevance)
    0.0: Far Edge (Deep archive, low retention, rarely accessed)
    Derived from galactic_distance: v = 1.0 - galactic_distance

U-Axis (Galaxy Affinity):
    0.0: FAR_EDGE (telemetry, archive — noise, cold storage)
    0.3: OUTER_RIM (substrate, tutorial, universal — infrastructure)
    0.5: MID_BAND (research, journals, dreams — exploration)
    0.7: INNER_RIM (sessions, codex, knowledge — active knowledge)
    1.0: CORE (aria, citta, meta — identity, consciousness, index)
    Derived from the canonical GALAXY_ZONES mapping.

v2.1 Changes:
- Added U-Axis (Galaxy Affinity) based on canonical galaxy zones
- Improved keyword matching for all axes
- Fixed memory_type field name
- Better time calculation using actual timestamps
- Content hash for deterministic spread
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

logger = logging.getLogger(__name__)

# Rust acceleration (S026 VC6)
try:
    import whitemagic_rust as _wr

    _rust_holographic: Any = getattr(_wr, "holographic_encoder_5d", None)
    RUST_HOLOGRAPHIC_AVAILABLE = _rust_holographic is not None
except ImportError:
    _rust_holographic = None
    RUST_HOLOGRAPHIC_AVAILABLE = False
    logger.debug("Rust holographic_encoder_5d not available, using Python fallback")


@dataclass
class HolographicCoordinate:
    """HolographicCoordinate: holographic coordinate.

    Value object: equality and repr are field-based."""

    x: float  # Logic <-> Emotion
    y: float  # Micro <-> Macro
    z: float  # Time
    w: float  # Importance/Gravity
    v: float = 0.5  # Vitality/Galactic Distance (1.0=core, 0.0=edge)
    u: float = 0.5  # Galaxy Affinity (1.0=core zone, 0.0=far edge zone)

    def to_vector(self) -> list[float]:
        """
        Convert to/from vector.

        Returns:
            list[float]
        """
        return [self.x, self.y, self.z, self.w, self.v, self.u]

    def to_vector_4d(self) -> list[float]:
        """Legacy 4D vector for backward compatibility."""
        return [self.x, self.y, self.z, self.w]

    def to_vector_5d(self) -> list[float]:
        """5D vector (without U-axis) for backward compatibility."""
        return [self.x, self.y, self.z, self.w, self.v]

    def to_dict(self) -> dict[str, float]:
        """
        Convert to/from dict.

        Returns:
            dict[str, float]
        """
        return {"x": self.x, "y": self.y, "z": self.z, "w": self.w, "v": self.v, "u": self.u}


class CoordinateEncoder:
    """Encodes memories into holographic coordinates (v2.0)."""

    ANCHOR_LOGIC_ID = "3c9afb8e-bca0-4ef1-bc1d-64dd5595b93f"
    ANCHOR_EMOTION_ID = "33c01076f2580558"
    # Macro/Reflection vs Micro/Benchmark
    ANCHOR_MICRO_ID = "34d35ecd387033af270bdcbd973dd0fc"
    ANCHOR_MACRO_ID = "1d2d36b19b9b0757"

    def __init__(self) -> None:
        self._cache: dict[str, HolographicCoordinate] = {}
        self._garden_bias_enabled = True
        self._embedding_engine: Any | None = None
        self._anchor_embeddings: dict[str, Any] = {}  # Now stores list[float]
        self._mean_vector: list[float] | None = None
        self._pca_components: dict[str, list[float]] | None = None
        self._load_mean_vector()
        self._load_pca_components()

    def _load_mean_vector(self) -> None:
        """Load the semantic mean vector for centering embeddings."""
        import json
        import os
        from pathlib import Path

        # Use project-relative path
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        path = project_root / "data/semantic_mean_vector.json"
        # Fallback to archives if not found
        if not path.exists():
            path = Path(
                "/media/lucas/SD_CARD/WHITEMAGIC/archives/whitemagic-clean-BACKUP-20250407/core_system/data/semantic_mean_vector.json"
            )
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self._mean_vector = json.load(f)
            except Exception as _e:
                logger.debug("Non-fatal error silenced in holographic encoder: %s", _e)

    def _load_pca_components(self) -> None:
        """Load the PCA components for direct axis projection."""
        import json
        import os
        from pathlib import Path

        # Use project-relative path
        project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
        path = project_root / "data/semantic_pca_components.json"
        # Fallback to archives if not found
        if not path.exists():
            path = Path(
                "/media/lucas/SD_CARD/WHITEMAGIC/archives/whitemagic-clean-BACKUP-20250407/core_system/data/semantic_pca_components.json"
            )
        if os.path.exists(path):
            try:
                with open(path) as f:
                    self._pca_components = json.load(f)
            except Exception as _e:
                logger.debug("Non-fatal error silenced in holographic encoder: %s", _e)

    def _center_vector(self, vec: list[float] | Any) -> Any:
        """Subtract the mean vector from the given vector to amplify directional signal."""
        if self._mean_vector is None or vec is None:
            return vec
        # Pure Python implementation to avoid numpy dependency on VPS
        if len(vec) == len(self._mean_vector):
            return [v - m for v, m in zip(vec, self._mean_vector)]
        return vec

    def _get_embedding_engine(self) -> Any:
        """Lazy-load the embedding engine."""
        if self._embedding_engine is None:
            try:
                from whitemagic.core.memory.embeddings import get_embedding_engine

                self._embedding_engine = get_embedding_engine()
            except ImportError:
                logger.debug(
                    "Optional encoder dependency not available; using fallback"
                )
        return self._embedding_engine

    def _get_anchor_embedding(self, name: str, anchor_id: str) -> Any | None:
        """Get the cached and centered embedding for a semantic anchor ID."""
        if name in self._anchor_embeddings:
            return self._anchor_embeddings[name]

        engine = self._get_embedding_engine()
        if engine:
            vec = engine.get_cached_embedding(anchor_id)
            if vec:
                centered = self._center_vector(vec)
                self._anchor_embeddings[name] = centered
                return centered
        return None

    def _calculate_semantic_bias(self, memory: dict[str, Any], axis: str) -> float:
        """Calculate semantic bias for an axis (x or y) using PCA projection or vector projection.
        PCA projection is preferred as it captures the maximum variance of the dataset.
        """
        engine = self._get_embedding_engine()
        if not engine or not engine.available(include_cache=True):
            return 0.0

        mem_id = memory.get("id")
        if not mem_id:
            return 0.0

        mem_vec = engine.get_cached_embedding(mem_id)
        if not mem_vec:
            return 0.0

        import math

        # Center the memory vector
        v = self._center_vector(mem_vec)

        def dot_product(v1: list[float], v2: list[float]) -> float:
            """
            Perform the dot product operation.

            Args:
                v1: Parameter description.
                v2: Parameter description.
            """
            return sum(x * y for x, y in zip(v1, v2))

        def vec_norm(v1: list[float]) -> float:
            """
            Perform the vec norm operation.

            Args:
                v1: Parameter description.
            """
            return math.sqrt(sum(x * x for x in v1))

        def vec_sub(v1: list[float], v2: list[float]) -> list[float]:
            """
            Perform the vec sub operation.

            Args:
                v1: Parameter description.
                v2: Parameter description.
            """
            return [x - y for x, y in zip(v1, v2)]

        if self._pca_components:
            pc_vec = self._pca_components.get(f"{axis}_axis")
            if pc_vec:
                # Direct projection onto the principal component
                score = dot_product(v, pc_vec)
                # Amplified scaling to ensure coordinates occupy the full [-1, 1] range
                # After centering, MiniLM PCA scores are typically in [-0.15, 0.15]
                return float(max(-1.0, min(1.0, score * 6.0)))

        if axis == "x":
            # Axis: Logic (+) <---> Emotion (-)
            p1 = self._get_anchor_embedding("logic", self.ANCHOR_LOGIC_ID)
            p2 = self._get_anchor_embedding("emotion", self.ANCHOR_EMOTION_ID)

            if p1 is not None and p2 is not None:
                # Axis vector from p2 to p1
                axis_vec = vec_sub(p1, p2)
                axis_norm = vec_norm(axis_vec)
                if axis_norm < 1e-6:
                    return 0.0

                # Project (v - p2) onto axis_vec
                # Result is in range [0, 1] if v is between p2 and p1
                v_minus_p2 = vec_sub(v, p2)
                projection = dot_product(v_minus_p2, axis_vec) / (axis_norm**2)

                # Map [0, 1] to [-1, 1]
                score = (projection * 2.0) - 1.0
                # Amplify the center to push toward edges if needed
                return float(max(-1.0, min(1.0, score * 1.5)))

        elif axis == "y":
            # Axis: Macro (+) <---> Micro (-)
            p1 = self._get_anchor_embedding("macro", self.ANCHOR_MACRO_ID)
            p2 = self._get_anchor_embedding("micro", self.ANCHOR_MICRO_ID)

            if p1 is not None and p2 is not None:
                axis_vec = vec_sub(p1, p2)
                axis_norm = vec_norm(axis_vec)
                if axis_norm < 1e-6:
                    return 0.0

                v_minus_p2 = vec_sub(v, p2)
                projection = dot_product(v_minus_p2, axis_vec) / (axis_norm**2)
                score = (projection * 2.0) - 1.0
                return float(max(-1.0, min(1.0, score * 1.5)))

        return 0.0

    GANA_MAP = {
        "degree": "Business Administration",
        "graduated": "Diplomat",
        "studies": "Curriculum",
        "major": "Specialization",
        "project": "Repository",
        "loyal": "Fidelity",
        "career": "Profession",
        "research": "Investigation",
    }

    def _apply_gana_alignment(
        self, text: str, x: float, y: float
    ) -> tuple[float, float]:
        """Align coordinates to semantic poles based on keyword detection.
        Re-aligned to 0.5 baseline for DB compatibility.
        """
        text = text.lower()
        for key, val in self.GANA_MAP.items():
            if key in text or val.lower() in text:
                # Align to the "GANA Pole" (Macroscopic Logic)
                # Reverted to 0.5 weight to match original ingestion baseline.
                x = (x * 0.5) + (1.0 * 0.5)
                y = (y * 0.5) + (0.5 * 0.5)  # Shift toward GANA Pole
        return x, y

    def encode(self, memory: dict[str, Any]) -> HolographicCoordinate:
        """Encode a memory dictionary into a HolographicCoordinate."""
        import time

        # 1. Base calculations (always do these for fallback/verification)
        x = self._calculate_x(memory)
        y = self._calculate_y(memory)
        z = self._calculate_z(memory)
        w = self._calculate_w(memory)
        v = self._calculate_v(memory)
        u = self._calculate_u(memory)

        # 2. Try Rust v13.1 accelerated encoding (fastest path)
        # to ensure the high-variance signal is preserved even on stale binaries.
        try:
            from whitemagic.optimization.rust_accelerators import (
                holographic_encode_single,
                rust_v131_available,
            )

            if rust_v131_available():
                result = holographic_encode_single(memory)
                if result:
                    # Blend Rust base with Python semantic bias (0.8 weight for semantics)
                    x_rust = result.get("x", 0.0)
                    y_rust = result.get("y", 0.0)

                    # Apply semantic bias (X/Y) to the Rust result
                    bias_x = self._calculate_semantic_bias(memory, "x")
                    bias_y = self._calculate_semantic_bias(memory, "y")

                    x = (x_rust * 0.2) + (bias_x * 0.8)
                    y = (y_rust * 0.2) + (bias_y * 0.8)
                    z = result.get("z", z)
                    w = result.get("w", w)
                    v = result.get("v", v)

                    return HolographicCoordinate(x, y, z, w, v, u)
        except Exception as _e:
            logger.debug("Non-fatal error silenced in holographic encoder: %s", _e)

        # 3. Try polyglot routing for Mojo/Zig acceleration
        # Avoid circular imports by checking if we are already in a fallback
        if getattr(self, "_routing_active", False):
            # Already in target calculation, don't route again
            pass
        else:
            try:
                from whitemagic.optimization.polyglot_router import get_router

                router = get_router()
                current_time = int(time.time())

                # Set flag to prevent recursion
                self._routing_active = True
                mojo_coords = router.encode_holographic(memory, current_time)
                self._routing_active = False

                if mojo_coords:
                    return HolographicCoordinate(
                        mojo_coords.get("x", x),
                        mojo_coords.get("y", y),
                        mojo_coords.get("z", z),
                        mojo_coords.get("w", w),
                        mojo_coords.get("v", v),
                        u,
                    )
            except Exception as e:
                logger.debug(
                    "Mojo router failed, falling back to Python math: %s",
                    e,
                    exc_info=True,
                )
                self._routing_active = False
                # Fall through to Python math

        # Legacy fallback if router fails completely
        x = self._calculate_x(memory)
        y = self._calculate_y(memory)
        z = self._calculate_z(memory)
        w = self._calculate_w(memory)
        v = self._calculate_v(memory)

        # Apply garden bias if present
        if self._garden_bias_enabled:
            garden_bias = self._get_garden_bias(memory)
            if garden_bias:
                x, y, z, w, v = self._blend_with_garden(x, y, z, w, garden_bias, v=v)

        x, y = self._apply_gana_alignment(memory, x, y)  # type: ignore[arg-type]

        return HolographicCoordinate(x, y, z, w, v, u)

    def encode_batch(
        self, memories: list[dict[str, Any]]
    ) -> list[HolographicCoordinate]:
        """Batch-encode memories into holographic coordinates.

        Uses Rust Rayon parallelism when available, falls back to
        sequential Python encoding.
        """
        if RUST_HOLOGRAPHIC_AVAILABLE and len(memories) > 1:
            try:
                import json

                # Prepare memories for Rust (simplified format)
                rust_memories = []
                for m in memories:
                    rust_memories.append(
                        {
                            "id": m.get("id", ""),
                            "content": str(m.get("content", "")),
                            "importance": float(m.get("importance") or 0.5),
                            "access_count": int(m.get("access_count") or 0),
                            "age_days": self._get_age_days(m),
                            "galactic_distance": float(
                                m.get("galactic_distance") or 0.5
                            ),
                            "garden": m.get("metadata", {}).get("garden", "")
                            if isinstance(m.get("metadata"), dict)
                            else "",
                            "tags": list(m.get("tags", []))
                            if isinstance(m.get("tags"), (list, set))
                            else [],
                        }
                    )

                result_json = _rust_holographic.holographic_encode_batch(
                    json.dumps(rust_memories)
                )
                results = json.loads(result_json)

                return [
                    HolographicCoordinate(
                        r.get("x", 0.0),
                        r.get("y", 0.0),
                        r.get("z", 0.0),
                        r.get("w", 0.5),
                        r.get("v", 0.5),
                        self._calculate_u(m),
                    )
                    for r, m in zip(results, memories)
                ]
            except Exception as e:
                logger.warning(
                    "Rust batch encoding failed: %s, falling back to Python",
                    e,
                    exc_info=True,
                )

        # Python fallback: encode one at a time
        return [self.encode(m) for m in memories]

    def _get_age_days(self, memory: dict[str, Any]) -> float:
        """Calculate age in days from timestamp."""
        timestamp_str = memory.get("created_at") or memory.get("timestamp")
        if timestamp_str:
            try:
                if isinstance(timestamp_str, str):
                    for fmt in [
                        "%Y-%m-%dT%H:%M:%S.%f",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d",
                    ]:
                        try:
                            ts = datetime.strptime(timestamp_str[:26], fmt)
                            return (datetime.now() - ts).days
                        except ValueError:
                            continue
            except Exception as _e:
                logger.debug("Non-fatal error silenced in holographic encoder: %s", _e)
        return 0.0

    def _get_garden_bias(self, memory: dict[str, Any]) -> dict[str, float] | None:
        """Extract garden bias from memory if garden affiliation exists."""
        metadata = memory.get("metadata", {})
        if "coordinate_bias" in metadata:
            return cast(dict[str, float], metadata["coordinate_bias"])

        garden_name = metadata.get("garden")
        if not garden_name:
            tags = memory.get("tags", [])
            garden_tags = [
                t
                for t in tags
                if t
                in [
                    "joy",
                    "wisdom",
                    "beauty",
                    "truth",
                    "love",
                    "mystery",
                    "play",
                    "wonder",
                    "connection",
                    "courage",
                    "gratitude",
                    "patience",
                    "grief",
                    "awe",
                    "humor",
                    "healing",
                    "creation",
                    "transformation",
                    "sanctuary",
                    "adventure",
                    "reverence",
                    "stillness",
                    "protection",
                    "presence",
                    "voice",
                    "dharma",
                    "sangha",
                    "practice",
                    "browser",
                ]
            ]
            if garden_tags:
                garden_name = garden_tags[0]

        if garden_name:
            try:
                from whitemagic.gardens.base_garden import get_garden_bias

                bias = get_garden_bias(garden_name)
                if bias:
                    return cast(dict[str, float], bias.to_dict())
            except ImportError:
                logger.debug(
                    "Optional encoder dependency not available; using fallback"
                )
        return None

    def _blend_with_garden(
        self,
        x: float,
        y: float,
        z: float,
        w: float,
        bias: dict[str, float],
        ratio: float = 0.3,
        v: float = 0.5,
    ) -> tuple:
        """Blend base coordinates with garden bias."""
        blended_x = x * (1 - ratio) + bias.get("x", 0.0) * ratio
        blended_y = y * (1 - ratio) + bias.get("y", 0.0) * ratio
        blended_z = z * (1 - ratio) + bias.get("z", 0.0) * ratio
        blended_w = w * (1 + bias.get("w", 0.0))
        blended_v = v * (1 - ratio) + bias.get("v", v) * ratio

        blended_x = max(-1.0, min(1.0, blended_x))
        blended_y = max(-1.0, min(1.0, blended_y))
        blended_z = max(-1.0, min(1.0, blended_z))
        blended_v = max(0.0, min(1.0, blended_v))

        return (blended_x, blended_y, blended_z, blended_w, blended_v)

    def _content_hash_bias(self, memory: dict[str, Any], axis: str) -> float:
        """Generate deterministic spread based on content hash."""
        content = str(memory.get("content", "")) + str(memory.get("title", ""))
        mem_id = memory.get("id", "")
        hash_input = f"{content}{mem_id}{axis}"
        hash_val = int(hashlib.md5(hash_input.encode()).hexdigest()[:8], 16)
        return ((hash_val % 1000) / 1000.0 - 0.5) * 0.4

    def _calculate_x(self, memory: dict[str, Any]) -> float:
        """Calculate X-Axis: Logic vs Emotion.
        Range: [-1.0, 1.0].
        """
        valence = memory.get("emotional_valence")
        if valence is None:
            valence = 0.0
        score = -0.5 * valence

        # Logic keywords (toward +1.0)
        logic_tags = {
            "logic",
            "strategy",
            "code",
            "architecture",
            "plan",
            "analysis",
            "audit",
            "technical",
            "system",
            "algorithm",
            "debug",
            "fix",
            "implementation",
            "refactor",
            "migration",
            "database",
            "api",
            "sql",
            "rust",
            "python",
            "cli",
            "schema",
            "backend",
        }

        # Emotion keywords (toward -1.0)
        emotion_tags = {
            "joy",
            "fear",
            "anger",
            "love",
            "gratitude",
            "meditation",
            "dream",
            "feeling",
            "emotion",
            "heart",
            "soul",
            "spirit",
            "intuition",
            "wonder",
            "awe",
            "beauty",
            "sacred",
            "dharma",
        }

        tags = set(t.lower() for t in memory.get("tags", []))
        logic_count = len(tags.intersection(logic_tags))
        emotion_count = len(tags.intersection(emotion_tags))

        if logic_count > emotion_count:
            score += 0.4 + (0.1 * min(logic_count, 5))
        elif emotion_count > logic_count:
            score -= 0.4 + (0.1 * min(emotion_count, 5))

        # Content keyword analysis
        content = str(memory.get("content", "")).lower()
        title = str(memory.get("title", "")).lower()
        combined = content + " " + title

        logic_keywords = [
            "code",
            "function",
            "class",
            "import",
            "error",
            "bug",
            "fix",
            "algorithm",
            "database",
            "sql",
            "api",
            "commit",
            "git",
            "version",
            "module",
            "test",
            "debug",
            "config",
            "schema",
            "migrate",
            "refactor",
            "implement",
            "build",
            "deploy",
        ]
        emotion_keywords = [
            "feel",
            "heart",
            "love",
            "joy",
            "wonder",
            "beauty",
            "soul",
            "intuition",
            "sacred",
            "meditation",
            "dream",
            "gratitude",
            "peace",
            "calm",
            "insight",
            "wisdom",
            "dharma",
            "spirit",
        ]

        logic_word_count = sum(1 for kw in logic_keywords if kw in combined)
        emotion_word_count = sum(1 for kw in emotion_keywords if kw in combined)

        score += 0.03 * logic_word_count
        score -= 0.03 * emotion_word_count

        score += self._content_hash_bias(memory, "x")

        semantic_bias = self._calculate_semantic_bias(memory, "x")
        score = (score * 0.2) + (semantic_bias * 0.8)

        return max(-1.0, min(1.0, score))

    def _calculate_y(self, memory: dict[str, Any]) -> float:
        """Calculate Y-Axis: Micro vs Macro.
        Range: [-1.0, 1.0].
        """
        score = 0.0

        raw_type = memory.get("memory_type")
        if raw_type is None:
            raw_type = memory.get("type", "unknown")

        mem_type = str(raw_type).lower() if raw_type else "unknown"

        # Micro types (toward -1.0)
        if mem_type in ["log", "transcript", "raw", "debug", "short_term"]:
            score = -0.6
        # Macro types (toward +1.0)
        elif mem_type in ["pattern", "principle", "wisdom", "insight", "long_term"]:
            score = 0.6
        # Mid-level types
        elif mem_type in ["summary", "report", "episodic"]:
            score = 0.2

        # Micro tags
        micro_tags = {"detail", "specific", "log", "debug", "error", "line", "file"}
        # Macro tags
        macro_tags = {
            "pattern",
            "principle",
            "wisdom",
            "insight",
            "overview",
            "architecture",
            "design",
            "philosophy",
            "strategy",
            "era",
        }

        tags = set(t.lower() for t in memory.get("tags", []))
        micro_count = len(tags.intersection(micro_tags))
        macro_count = len(tags.intersection(macro_tags))

        score -= 0.15 * micro_count
        score += 0.15 * macro_count

        # Content analysis
        content = str(memory.get("content", "")).lower()

        # Macro indicators
        if any(
            w in content
            for w in [
                "universal",
                "always",
                "principle",
                "pattern",
                "architecture",
                "overview",
                "era",
                "phase",
            ]
        ):
            score += 0.15
        # Micro indicators
        if any(
            w in content
            for w in [
                "specific",
                "line",
                "error",
                "bug",
                "file:",
                "at line",
                "traceback",
            ]
        ):
            score -= 0.15

        # Hash variation
        score += self._content_hash_bias(memory, "y")

        semantic_bias = self._calculate_semantic_bias(memory, "y")
        score = (score * 0.2) + (semantic_bias * 0.8)

        return max(-1.0, min(1.0, score))

    def _calculate_z(self, memory: dict[str, Any]) -> float:
        """Calculate Z-Axis: Time / Chronos.
        Range: [-1.0, 1.0].
        """
        score = 0.0

        timestamp_str = memory.get("created_at") or memory.get("timestamp")
        if timestamp_str:
            try:
                if isinstance(timestamp_str, str):
                    for fmt in [
                        "%Y-%m-%dT%H:%M:%S.%f",
                        "%Y-%m-%dT%H:%M:%S",
                        "%Y-%m-%d %H:%M:%S",
                        "%Y-%m-%d",
                    ]:
                        try:
                            ts = datetime.strptime(timestamp_str[:26], fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        ts = datetime.now()
                else:
                    ts = datetime.now()

                # Calculate relative age (days from now)
                age_days = (datetime.now() - ts).days

                # Map age to Z: recent = 0, old = -1
                if age_days < 1:
                    score = 0.0  # Today
                elif age_days < 7:
                    score = -0.2  # This week
                elif age_days < 30:
                    score = -0.4  # This month
                elif age_days < 90:
                    score = -0.6  # This quarter
                else:
                    score = -0.8  # Older
            except Exception as _e:
                logger.debug("Non-fatal error silenced in holographic encoder: %s", _e)

        # Future-oriented tags push toward +1.0
        tags = set(t.lower() for t in memory.get("tags", []))
        if tags.intersection({"future", "plan", "vision", "roadmap", "goal", "next"}):
            score += 0.5
        if tags.intersection({"history", "archive", "legacy", "old", "past"}):
            score -= 0.3

        # Content hints
        content = str(memory.get("content", "")).lower()
        if any(
            w in content for w in ["will ", "plan to", "next step", "future", "goal"]
        ):
            score += 0.2
        if any(w in content for w in ["was ", "used to", "previously", "legacy"]):
            score -= 0.2

        # Hash variation
        score += self._content_hash_bias(memory, "z") * 0.5

        return max(-1.0, min(1.0, score))

    def _calculate_w(self, memory: dict[str, Any]) -> float:
        """Calculate W-Axis: Importance / Gravity.
        Range: [0.0, 2.0+].
        """
        # Base importance (v5.0 integration: uses importance OR neuro_score)
        importance = float(memory.get("importance") or 0.5)
        neuro_score = float(memory.get("neuro_score") or 1.0)

        # Gravity is a combination of importance and neural strength
        base = (importance * 0.4) + (neuro_score * 0.6)

        # Usage Patterns (v15.1 Enhancement)
        access_count = int(memory.get("access_count") or 0)
        recall_count = int(memory.get("recall_count") or 0)
        usage_boost = min(0.5, (access_count + recall_count * 2) / 20.0)
        base += usage_boost

        # Reference Density (v15.1 Enhancement)
        links = memory.get("links", {})
        link_count = len(links) if isinstance(links, dict) else 0
        assoc_count = len(memory.get("associations", {}))
        density_boost = min(0.3, (link_count + assoc_count) * 0.05)
        base += density_boost

        # Memory type boost
        raw_type = memory.get("memory_type")
        if raw_type is None:
            raw_type = memory.get("type", "")
        mem_type = str(raw_type).lower() if raw_type else ""
        if mem_type == "long_term":
            base += 0.3
        elif mem_type == "pattern":
            base += 0.4  # Discovered patterns have high gravity
        elif mem_type == "short_term":
            base -= 0.1

        # High-importance tags
        important_tags = {
            "critical",
            "important",
            "key",
            "core",
            "essential",
            "milestone",
            "breakthrough",
            "wisdom",
            "principle",
        }
        tags = set(t.lower() for t in memory.get("tags", []))

        base += 0.1 * len(tags.intersection(important_tags))

        # Joy/resonance scores
        joy_score = float(memory.get("joy_score", 0.0) or 0.0)
        resonance_score = float(memory.get("resonance_score", 0.0) or 0.0)

        w = base + (joy_score * 0.5) + (resonance_score * 0.5)

        # Content length as minor importance signal
        content_len = len(str(memory.get("content", "")))
        if content_len > 1000:
            w += 0.1
        elif content_len > 500:
            w += 0.05

        return float(max(0.1, w))  # Minimum 0.1 to ensure visibility

    def _calculate_v(self, memory: dict[str, Any]) -> float:
        """Calculate V-Axis: Vitality / Galactic Distance.
        Range: [0.0, 1.0]
        1.0 = Core (active spotlight, high retention)
        0.0 = Far Edge (deep archive, low retention).
        """
        # Protected = always at core
        if (
            memory.get("is_protected")
            or memory.get("is_core_identity")
            or memory.get("is_sacred")
        ):
            return 1.0

        # Base from galactic distance if available
        galactic_distance = memory.get("galactic_distance")
        v_base = 0.5
        if isinstance(galactic_distance, (int, float)) and galactic_distance > 0.0:
            v_base = 1.0 - float(galactic_distance)
        else:
            # Fallback to neuro_score
            v_base = float(memory.get("neuro_score") or 0.5)

        # Dynamic Lifecycle (v15.1 Enhancement)
        # Time since last access (decay toward edge)
        last_recalled = memory.get("last_recalled") or memory.get("accessed_at")
        days_since = 0.0
        if last_recalled:
            try:
                from whitemagic.utils.core import parse_datetime

                if isinstance(last_recalled, str):
                    dt = parse_datetime(last_recalled)
                else:
                    dt = last_recalled
                days_since = (datetime.now() - dt).total_seconds() / 86400.0
            except Exception as _e:
                logger.debug("Non-fatal error silenced in holographic encoder: %s", _e)

        # Decay vitality based on time (half-life of 14 days for vitality)
        decay = 0.5 ** (days_since / 14.0)
        v = v_base * decay

        # Rescue Logic: Recent activity boosts vitality back toward core
        access_count = int(memory.get("access_count") or 0)
        recall_count = int(memory.get("recall_count") or 0)
        activity_bonus = min(0.3, (access_count + recall_count) * 0.05)
        v += activity_bonus

        # Consolidation Bonus
        if memory.get("metadata", {}).get("consolidated"):
            v += 0.1

        return float(max(0.0, min(1.0, v)))

    def _calculate_u(self, memory: dict[str, Any]) -> float:
        """Calculate U-Axis: Galaxy Affinity.
        Range: [0.0, 1.0]
        1.0 = CORE zone (aria, citta, meta — identity, consciousness, index)
        0.7 = INNER_RIM (sessions, codex, knowledge — active knowledge)
        0.5 = MID_BAND (research, journals, dreams — exploration)
        0.3 = OUTER_RIM (substrate, tutorial, universal — infrastructure)
        0.0 = FAR_EDGE (telemetry, archive — noise, cold storage)
        """
        galaxy = memory.get("galaxy", "")
        if not galaxy:
            # Try to infer from metadata
            meta = memory.get("metadata", {})
            if isinstance(meta, dict):
                galaxy = meta.get("galaxy", "")

        if not galaxy:
            return 0.5  # Unknown galaxy defaults to mid-range

        try:
            from whitemagic.core.memory.galaxy_taxonomy import GALAXY_ZONES

            zone = GALAXY_ZONES.get(galaxy, "OUTER_RIM")
            zone_values = {
                "CORE": 1.0,
                "INNER_RIM": 0.7,
                "MID_BAND": 0.5,
                "OUTER_RIM": 0.3,
                "FAR_EDGE": 0.0,
            }
            return zone_values.get(zone, 0.5)
        except Exception:
            return 0.5


# Integration helper
def encode_memory(memory_obj: Any) -> Any:
    """
    Perform the encode memory operation.

    Args:
        memory_obj: Parameter description.

    Returns:
        Any
    """
    encoder = CoordinateEncoder()
    return encoder.encode(memory_obj)
