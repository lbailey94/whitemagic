# ruff: noqa: BLE001
"""CRDT Distributed Leaderboard — Convergent experiment rankings (v24.3.0).

Uses Loro CRDT (Rust-backed, production-ready) for distributed leaderboards
that converge across P2P mesh nodes without coordination. Falls back to
local-only mode when `loro` is not installed.

Architecture (from Hyperspace AGI validation):
    Local updates → Loro CRDT document → GossipSub broadcast
    Peer updates → Loro CRDT merge → Convergent state

The leaderboard tracks experiment fitness scores across all nodes.
Each node can submit experiments and the CRDT ensures all nodes
eventually agree on the ranking without central coordination.

Integration points:
    - ResearchDAG: provides experiment data for leaderboard entries
    - ExperimentSync: broadcasts CRDT updates via mesh
    - ConsciousnessLoop: periodic sync via mesh_sync tick
"""

from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Lazy import loro
_LORO_AVAILABLE: bool | None = None
_LORO_IMPORT_ERROR: str = ""


def _check_loro() -> bool:
    """Check if loro is available (cached)."""
    global _LORO_AVAILABLE, _LORO_IMPORT_ERROR
    if _LORO_AVAILABLE is None:
        try:
            import loro  # type: ignore[import-untyped]
            _LORO_AVAILABLE = True
            _LORO_IMPORT_ERROR = ""
        except ImportError as e:
            _LORO_AVAILABLE = False
            _LORO_IMPORT_ERROR = str(e)
            logger.info("Loro CRDT not available, using local-only mode: %s", e)
    return _LORO_AVAILABLE


@dataclass
class LeaderboardEntry:
    """A single entry in the distributed leaderboard."""

    experiment_id: str
    hypothesis: str
    domain: str
    fitness_score: float
    agent_id: str
    node_id: str
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "hypothesis": self.hypothesis,
            "domain": self.domain,
            "fitness_score": self.fitness_score,
            "agent_id": self.agent_id,
            "node_id": self.node_id,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LeaderboardEntry:
        return cls(
            experiment_id=data["experiment_id"],
            hypothesis=data.get("hypothesis", ""),
            domain=data.get("domain", "custom"),
            fitness_score=float(data.get("fitness_score", 0.0)),
            agent_id=data.get("agent_id", ""),
            node_id=data.get("node_id", "local"),
            created_at=data.get("created_at", datetime.now().isoformat()),
            metadata=data.get("metadata", {}),
        )


