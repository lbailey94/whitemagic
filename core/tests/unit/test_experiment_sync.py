"""Tests for Experiment Sync — P2P experiment sharing via mesh."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")

import json

import pytest

from whitemagic.core.evolution.research_dag import ResearchDomain
from whitemagic.mesh.experiment_sync import (
    DOMAIN_TOPICS,
    PeerExperiment,
    get_experiment_sync,
)


@pytest.fixture
def sync():
    """Get a fresh ExperimentSync instance."""
    return get_experiment_sync()


class TestDomainTopics:
    def test_all_domains_mapped(self):
        for domain in ResearchDomain:
            assert domain in DOMAIN_TOPICS or domain == ResearchDomain.CUSTOM

    def test_topic_format(self):
        for domain, topic in DOMAIN_TOPICS.items():
            assert topic.startswith("wm/research/")


class TestPeerExperiment:
    def test_creation(self):
        peer_exp = PeerExperiment(
            experiment_id="peer_001",
            source_node="node_abc",
            domain=ResearchDomain.COGNITIVE,
            hypothesis="Peer hypothesis",
            fitness_score=0.75,
        )
        assert peer_exp.experiment_id == "peer_001"
        assert peer_exp.source_node == "node_abc"
        assert peer_exp.imported is False

    def test_to_dict(self):
        peer_exp = PeerExperiment(
            experiment_id="peer_002",
            source_node="node_xyz",
            domain=ResearchDomain.MEMORY,
            hypothesis="Test",
            fitness_score=0.6,
        )
        d = peer_exp.to_dict()
        assert d["experiment_id"] == "peer_002"
        assert d["domain"] == "memory"


class TestExperimentSync:
    def test_get_status(self, sync):
        status = sync.get_status()
        assert "stats" in status
        assert "peer_experiments_cached" in status
        assert "pending_broadcasts" in status
        assert "topics" in status

    def test_receive_experiment(self, sync):
        payload = json.dumps({
            "type": "experiment_share",
            "experiment_id": "peer_exp_001",
            "hypothesis": "Remote experiment about coherence",
            "domain": "cognitive",
            "stage": "result",
            "fitness_score": 0.82,
            "parameters": {"sattvic_target": 0.22},
            "agent_id": "remote_node_1",
            "source_node": "remote_node_1",
        })

        result = sync.receive_experiment(payload, source_node="remote_node_1")
        assert result["status"] == "success"
        assert result["received"] is True

    def test_receive_breakthrough(self, sync):
        payload = json.dumps({
            "type": "experiment_share",
            "experiment_id": "peer_breakthrough_001",
            "hypothesis": "Major breakthrough in evolution",
            "domain": "evolution",
            "stage": "breakthrough",
            "fitness_score": 0.95,
            "parameters": {"mutation_rate": 0.15},
            "source_node": "breakthrough_node",
        })

        result = sync.receive_experiment(payload, source_node="breakthrough_node")
        assert result["status"] == "success"

    def test_receive_invalid_payload(self, sync):
        result = sync.receive_experiment("invalid json", source_node="test")
        assert result["status"] == "error"

    def test_get_peer_experiments(self, sync):
        # Add a peer experiment
        payload = json.dumps({
            "experiment_id": "peer_list_001",
            "hypothesis": "Test for listing",
            "domain": "memory",
            "stage": "result",
            "fitness_score": 0.7,
            "source_node": "list_node",
        })
        sync.receive_experiment(payload, source_node="list_node")

        exps = sync.get_peer_experiments(domain=ResearchDomain.MEMORY)
        assert any(e["experiment_id"] == "peer_list_001" for e in exps)

    def test_discover_peers(self, sync):
        result = sync.discover_peers()
        assert "status" in result
        # In local-only mode, should return empty or local peers
        assert "peers" in result or "error" in result

    def test_sync_pending_empty(self, sync):
        result = sync.sync_pending()
        assert result["status"] == "success"
        assert result["pending"] == 0

    def test_share_experiment_nonexistent(self, sync):
        result = sync.share_experiment("nonexistent_exp_id")
        assert result["status"] == "error"
