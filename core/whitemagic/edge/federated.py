# ruff: noqa: BLE001
"""
Federated Learning for WhiteMagic Edge AI.

Enables collective intelligence without sharing private data.
Each node learns locally and shares only patterns/rules.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

from whitemagic.config.paths import get_state_root

logger = logging.getLogger(__name__)


class FederatedLearning:
    """Federated learning coordinator."""

    def __init__(self, data_dir: Path | None = None) -> None:
        if data_dir is None:
            data_dir = get_state_root() / "edge" / "federated"
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.nodes: dict[str, dict[str, Any]] = {}
        self.shared_patterns: list[dict[str, Any]] = []

    def register_node(
        self, node_id: str, capabilities: list[str] | None = None
    ) -> None:
        """Register a federated node."""
        self.nodes[node_id] = {
            "capabilities": capabilities or [],
            "registered": time.time(),
            "patterns_shared": 0,
        }

    def share_pattern(self, node_id: str, pattern: dict[str, Any]) -> None:
        """Share a pattern from a node (no raw data shared)."""
        entry = {
            "node_id": node_id,
            "pattern": pattern,
            "timestamp": time.time(),
        }
        self.shared_patterns.append(entry)
        if node_id in self.nodes:
            self.nodes[node_id]["patterns_shared"] += 1
        with open(self.data_dir / "shared_patterns.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")

    def aggregate_patterns(self) -> list[dict[str, Any]]:
        """Aggregate shared patterns across nodes."""
        by_type: dict[str, list[dict[str, Any]]] = {}
        for entry in self.shared_patterns:
            ptype = entry["pattern"].get("type", "unknown")
            by_type.setdefault(ptype, []).append(entry)

        aggregated: list[dict[str, Any]] = []
        for ptype, entries in by_type.items():
            if len(entries) >= 2:
                aggregated.append(
                    {
                        "type": ptype,
                        "node_count": len(set(e["node_id"] for e in entries)),
                        "total_patterns": len(entries),
                    }
                )
        return aggregated

    def summary(self) -> dict[str, Any]:
        return {
            "total_nodes": len(self.nodes),
            "total_patterns": len(self.shared_patterns),
            "aggregated_clusters": len(self.aggregate_patterns()),
        }


_federated: FederatedLearning | None = None


def get_federated() -> FederatedLearning:
    global _federated
    if _federated is None:
        _federated = FederatedLearning()
    return _federated