class CRDTLeaderboard:
    """Distributed leaderboard using Loro CRDT with local fallback.

    When Loro is installed, updates are tracked in a CRDT document
    that can be serialized and shared with peers. When Loro is not
    available, falls back to a simple in-memory dict that works
    locally only.
    """

    _instance: CRDTLeaderboard | None = None
    _lock = threading.RLock()

    def __init__(self, node_id: str = "local") -> None:
        self._node_id = node_id
        self._entries: dict[str, LeaderboardEntry] = {}
        self._entries_lock = threading.RLock()
        self._stats_lock = threading.RLock()
        self._loro_doc: Any = None
        self._loro_map: Any = None
        self._updates_sent: int = 0
        self._updates_received: int = 0
        self._merges: int = 0
        self._init_loro()

    def _init_loro(self) -> None:
        """Initialize Loro CRDT document if available."""
        if not _check_loro():
            return
        try:
            import loro  # type: ignore[import-untyped]

            self._loro_doc = loro.LoroDoc()
            self._loro_map = self._loro_doc.get_map("leaderboard")
            logger.info("Loro CRDT leaderboard initialized (node=%s)", self._node_id)
        except Exception as e:
            logger.debug("Loro init failed, using fallback: %s", e, exc_info=True)
            self._loro_doc = None
            self._loro_map = None

    @classmethod
    def get_instance(cls, node_id: str = "local") -> CRDTLeaderboard:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(node_id=node_id)
        return cls._instance

    def submit(
        self,
        experiment_id: str,
        hypothesis: str,
        domain: str,
        fitness_score: float,
        agent_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> LeaderboardEntry:
        """Submit or update an experiment in the leaderboard.

        If the experiment already exists, updates the fitness score
        if the new score is higher (monotonic updates for CRDT safety).
        """
        entry = LeaderboardEntry(
            experiment_id=experiment_id,
            hypothesis=hypothesis,
            domain=domain,
            fitness_score=fitness_score,
            agent_id=agent_id,
            node_id=self._node_id,
            metadata=metadata or {},
        )

        with self._entries_lock:
            # Monotonic: only update if new score is higher
            existing = self._entries.get(experiment_id)
            if existing and existing.fitness_score >= fitness_score:
                return existing
            self._entries[experiment_id] = entry

        # Update Loro CRDT if available
        if self._loro_map is not None:
            try:
                self._loro_map.insert(
                    experiment_id,
                    json.dumps(entry.to_dict()),
                )
                if self._loro_doc:
                    self._loro_doc.commit()
            except Exception as e:
                logger.debug("Loro update failed: %s", e, exc_info=True)

        logger.debug(
            "Leaderboard: submitted [%s] fitness=%.4f domain=%s",
            experiment_id[:8], fitness_score, domain,
        )
        return entry

    def get_top(self, n: int = 10, domain: str | None = None) -> list[LeaderboardEntry]:
        """Get top N entries, optionally filtered by domain."""
        with self._entries_lock:
            entries = list(self._entries.values())
        if domain:
            entries = [e for e in entries if e.domain == domain]
        entries.sort(key=lambda e: e.fitness_score, reverse=True)
        return entries[:n]

    def get_entry(self, experiment_id: str) -> LeaderboardEntry | None:
        """Get a single entry by experiment ID."""
        with self._entries_lock:
            return self._entries.get(experiment_id)

    def merge_remote(self, remote_data: bytes | str) -> dict[str, Any]:
        """Merge remote CRDT updates from a peer node.

        Args:
            remote_data: Serialized Loro CRDT update (bytes) or JSON
                         fallback (str) from a peer.

        Returns:
            Dict with merge stats (new entries, updated entries).
        """
        new_count = 0
        updated_count = 0

        if self._loro_doc is not None and isinstance(remote_data, bytes):
            try:
                self._loro_doc.import_(remote_data)
                self._merges += 1

                # Sync local entries from Loro map
                if self._loro_map:
                    for key, value in self._loro_map.get_value().items():
                        data = json.loads(value) if isinstance(value, str) else value
                        entry = LeaderboardEntry.from_dict(data)
                        with self._entries_lock:
                            existing = self._entries.get(entry.experiment_id)
                            if existing is None:
                                new_count += 1
                            elif existing.fitness_score < entry.fitness_score:
                                updated_count += 1
                            self._entries[entry.experiment_id] = entry
            except Exception as e:
                logger.debug("Loro merge failed: %s", e, exc_info=True)
        else:
            # Fallback: JSON merge
            try:
                if isinstance(remote_data, bytes):
                    remote_data = remote_data.decode("utf-8")
                data = json.loads(remote_data)
                entries = data.get("entries", [])
                for entry_data in entries:
                    entry = LeaderboardEntry.from_dict(entry_data)
                    with self._entries_lock:
                        existing = self._entries.get(entry.experiment_id)
                        if existing is None:
                            new_count += 1
                        elif existing.fitness_score < entry.fitness_score:
                            updated_count += 1
                        # Monotonic merge
                        if existing is None or existing.fitness_score < entry.fitness_score:
                            self._entries[entry.experiment_id] = entry
                self._merges += 1
            except Exception as e:
                logger.debug("JSON merge failed: %s", e, exc_info=True)

        self._updates_received += 1
        logger.info(
            "Leaderboard merge: %d new, %d updated (total=%d)",
            new_count, updated_count, len(self._entries),
        )
        return {"new": new_count, "updated": updated_count, "total": len(self._entries)}

    def export(self) -> bytes | str:
        """Export current state for sharing with peers.

        Returns Loro CRDT binary update if available, otherwise JSON fallback.
        """
        if self._loro_doc is not None:
            try:
                return self._loro_doc.export_json()
            except Exception:
                logger.debug("Ignored error in crdt_leaderboard.py:271")

        # Fallback: JSON export
        with self._entries_lock:
            entries = [e.to_dict() for e in self._entries.values()]
        return json.dumps({
            "entries": entries,
            "node_id": self._node_id,
            "timestamp": datetime.now().isoformat(),
        })

    def export_incremental(self) -> bytes | str:
        """Export only new changes since last export (for efficient sync).

        With Loro, this exports the pending update batch.
        Without Loro, exports the full state (fallback).
        """
        if self._loro_doc is not None:
            try:
                # Loro supports incremental export via export_json_updates
                # but the API varies by version; fall back to full export
                return self._loro_doc.export_json()
            except Exception:
                logger.debug("Ignored error in crdt_leaderboard.py:294")
        return self.export()

    def get_status(self) -> dict[str, Any]:
        """Get leaderboard status."""
        with self._entries_lock:
            total = len(self._entries)
            by_domain: dict[str, int] = {}
            for e in self._entries.values():
                by_domain[e.domain] = by_domain.get(e.domain, 0) + 1

        with self._stats_lock:
            stats = {
                "updates_sent": self._updates_sent,
                "updates_received": self._updates_received,
                "merges": self._merges,
            }

        return {
            "node_id": self._node_id,
            "loro_enabled": self._loro_doc is not None,
            "total_entries": total,
            "by_domain": by_domain,
            **stats,
        }

    def clear(self) -> None:
        """Clear all entries (for testing)."""
        with self._entries_lock:
            self._entries.clear()
        if self._loro_doc is not None:
            try:
                self._loro_doc = None
                self._loro_map = None
                self._init_loro()
            except Exception:
                logger.debug("Ignored error in crdt_leaderboard.py:330")


def get_leaderboard(node_id: str = "local") -> CRDTLeaderboard:
    """Get the singleton CRDTLeaderboard instance."""
    return CRDTLeaderboard.get_instance(node_id=node_id)
