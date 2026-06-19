# ruff: noqa: BLE001, E402
"""Dream Artifacts — YAML-structured imagination capture.

When the Bicameral Reasoner emits a low-confidence creative bridge,
this module writes a human-readable YAML artifact to the dreams directory.
Artifacts can be revisited, promoted to memories, or expired.

Usage:
    from whitemagic.core.dreaming.dream_artifacts import (
        DreamArtifact, DreamArtifactWriter,
        list_dreams, read_dream, promote_dream, expire_dream,
    )
    writer = DreamArtifactWriter()
    writer.start_listening()  # registers on Gan Ying bus
"""

from __future__ import annotations

import logging
import re
import threading
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Safe YAML — no code execution
import yaml


@dataclass
class DreamArtifact:
    """A single dream artifact."""

    dream_id: str
    created_at: datetime
    source: str
    confidence: float
    tension_score: float
    left_hemisphere: str
    right_hemisphere: str
    creative_bridge: str
    keywords: list[str] = field(default_factory=list)
    revisit_count: int = 0
    status: str = "incubating"  # incubating → reconsidered → promoted → archived → expired
    last_revisited: datetime | None = None
    promoted_to_memory_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.

        Returns:
            dict[str, Any]
        """
        return {
            "dream_id": self.dream_id,
            "created_at": self.created_at.isoformat(),
            "source": self.source,
            "confidence": round(self.confidence, 4),
            "tension_score": round(self.tension_score, 4),
            "left_hemisphere": self.left_hemisphere,
            "right_hemisphere": self.right_hemisphere,
            "creative_bridge": self.creative_bridge,
            "keywords": self.keywords,
            "revisit_count": self.revisit_count,
            "status": self.status,
            "last_revisited": self.last_revisited.isoformat() if self.last_revisited else None,
            "promoted_to_memory_id": self.promoted_to_memory_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DreamArtifact:
        """
        Convert to/from m dict.

        Args:
            cls: Parameter description.
            data: Parameter description.

        Returns:
            DreamArtifact
        """
        return cls(
            dream_id=data["dream_id"],
            created_at=datetime.fromisoformat(data["created_at"]),
            source=data.get("source", "unknown"),
            confidence=data.get("confidence", 0.0),
            tension_score=data.get("tension_score", 0.0),
            left_hemisphere=data.get("left_hemisphere", ""),
            right_hemisphere=data.get("right_hemisphere", ""),
            creative_bridge=data.get("creative_bridge", ""),
            keywords=data.get("keywords", []),
            revisit_count=data.get("revisit_count", 0),
            status=data.get("status", "incubating"),
            last_revisited=datetime.fromisoformat(data["last_revisited"]) if data.get("last_revisited") else None,
            promoted_to_memory_id=data.get("promoted_to_memory_id"),
        )


def _dreams_dir() -> Path:
    from whitemagic.config.paths import DREAMS_DIR

    DREAMS_DIR.mkdir(parents=True, exist_ok=True)
    return DREAMS_DIR


def _sanitize_filename(text: str, max_len: int = 40) -> str:
    """Create a filesystem-safe slug from text."""
    slug = re.sub(r"[^\w\s-]", "", text).strip().lower()
    slug = re.sub(r"[-\s]+", "-", slug)
    return slug[:max_len]


def _extract_keywords(left: str, right: str, bridge: str) -> list[str]:
    """Heuristic keyword extraction from dream text."""
    text = f"{left} {right} {bridge}".lower()
    # Simple frequency-based extraction
    words = re.findall(r"\b[a-z]{4,}\b", text)
    stop = {
        "should", "would", "could", "might", "maybe", "perhaps", "this", "that",
        "with", "from", "have", "been", "were", "they", "them", "their", "there",
        "what", "when", "where", "which", "while", "about", "into", "through",
        "during", "before", "after", "above", "below", "between", "among",
    }
    filtered = [w for w in words if w not in stop]
    # Return top 5 unique by frequency
    counts: dict[str, int] = {}
    for w in filtered:
        counts[w] = counts.get(w, 0) + 1
    top = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return [w for w, _ in top]


# ---------------------------------------------------------------------------
# Writer — listens to Gan Ying bus
# ---------------------------------------------------------------------------

class DreamArtifactWriter:
    """Listens for CREATIVE_BRIDGE_LOW_CONFIDENCE and writes YAML artifacts."""

    def __init__(self) -> None:
        self._listening = False
        self._lock = threading.Lock()

    def start_listening(self) -> None:
        """Idempotently register on the Gan Ying bus."""
        with self._lock:
            if self._listening:
                return
            try:
                from whitemagic.core.resonance import EventType, get_bus
                get_bus().listen(EventType.CREATIVE_BRIDGE_LOW_CONFIDENCE, self._on_event)
                self._listening = True
                logger.info("DreamArtifactWriter registered on Gan Ying bus")
            except Exception as exc:
                logger.warning(f"DreamArtifactWriter failed to register: {exc}")

    def _on_event(self, event: Any) -> None:
        data = getattr(event, "data", {})
        if not data:
            return
        try:
            self.write_artifact(
                query=data.get("query", ""),
                left=data.get("left", ""),
                right=data.get("right", ""),
                synthesis=data.get("synthesis", ""),
                confidence=data.get("confidence", 0.0),
                tension=data.get("tension", 0.0),
                dominant=data.get("dominant", "balanced"),
            )
        except Exception as exc:
            logger.error(f"Failed to write dream artifact: {exc}", exc_info=True)

    def write_artifact(
        self,
        query: str,
        left: str,
        right: str,
        synthesis: str,
        confidence: float,
        tension: float,
        dominant: str,
    ) -> DreamArtifact:
        """Write a dream artifact to disk."""
        now = datetime.now(UTC)
        slug = _sanitize_filename(query or "dream")
        uid = uuid.uuid4().hex[:8]
        dream_id = f"dream_{now.strftime('%Y%m%d_%H%M%S')}_{uid}"
        path = _dreams_dir() / f"{dream_id}_{slug}.yaml"

        bridge = synthesis or right or left
        artifact = DreamArtifact(
            dream_id=dream_id,
            created_at=now,
            source="bicameral_reasoner",
            confidence=confidence,
            tension_score=tension,
            left_hemisphere=left,
            right_hemisphere=right,
            creative_bridge=bridge,
            keywords=_extract_keywords(left, right, bridge),
        )

        with open(path, "w", encoding="utf-8") as fp:
            yaml.dump(artifact.to_dict(), fp, default_flow_style=False, sort_keys=False, allow_unicode=True)

        logger.info(f"Dream artifact written: {path.name}")
        return artifact


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def list_dreams(status_filter: str | None = None) -> list[dict[str, Any]]:
    """List all dream artifacts, optionally filtered by status."""
    dreams_dir = _dreams_dir()
    results: list[dict[str, Any]] = []
    for path in sorted(dreams_dir.glob("*.yaml"), reverse=True):
        try:
            with open(path, encoding="utf-8") as fp:
                data = yaml.safe_load(fp)
            if data and (status_filter is None or data.get("status") == status_filter):
                data["_filename"] = path.name
                results.append(data)
        except Exception as exc:
            logger.debug(f"Skipping unreadable dream {path.name}: {exc}")
    return results


def read_dream(dream_id: str) -> dict[str, Any] | None:
    """Read a single dream artifact by ID."""
    dreams_dir = _dreams_dir()
    for path in dreams_dir.glob("*.yaml"):
        if dream_id in path.name:
            try:
                with open(path, encoding="utf-8") as fp:
                    data = yaml.safe_load(fp)
                if data and data.get("dream_id") == dream_id:
                    data["_filename"] = path.name
                    return data
            except Exception as exc:
                logger.warning(f"Failed to read dream {path.name}: {exc}")
    return None


def _update_dream_file(dream_id: str, **kwargs: Any) -> dict[str, Any] | None:
    """Update fields in a dream artifact file."""
    dreams_dir = _dreams_dir()
    for path in dreams_dir.glob("*.yaml"):
        if dream_id in path.name:
            try:
                with open(path, encoding="utf-8") as fp:
                    data = yaml.safe_load(fp)
                if not data or data.get("dream_id") != dream_id:
                    continue
                for k, v in kwargs.items():
                    data[k] = v
                with open(path, "w", encoding="utf-8") as fp:
                    yaml.dump(data, fp, default_flow_style=False, sort_keys=False, allow_unicode=True)
                data["_filename"] = path.name
                return data
            except Exception as exc:
                logger.warning(f"Failed to update dream {path.name}: {exc}")
    return None


def promote_dream(dream_id: str, memory_id: str | None = None) -> dict[str, Any] | None:
    """Promote a dream to a real memory (or mark as promoted)."""
    mem_id = memory_id or f"mem_{uuid.uuid4().hex[:12]}"
    return _update_dream_file(
        dream_id,
        status="promoted",
        promoted_to_memory_id=mem_id,
        last_revisited=datetime.now(UTC).isoformat(),
    )


def expire_dream(dream_id: str) -> dict[str, Any] | None:
    """Mark a dream as expired (soft delete)."""
    return _update_dream_file(
        dream_id,
        status="expired",
        last_revisited=datetime.now(UTC).isoformat(),
    )


def archive_dream(dream_id: str) -> dict[str, Any] | None:
    """Mark a dream as archived."""
    return _update_dream_file(
        dream_id,
        status="archived",
        last_revisited=datetime.now(UTC).isoformat(),
    )


def revisit_dream(dream_id: str) -> dict[str, Any] | None:
    """Increment revisit count and update timestamp."""
    data = read_dream(dream_id)
    if data is None:
        return None
    return _update_dream_file(
        dream_id,
        revisit_count=data.get("revisit_count", 0) + 1,
        last_revisited=datetime.now(UTC).isoformat(),
    )
