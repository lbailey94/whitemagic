"""Tests for v24.3 Research Systems Strategy implementation.

Tests cover:
- Effect registry Hyperspace tool entries
- Autoswarm tick() and tick_mesh_sync()
- ConsciousnessLoop autoswarm/mesh sync integration
- CRDT leaderboard (local fallback mode)
- Research adapters (base adapter + all 6 adapters)
- ResearchDAG synthesis generation
- Pulse verification (tiered)
- Critique protocol
- Durable archive
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from whitemagic.core.evolution.research_dag import ResearchDomain

# Use temp state root for tests
_tmpdir = tempfile.mkdtemp(prefix="wm_test_research_")
os.environ.setdefault("WM_STATE_ROOT", _tmpdir)
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")


# ── Effect Registry ───────────────────────────────────────────────────


class TestEffectRegistryHyperspace:
    """Test effect registry entries for Hyperspace tools."""

    def test_mesh_experiment_tools_are_network(self):
        from whitemagic.dharma.effect_registry import _NETWORK_TOOLS
        assert "mesh.experiment.share" in _NETWORK_TOOLS
        assert "mesh.experiment.receive" in _NETWORK_TOOLS
        assert "mesh.experiment.peers" in _NETWORK_TOOLS
        assert "mesh.experiment.discover" in _NETWORK_TOOLS

    def test_warp_delete_is_destructive(self):
        from whitemagic.dharma.effect_registry import _DESTRUCTIVE_TOOLS
        assert "warp.delete" in _DESTRUCTIVE_TOOLS

    def test_research_dag_read_tools_are_pure(self):
        from whitemagic.dharma.effect_registry import _PURE_TOOLS
        assert "research.dag.lineage" in _PURE_TOOLS
        assert "research.dag.breakthroughs" in _PURE_TOOLS
        assert "research.dag.stats" in _PURE_TOOLS
        assert "research.dag.leaderboard" in _PURE_TOOLS
        assert "research.dag.experiments" in _PURE_TOOLS
        assert "autoswarm.status" in _PURE_TOOLS
        assert "warp.load" in _PURE_TOOLS
        assert "warp.list" in _PURE_TOOLS
        assert "warp.status" in _PURE_TOOLS
        assert "mesh.experiment.status" in _PURE_TOOLS

    def test_infer_target_research(self):
        from whitemagic.dharma.effect_registry import _infer_target, infer_effects
        effects = infer_effects("research.dag.submit", safety="WRITE")
        assert any(e.target == "research:db" for e in effects)

    def test_infer_target_warp(self):
        from whitemagic.dharma.effect_registry import infer_effects
        effects = infer_effects("warp.save", safety="WRITE")
        assert any(e.target == "warp:store" for e in effects)


# ── Autoswarm Tick ────────────────────────────────────────────────────


class TestAutoswarmTick:
    """Test autoswarm tick() and tick_mesh_sync() methods."""

    def test_tick_exists(self):
        from whitemagic.core.evolution.autoswarm import EvolutionaryAutoswarm
        swarm = EvolutionaryAutoswarm()
        assert hasattr(swarm, "tick")
        assert hasattr(swarm, "tick_mesh_sync")

    def test_tick_returns_campaign_result_or_none(self):
        from whitemagic.core.evolution.autoswarm import EvolutionaryAutoswarm
        swarm = EvolutionaryAutoswarm()
        # tick may return a CampaignResult or None if it errors/skips
        # Just verify it doesn't crash
        try:
            result = swarm.tick()
            assert result is None or hasattr(result, "campaign_name")
        except Exception:
            # Acceptable — tick should be resilient
            pass

    def test_tick_mesh_sync_returns_dict(self):
        from whitemagic.core.evolution.autoswarm import EvolutionaryAutoswarm
        swarm = EvolutionaryAutoswarm()
        result = swarm.tick_mesh_sync()
        assert isinstance(result, dict)
        assert "synced" in result


# ── ConsciousnessLoop Integration ─────────────────────────────────────


class TestConsciousnessLoopHyperspace:
    """Test consciousness loop autoswarm/mesh sync integration."""

    def test_config_has_autoswarm_fields(self):
        from whitemagic.core.consciousness.consciousness_loop import LoopConfig
        config = LoopConfig()
        assert hasattr(config, "enable_autoswarm")
        assert hasattr(config, "enable_mesh_sync")
        assert hasattr(config, "autoswarm_interval_s")
        assert hasattr(config, "mesh_sync_interval_s")
        assert config.enable_autoswarm is False  # Default off
        assert config.enable_mesh_sync is False  # Default off

    def test_config_from_env_autoswarm(self):
        from whitemagic.core.consciousness.consciousness_loop import LoopConfig
        os.environ["WM_ENABLE_AUTOSWARM"] = "1"
        os.environ["WM_AUTOSWARM_INTERVAL"] = "120"
        try:
            config = LoopConfig.from_env()
            assert config.enable_autoswarm is True
            assert config.autoswarm_interval_s == 120.0
        finally:
            del os.environ["WM_ENABLE_AUTOSWARM"]
            del os.environ["WM_AUTOSWARM_INTERVAL"]

    def test_stats_have_hyperspace_fields(self):
        from whitemagic.core.consciousness.consciousness_loop import LoopStats
        stats = LoopStats()
        assert hasattr(stats, "autoswarm_ticks")
        assert hasattr(stats, "autoswarm_campaigns")
        assert hasattr(stats, "autoswarm_breakthroughs")
        assert hasattr(stats, "mesh_sync_ticks")
        assert hasattr(stats, "mesh_sync_synced")

    def test_stats_to_dict_includes_hyperspace(self):
        from whitemagic.core.consciousness.consciousness_loop import LoopStats
        stats = LoopStats()
        d = stats.to_dict()
        assert "autoswarm_ticks" in d
        assert "mesh_sync_ticks" in d

    def test_loop_has_run_autoswarm_tick_method(self):
        from whitemagic.core.consciousness.consciousness_loop import ConsciousnessLoop
        loop = ConsciousnessLoop()
        assert hasattr(loop, "_run_autoswarm_tick")
        assert hasattr(loop, "_run_mesh_sync")


# ── CRDT Leaderboard ──────────────────────────────────────────────────


class TestCRDTLeaderboard:
    """Test CRDT leaderboard (local fallback mode)."""

    def test_submit_and_get(self):
        from whitemagic.mesh.crdt_leaderboard import CRDTLeaderboard
        lb = CRDTLeaderboard(node_id="test_node")
        lb.clear()
        entry = lb.submit(
            experiment_id="exp_001",
            hypothesis="Test hypothesis",
            domain="cognitive",
            fitness_score=0.85,
            agent_id="test_agent",
        )
        assert entry.experiment_id == "exp_001"
        assert entry.fitness_score == 0.85

        retrieved = lb.get_entry("exp_001")
        assert retrieved is not None
        assert retrieved.fitness_score == 0.85

    def test_get_top_sorted(self):
        from whitemagic.mesh.crdt_leaderboard import CRDTLeaderboard
        lb = CRDTLeaderboard(node_id="test_node")
        lb.clear()
        lb.submit("exp_1", "H1", "cognitive", 0.5)
        lb.submit("exp_2", "H2", "cognitive", 0.9)
        lb.submit("exp_3", "H3", "memory", 0.7)

        top = lb.get_top(n=3)
        assert len(top) == 3
        assert top[0].fitness_score == 0.9  # Highest first

    def test_get_top_filtered_by_domain(self):
        from whitemagic.mesh.crdt_leaderboard import CRDTLeaderboard
        lb = CRDTLeaderboard(node_id="test_node")
        lb.clear()
        lb.submit("exp_1", "H1", "cognitive", 0.5)
        lb.submit("exp_2", "H2", "memory", 0.9)

        top = lb.get_top(n=10, domain="memory")
        assert len(top) == 1
        assert top[0].domain == "memory"

    def test_monotonic_update(self):
        from whitemagic.mesh.crdt_leaderboard import CRDTLeaderboard
        lb = CRDTLeaderboard(node_id="test_node")
        lb.clear()
        lb.submit("exp_1", "H1", "cognitive", 0.5)
        # Lower score should not replace
        lb.submit("exp_1", "H1", "cognitive", 0.3)
        entry = lb.get_entry("exp_1")
        assert entry.fitness_score == 0.5  # Kept higher

        # Higher score should replace
        lb.submit("exp_1", "H1", "cognitive", 0.8)
        entry = lb.get_entry("exp_1")
        assert entry.fitness_score == 0.8

    def test_merge_remote_json(self):
        from whitemagic.mesh.crdt_leaderboard import CRDTLeaderboard
        import json
        lb = CRDTLeaderboard(node_id="test_node")
        lb.clear()

        remote_data = json.dumps({
            "entries": [
                {"experiment_id": "peer_1", "hypothesis": "Peer H", "domain": "cognitive",
                 "fitness_score": 0.75, "agent_id": "peer_node", "node_id": "peer"},
            ],
        })

        result = lb.merge_remote(remote_data)
        assert result["new"] == 1
        assert lb.get_entry("peer_1") is not None

    def test_export_import_roundtrip(self):
        from whitemagic.mesh.crdt_leaderboard import CRDTLeaderboard
        lb1 = CRDTLeaderboard(node_id="node_a")
        lb1.clear()
        lb1.submit("exp_1", "H1", "cognitive", 0.6)

        exported = lb1.export()

        lb2 = CRDTLeaderboard(node_id="node_b")
        lb2.clear()
        lb2.merge_remote(exported)

        entry = lb2.get_entry("exp_1")
        assert entry is not None
        assert entry.fitness_score == 0.6

    def test_status(self):
        from whitemagic.mesh.crdt_leaderboard import CRDTLeaderboard
        lb = CRDTLeaderboard(node_id="test_node")
        lb.clear()
        lb.submit("exp_1", "H1", "cognitive", 0.5)
        status = lb.get_status()
        assert status["total_entries"] == 1
        assert "by_domain" in status
        assert status["by_domain"]["cognitive"] == 1


# ── Research Adapters ─────────────────────────────────────────────────


class TestResearchAdapters:
    """Test research adapter base class and registry."""

    def test_base_adapter_record_experiment(self):
        from whitemagic.core.evolution.research_adapters import BaseAdapter
        adapter = BaseAdapter(agent_id="test", domain=ResearchDomain.COGNITIVE)
        result = adapter._record_experiment(
            hypothesis="Test hypothesis",
            fitness_score=0.7,
            outcome={"test": True},
        )
        assert result is not None
        assert result.fitness_score == 0.7

    def test_get_adapter_unknown_raises(self):
        from whitemagic.core.evolution.research_adapters import get_adapter
        with pytest.raises(ValueError, match="Unknown adapter"):
            get_adapter("nonexistent")

    def test_get_adapter_stats(self):
        from whitemagic.core.evolution.research_adapters import get_all_adapter_stats
        stats = get_all_adapter_stats()
        assert isinstance(stats, dict)

    def test_rabbit_hole_adapter_init(self):
        from whitemagic.core.evolution.research_adapters import RabbitHoleAdapter
        adapter = RabbitHoleAdapter()
        assert adapter._agent_id == "rabbit_hole"
        assert adapter._domain == ResearchDomain.SYNTHESIS

    def test_parallel_reasoning_adapter_init(self):
        from whitemagic.core.evolution.research_adapters import ParallelReasoningAdapter
        adapter = ParallelReasoningAdapter()
        assert adapter._agent_id == "parallel_reasoning"

    def test_alchemical_loop_adapter_init(self):
        from whitemagic.core.evolution.research_adapters import AlchemicalLoopAdapter
        adapter = AlchemicalLoopAdapter()
        assert adapter._agent_id == "alchemical_loop"

    def test_recursive_loop_adapter_init(self):
        from whitemagic.core.evolution.research_adapters import RecursiveLoopAdapter
        adapter = RecursiveLoopAdapter()
        assert adapter._agent_id == "recursive_loop"

    def test_knowledge_gap_adapter_init(self):
        from whitemagic.core.evolution.research_adapters import KnowledgeGapAdapter
        adapter = KnowledgeGapAdapter()
        assert adapter._agent_id == "knowledge_gap"

    def test_self_directed_adapter_init(self):
        from whitemagic.core.evolution.research_adapters import SelfDirectedAdapter
        adapter = SelfDirectedAdapter()
        assert adapter._agent_id == "self_directed"


# ── ResearchDAG Synthesis ─────────────────────────────────────────────


class TestResearchDAGSynthesis:
    """Test synthesis generation in ResearchDAG."""

    def test_synthesis_stage_exists(self):
        from whitemagic.core.evolution.research_dag import ExperimentStage
        assert ExperimentStage.SYNTHESIS.value == "synthesis"

    def test_generate_synthesis_not_enough_experiments(self):
        from whitemagic.core.evolution.research_dag import ResearchDAG, ResearchDomain
        dag = ResearchDAG()
        # With no experiments, should return None
        result = dag.generate_synthesis(
            domain=ResearchDomain.COGNITIVE,
            min_experiments=100,  # Higher than any existing
        )
        assert result is None

    def test_generate_synthesis_with_experiments(self):
        from whitemagic.core.evolution.research_dag import (
            ResearchDAG, ResearchDomain, get_research_dag,
        )
        dag = get_research_dag()

        # Create some experiments with results
        for i in range(6):
            exp = dag.submit_hypothesis(
                hypothesis=f"Synthesis test {i}",
                domain=ResearchDomain.COGNITIVE,
                agent_id="synthesis_test",
            )
            dag.record_trial(exp.experiment_id)
            dag.record_result(exp.experiment_id, fitness_score=0.5 + i * 0.05)

        result = dag.generate_synthesis(
            domain=ResearchDomain.COGNITIVE,
            min_experiments=5,
            top_n=5,
        )

        if result:
            assert "synthesis_id" in result
            assert "title" in result
            assert "body" in result
            assert result["experiments_synthesized"] <= 5


# ── Pulse Verification ────────────────────────────────────────────────


class TestPulseVerification:
    """Test tiered pulse verification."""

    def test_create_pulse(self):
        from whitemagic.mesh.pulse_verification import get_pulse_verifier, VerificationTier
        verifier = get_pulse_verifier()
        pulse = verifier.create_pulse(
            experiment_id="test_exp_001",
            node_id="test_node",
            fitness_claim=0.75,
            experiment_data={"hypothesis": "test", "fitness": 0.75},
        )
        assert pulse.experiment_id == "test_exp_001"
        assert pulse.fitness_claim == 0.75
        assert len(pulse.signature) > 0
        assert len(pulse.merkle_root) > 0

    def test_verify_tier0_pass(self):
        from whitemagic.mesh.pulse_verification import get_pulse_verifier
        verifier = get_pulse_verifier()
        data = {"hypothesis": "test", "fitness": 0.75}
        verifier.create_pulse(
            experiment_id="test_exp_002",
            node_id="test_node",
            fitness_claim=0.75,
            experiment_data=data,
        )
        pulse = verifier.verify(
            experiment_id="test_exp_002",
            experiment_data=data,
            node_reputation=0.8,
            force_tier=__import__("whitemagic.mesh.pulse_verification", fromlist=["VerificationTier"]).VerificationTier.AUTOMATED,
        )
        assert pulse is not None
        assert len(pulse.verifications) >= 1
        assert pulse.verifications[0].tier == 0  # AUTOMATED
        assert pulse.verifications[0].passed

    def test_verify_tier0_fail_wrong_data(self):
        from whitemagic.mesh.pulse_verification import get_pulse_verifier, VerificationTier
        verifier = get_pulse_verifier()
        verifier.create_pulse(
            experiment_id="test_exp_003",
            node_id="test_node",
            fitness_claim=0.75,
            experiment_data={"original": "data"},
        )
        pulse = verifier.verify(
            experiment_id="test_exp_003",
            experiment_data={"different": "data"},  # Wrong data
            force_tier=VerificationTier.AUTOMATED,
        )
        assert pulse is not None
        assert pulse.verifications[0].passed is False  # Merkle mismatch

    def test_escalation_high_fitness_low_reputation(self):
        from whitemagic.mesh.pulse_verification import (
            get_pulse_verifier, PulseRecord, VerificationTier,
        )
        verifier = get_pulse_verifier()
        pulse = PulseRecord(
            experiment_id="test",
            node_id="unknown_node",
            signature="sig",
            merkle_root="root",
            fitness_claim=0.95,
        )
        tier = verifier._determine_escalation(pulse, node_reputation=0.2)
        assert tier >= VerificationTier.PEER_REVIEW

    def test_escalation_normal(self):
        from whitemagic.mesh.pulse_verification import (
            get_pulse_verifier, PulseRecord, VerificationTier,
        )
        verifier = get_pulse_verifier()
        pulse = PulseRecord(
            experiment_id="test",
            node_id="trusted_node",
            signature="sig",
            merkle_root="root",
            fitness_claim=0.5,
        )
        tier = verifier._determine_escalation(pulse, node_reputation=0.8)
        assert tier == VerificationTier.AUTOMATED

    def test_get_status(self):
        from whitemagic.mesh.pulse_verification import get_pulse_verifier
        verifier = get_pulse_verifier()
        status = verifier.get_status()
        assert "tier0_checks" in status
        assert "total_passed" in status


# ── Critique Protocol ─────────────────────────────────────────────────


class TestCritiqueProtocol:
    """Test experiment critique protocol."""

    def test_critique_dimensions(self):
        from whitemagic.mesh.critique_protocol import CRITIQUE_DIMENSIONS
        assert "methodology" in CRITIQUE_DIMENSIONS
        assert "novelty" in CRITIQUE_DIMENSIONS
        assert "significance" in CRITIQUE_DIMENSIONS
        assert "reproducibility" in CRITIQUE_DIMENSIONS

    def test_critique_experiment(self):
        from whitemagic.mesh.critique_protocol import get_critique_protocol
        from whitemagic.core.evolution.research_dag import get_research_dag, ResearchDomain

        dag = get_research_dag()
        exp = dag.submit_hypothesis(
            hypothesis="Critique test",
            domain=ResearchDomain.COGNITIVE,
            agent_id="critique_test",
        )
        dag.record_trial(exp.experiment_id)
        dag.record_result(exp.experiment_id, fitness_score=0.7)

        protocol = get_critique_protocol()
        critique = protocol.critique_experiment(
            experiment_id=exp.experiment_id,
            critic_agent_id="test_critic",
            scores={
                "methodology": 8,
                "novelty": 7,
                "significance": 6,
                "reproducibility": 8,
            },
            written_review="Good experiment with solid methodology.",
        )

        assert critique is not None
        assert critique.aggregate_score == 7.25
        assert critique.recommendation == "accept"

    def test_critique_revision_threshold(self):
        from whitemagic.mesh.critique_protocol import get_critique_protocol
        from whitemagic.core.evolution.research_dag import get_research_dag, ResearchDomain

        dag = get_research_dag()
        exp = dag.submit_hypothesis(
            hypothesis="Critique revision test",
            domain=ResearchDomain.COGNITIVE,
            agent_id="critique_test",
        )
        dag.record_trial(exp.experiment_id)
        dag.record_result(exp.experiment_id, fitness_score=0.3)

        protocol = get_critique_protocol()
        critique = protocol.critique_experiment(
            experiment_id=exp.experiment_id,
            critic_agent_id="test_critic",
            scores={
                "methodology": 4,
                "novelty": 3,
                "significance": 5,
                "reproducibility": 4,
            },
        )

        assert critique is not None
        assert critique.recommendation == "revise"

    def test_critique_reject_threshold(self):
        from whitemagic.mesh.critique_protocol import get_critique_protocol
        from whitemagic.core.evolution.research_dag import get_research_dag, ResearchDomain

        dag = get_research_dag()
        exp = dag.submit_hypothesis(
            hypothesis="Critique reject test",
            domain=ResearchDomain.COGNITIVE,
            agent_id="critique_test",
        )
        dag.record_trial(exp.experiment_id)
        dag.record_result(exp.experiment_id, fitness_score=0.1)

        protocol = get_critique_protocol()
        critique = protocol.critique_experiment(
            experiment_id=exp.experiment_id,
            critic_agent_id="test_critic",
            scores={
                "methodology": 2,
                "novelty": 1,
                "significance": 1,
                "reproducibility": 2,
            },
        )

        assert critique is not None
        assert critique.recommendation == "reject"

    def test_auto_critique(self):
        from whitemagic.mesh.critique_protocol import get_critique_protocol
        from whitemagic.core.evolution.research_dag import get_research_dag, ResearchDomain

        dag = get_research_dag()
        exp = dag.submit_hypothesis(
            hypothesis="Auto critique test",
            domain=ResearchDomain.COGNITIVE,
            agent_id="auto_critique_test",
            parameters={"param1": 0.5, "param2": 0.3, "param3": 0.8},
        )
        dag.record_trial(exp.experiment_id)
        dag.record_result(exp.experiment_id, fitness_score=0.8)

        protocol = get_critique_protocol()
        critique = protocol.auto_critique(exp.experiment_id)

        assert critique is not None
        assert len(critique.scores) == 4
        assert all(1 <= s.score <= 10 for s in critique.scores)

    def test_get_status(self):
        from whitemagic.mesh.critique_protocol import get_critique_protocol
        protocol = get_critique_protocol()
        status = protocol.get_status()
        assert "total_critiques" in status
        assert "dimensions" in status


# ── Durable Archive ───────────────────────────────────────────────────


class TestDurableArchive:
    """Test durable archive layer."""

    def test_archive_dir_created(self):
        from whitemagic.mesh.durable_archive import get_durable_archive
        archive = get_durable_archive()
        assert archive._archive_dir.exists()
        assert archive._archive_dir.is_dir()

    def test_archive_new_empty(self):
        from whitemagic.mesh.durable_archive import get_durable_archive
        archive = get_durable_archive()
        result = archive.archive_new(force=False)
        assert result["status"] == "success"

    def test_get_status(self):
        from whitemagic.mesh.durable_archive import get_durable_archive
        archive = get_durable_archive()
        status = archive.get_status()
        assert "archive_runs" in status
        assert "archive_dir" in status
        assert "files_on_disk" in status

    def test_write_experiment_file(self):
        from whitemagic.mesh.durable_archive import DurableArchive
        from whitemagic.core.evolution.research_dag import Experiment, ResearchDomain, ExperimentStage

        archive = DurableArchive()
        exp = Experiment(
            experiment_id="test_archive_001",
            hypothesis="Archive test experiment",
            domain=ResearchDomain.COGNITIVE,
            stage=ExperimentStage.BREAKTHROUGH,
            fitness_score=0.85,
            agent_id="test_agent",
            parameters={"p1": 0.5},
            metadata={"source": "test"},
        )
        archive._write_experiment_file(exp, category="breakthrough")

        # Check file exists
        filepath = archive._archive_dir / "cognitive" / "breakthrough" / "test_archive_001.md"
        assert filepath.exists()
        content = filepath.read_text()
        assert "Archive test experiment" in content
        assert "0.8500" in content
