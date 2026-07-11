# ruff: noqa: BLE001
"""Experiment Sync — P2P Experiment Sharing via Mesh (v24.3.0).

Inspired by Hyperspace's GossipSub-based experiment sharing, this module
wires WhiteMagic's mesh client to broadcast and receive experiment results
across the P2P network.

GossipSub topics mapped to WhiteMagic research domains:
    wm/research/cognitive     — cognitive optimization experiments
    wm/research/memory        — memory system experiments
    wm/research/consciousness — consciousness tuning experiments
    wm/research/evolution     — evolutionary algorithm experiments
    wm/research/synthesis     — cross-domain synthesis experiments

The sync module:
1. Broadcasts experiment results to peers via mesh client
2. Receives experiment results from peers and imports to Research DAG
3. Maintains a local CRDT-like log of known peer experiments
4. Integrates with ConsciousnessLoop for periodic sync

Local-only fallback: when mesh is not connected, experiments are logged
locally and synced when connection is established.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from whitemagic.core.evolution.research_dag import (
    Experiment,
    ExperimentStage,
    ResearchDAG,
    ResearchDomain,
    get_research_dag,
)

logger = logging.getLogger(__name__)

# Domain → GossipSub topic mapping
DOMAIN_TOPICS: dict[ResearchDomain, str] = {
    ResearchDomain.COGNITIVE: "wm/research/cognitive",
    ResearchDomain.MEMORY: "wm/research/memory",
    ResearchDomain.CONSCIOUSNESS: "wm/research/consciousness",
    ResearchDomain.EVOLUTION: "wm/research/evolution",
    ResearchDomain.SYNTHESIS: "wm/research/synthesis",
    ResearchDomain.GOVERNANCE: "wm/research/governance",
    ResearchDomain.INFERENCE: "wm/research/inference",
    ResearchDomain.CUSTOM: "wm/research/custom",
}


@dataclass
class PeerExperiment:
    """An experiment received from a peer node."""

    experiment_id: str
    source_node: str
    domain: ResearchDomain
    hypothesis: str
    fitness_score: float
    parameters: dict[str, Any] = field(default_factory=dict)
    stage: str = "result"
    received_at: str = field(default_factory=lambda: datetime.now().isoformat())
    imported: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment_id,
            "source_node": self.source_node,
            "domain": self.domain.value,
            "hypothesis": self.hypothesis,
            "fitness_score": self.fitness_score,
            "parameters": self.parameters,
            "stage": self.stage,
            "received_at": self.received_at,
            "imported": self.imported,
        }


@dataclass
class SyncStats:
    """Statistics for experiment sync."""

    experiments_sent: int = 0
    experiments_received: int = 0
    experiments_imported: int = 0
    breakthroughs_received: int = 0
    last_sync_time: float = 0.0
    peers_known: int = 0


class ExperimentSync:
    """P2P experiment synchronization via the mesh network.

    Broadcasts experiment results to peers and imports received
    experiments into the local Research DAG.
    """

    _instance: ExperimentSync | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self._dag = get_research_dag()
        self._stats = SyncStats()
        self._stats_lock = threading.RLock()
        self._peer_experiments: dict[str, PeerExperiment] = {}
        self._peer_lock = threading.RLock()
        self._pending_broadcast: list[dict[str, Any]] = []
        self._broadcast_lock = threading.RLock()
        self._known_peers: set[str] = set()

    @classmethod
    def get_instance(cls) -> ExperimentSync:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def share_experiment(
        self,
        experiment_id: str,
        domain: ResearchDomain | None = None,
    ) -> dict[str, Any]:
        """Share an experiment result to the P2P mesh.

        Serializes the experiment and broadcasts it via the mesh client.
        If mesh is not connected, queues for later sync.
        """
        exp = self._dag._load(experiment_id)
        if exp is None:
            return {"status": "error", "error": "Experiment not found"}

        try:
            from whitemagic.mesh.client import get_mesh_client
            client = get_mesh_client()

            payload = json.dumps({
                "type": "experiment_share",
                "experiment_id": exp.experiment_id,
                "hypothesis": exp.hypothesis,
                "domain": exp.domain.value,
                "stage": exp.stage.value,
                "fitness_score": exp.fitness_score,
                "parameters": exp.parameters,
                "agent_id": exp.agent_id,
                "created_at": exp.created_at,
                "galactic_zone": exp.galactic_zone,
                "source_node": client._node_id,
                "timestamp": datetime.now().isoformat(),
            })

            signal = client.broadcast_signal(
                signal_type="EXPERIMENT_SHARE",
                payload=payload,
            )

            with self._stats_lock:
                self._stats.experiments_sent += 1
                self._stats.last_sync_time = time.time()

            logger.info(
                "ExperimentSync: shared [%s] domain=%s fitness=%.4f (success=%s)",
                experiment_id[:8], exp.domain.value, exp.fitness_score, signal.success,
            )

            return {
                "status": "success",
                "shared": True,
                "mesh_connected": client._connected,
                "experiment_id": experiment_id,
            }

        except Exception as e:
            # Queue for later sync
            with self._broadcast_lock:
                self._pending_broadcast.append({
                    "experiment_id": experiment_id,
                    "domain": domain.value if domain else exp.domain.value,
                    "queued_at": time.time(),
                })

            logger.debug("ExperimentSync: queued for later sync: %s", e, exc_info=True)
            return {"status": "queued", "error": str(e)}

    def receive_experiment(self, payload: str, source_node: str = "") -> dict[str, Any]:
        """Receive and import an experiment from a peer node.

        Called when a EXPERIMENT_SHARE signal is received from the mesh.
        Imports the experiment into the local Research DAG.
        """
        try:
            data = json.loads(payload)
            exp_id = data.get("experiment_id", "")
            domain_str = data.get("domain", "custom")
            domain = ResearchDomain(domain_str)

            peer_exp = PeerExperiment(
                experiment_id=exp_id,
                source_node=source_node or data.get("source_node", "unknown"),
                domain=domain,
                hypothesis=data.get("hypothesis", ""),
                fitness_score=float(data.get("fitness_score", 0.0)),
                parameters=data.get("parameters", {}),
                stage=data.get("stage", "result"),
            )

            with self._peer_lock:
                self._peer_experiments[exp_id] = peer_exp
                self._known_peers.add(peer_exp.source_node)

            # Import to DAG if it's a result or breakthrough
            if peer_exp.stage in ("result", "breakthrough"):
                imported = self._import_to_dag(peer_exp)
                peer_exp.imported = imported

            with self._stats_lock:
                self._stats.experiments_received += 1
                if peer_exp.imported:
                    self._stats.experiments_imported += 1
                if peer_exp.stage == "breakthrough":
                    self._stats.breakthroughs_received += 1
                self._stats.peers_known = len(self._known_peers)

            logger.info(
                "ExperimentSync: received [%s] from %s, domain=%s, fitness=%.4f",
                exp_id[:8], peer_exp.source_node[:12], domain.value, peer_exp.fitness_score,
            )

            return {
                "status": "success",
                "received": True,
                "imported": peer_exp.imported,
                "experiment_id": exp_id,
            }

        except Exception as e:
            logger.error("ExperimentSync: receive failed: %s", e, exc_info=True)
            return {"status": "error", "error": str(e)}

    def sync_pending(self) -> dict[str, Any]:
        """Sync pending broadcasts when mesh becomes available."""
        with self._broadcast_lock:
            pending = list(self._pending_broadcast)
            self._pending_broadcast.clear()

        synced = 0
        for item in pending:
            result = self.share_experiment(
                item["experiment_id"],
                ResearchDomain(item["domain"]) if item.get("domain") else None,
            )
            if result.get("status") == "success":
                synced += 1

        return {
            "status": "success",
            "pending": len(pending),
            "synced": synced,
        }

    def discover_peers(self) -> dict[str, Any]:
        """Discover peers on the mesh network."""
        try:
            from whitemagic.mesh.client import get_mesh_client
            client = get_mesh_client()
            peers = client.discover_peers()

            with self._stats_lock:
                self._stats.peers_known = len(peers)

            return {
                "status": "success",
                "peers": [p.to_dict() for p in peers],
                "peer_count": len(peers),
                "mesh_connected": client._connected,
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def get_status(self) -> dict[str, Any]:
        """Get sync status."""
        with self._stats_lock:
            stats = SyncStats(
                experiments_sent=self._stats.experiments_sent,
                experiments_received=self._stats.experiments_received,
                experiments_imported=self._stats.experiments_imported,
                breakthroughs_received=self._stats.breakthroughs_received,
                last_sync_time=self._stats.last_sync_time,
                peers_known=self._stats.peers_known,
            )

        with self._peer_lock:
            peer_exps = len(self._peer_experiments)

        with self._broadcast_lock:
            pending = len(self._pending_broadcast)

        return {
            "stats": {
                "experiments_sent": stats.experiments_sent,
                "experiments_received": stats.experiments_received,
                "experiments_imported": stats.experiments_imported,
                "breakthroughs_received": stats.breakthroughs_received,
                "peers_known": stats.peers_known,
                "last_sync_time": stats.last_sync_time,
            },
            "peer_experiments_cached": peer_exps,
            "pending_broadcasts": pending,
            "topics": {d.value: t for d, t in DOMAIN_TOPICS.items()},
        }

    def get_peer_experiments(
        self,
        domain: ResearchDomain | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get experiments received from peers."""
        with self._peer_lock:
            exps = list(self._peer_experiments.values())
        if domain:
            exps = [e for e in exps if e.domain == domain]
        exps.sort(key=lambda e: e.fitness_score, reverse=True)
        return [e.to_dict() for e in exps[:limit]]

    def _import_to_dag(self, peer_exp: PeerExperiment) -> bool:
        """Import a peer experiment into the local Research DAG."""
        try:
            # Submit as hypothesis first
            exp = self._dag.submit_hypothesis(
                hypothesis=f"[Peer:{peer_exp.source_node[:8]}] {peer_exp.hypothesis}",
                domain=peer_exp.domain,
                parameters=peer_exp.parameters,
                agent_id=peer_exp.source_node,
                metadata={
                    "source": "peer_share",
                    "source_node": peer_exp.source_node,
                    "original_id": peer_exp.experiment_id,
                    "received_at": peer_exp.received_at,
                },
            )

            # Record the result
            self._dag.record_result(
                exp.experiment_id,
                fitness_score=peer_exp.fitness_score,
                outcome={"peer_imported": True, "original_id": peer_exp.experiment_id},
            )

            return True
        except Exception as e:
            logger.debug("Peer experiment import: %s", e, exc_info=True)
            return False


def get_experiment_sync() -> ExperimentSync:
    """Get the singleton ExperimentSync instance."""
    return ExperimentSync.get_instance()
