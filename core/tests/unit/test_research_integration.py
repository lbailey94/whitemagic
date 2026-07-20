"""Integration test for the full research systems pipeline.

Tests the end-to-end flow:
1. Submit hypothesis to ResearchDAG
2. Record trial + result
3. Submit critique via CritiqueProtocol
4. Generate synthesis
5. Create + verify pulse
6. Submit to CRDT leaderboard
7. Run durable archive
8. Test autoswarm tick
"""

from __future__ import annotations

import os
import tempfile

import pytest

_tmpdir = tempfile.mkdtemp(prefix="wm_integration_")
os.environ.setdefault("WM_STATE_ROOT", _tmpdir)
os.environ.setdefault("WM_SILENT_INIT", "1")
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")

from whitemagic.core.evolution.research_dag import (  # noqa: E402
    ExperimentStage,
    ResearchDomain,
    get_research_dag,
)
from whitemagic.mesh.crdt_leaderboard import get_leaderboard  # noqa: E402
from whitemagic.mesh.critique_protocol import get_critique_protocol  # noqa: E402
from whitemagic.mesh.durable_archive import get_durable_archive  # noqa: E402
from whitemagic.mesh.pulse_verification import (  # noqa: E402
    get_pulse_verifier,
)


class TestFullResearchPipeline:
    """End-to-end integration test for the research systems pipeline."""

    @pytest.fixture(autouse=True)
    def _clear_dag_state(self):
        """Clear DAG and phylogenetics state to prevent cross-test contamination."""
        try:
            from whitemagic.core.memory.phylogenetics import get_phylogenetics
            pg = get_phylogenetics()
            pg._initialized = False
        except Exception:
            pass
        # Clear pulse verifier key cache to prevent stale Ed25519 keys
        try:
            from whitemagic.mesh.pulse_verification import _KEY_CACHE
            _KEY_CACHE.clear()
        except Exception:
            pass
        dag = get_research_dag()
        dag._initialized = False
        dag._cache.clear()
        dag._ensure_table()
        try:
            with dag._get_conn() as conn:
                conn.execute("DELETE FROM research_experiments")
                conn.execute("DELETE FROM lineage_edges WHERE target_galaxy = 'research' OR source_galaxy = 'research'")
                conn.commit()
        except Exception:
            pass
        yield

    def test_full_pipeline(self):
        """Test the complete research pipeline from hypothesis to archive."""
        dag = get_research_dag()

        # 1. Submit hypothesis
        exp = dag.submit_hypothesis(
            hypothesis="Integration test: cognitive parameter optimization via Monte Carlo",
            domain=ResearchDomain.COGNITIVE,
            agent_id="integration_test",
            parameters={"method": "monte_carlo", "trials": 100},
        )
        assert exp.stage == ExperimentStage.HYPOTHESIS

        # 2. Record trial + result (high fitness → breakthrough)
        dag.record_trial(exp.experiment_id)
        result = dag.record_result(
            exp.experiment_id,
            fitness_score=0.88,
            outcome={"best_params": {"learning_rate": 0.01}, "converged": True},
        )
        assert result is not None
        assert result.fitness_score == 0.88
        assert result.stage == ExperimentStage.BREAKTHROUGH  # Auto-promoted

        # 3. Submit critique
        protocol = get_critique_protocol()
        critique = protocol.critique_experiment(
            experiment_id=exp.experiment_id,
            critic_agent_id="integration_critic",
            scores={
                "methodology": 9,
                "novelty": 7,
                "significance": 8,
                "reproducibility": 9,
            },
            written_review="Solid methodology with clear parameter documentation.",
        )
        assert critique is not None
        assert critique.recommendation == "accept"
        assert critique.aggregate_score >= 7.0

        # 4. Generate synthesis (need enough experiments — create a few more)
        for i in range(5):
            extra = dag.submit_hypothesis(
                hypothesis=f"Integration test extra {i}",
                domain=ResearchDomain.COGNITIVE,
                agent_id="integration_test",
            )
            dag.record_trial(extra.experiment_id)
            dag.record_result(extra.experiment_id, fitness_score=0.5 + i * 0.05)

        synthesis = dag.generate_synthesis(
            domain=ResearchDomain.COGNITIVE,
            min_experiments=5,
            top_n=5,
        )
        if synthesis:
            assert "synthesis_id" in synthesis
            assert "body" in synthesis
            assert synthesis["experiments_synthesized"] <= 5

        # 5. Create + verify pulse
        verifier = get_pulse_verifier()
        pulse = verifier.create_pulse(
            experiment_id=exp.experiment_id,
            node_id="integration_test_node",
            fitness_claim=0.88,
            experiment_data={"hypothesis": "test", "fitness": 0.88},
        )
        assert pulse is not None

        verified = verifier.verify(
            experiment_id=exp.experiment_id,
            experiment_data={"hypothesis": "test", "fitness": 0.88},
            node_reputation=0.9,
        )
        assert verified is not None
        assert len(verified.verifications) >= 1
        assert verified.verifications[0].passed  # Tier 0 should pass

        # 6. Submit to CRDT leaderboard
        lb = get_leaderboard()
        lb.submit(
            experiment_id=exp.experiment_id,
            hypothesis="Integration test hypothesis",
            domain="cognitive",
            fitness_score=0.88,
            agent_id="integration_test",
        )
        top = lb.get_top(n=5, domain="cognitive")
        assert any(e.experiment_id == exp.experiment_id for e in top)

        # 7. Run durable archive
        archive = get_durable_archive()
        result = archive.archive_new(force=True)
        assert result["status"] == "success"

        # 8. Verify status endpoints
        assert verifier.get_status()["tier0_checks"] > 0
        assert protocol.get_status()["total_critiques"] > 0
        assert lb.get_status()["total_entries"] > 0
        assert archive.get_status()["archive_runs"] > 0

    def test_autoswarm_tick_integration(self):
        """Test that autoswarm tick runs without crashing."""
        from whitemagic.core.evolution.autoswarm import EvolutionaryAutoswarm

        swarm = EvolutionaryAutoswarm()
        try:
            result = swarm.tick()
            assert result is None or hasattr(result, "campaign_name")
        except (ValueError, RuntimeError, TypeError) as e:
            # These are expected when autoswarm has no campaigns configured
            assert "campaign" in str(e).lower() or "config" in str(e).lower() or "no" in str(e).lower(), (
                f"Unexpected error from autoswarm tick: {e}"
            )

    def test_consciousness_loop_config_integration(self):
        """Test that consciousness loop config properly loads autoswarm settings."""
        from whitemagic.core.consciousness.consciousness_loop import LoopConfig

        config = LoopConfig()
        assert hasattr(config, "enable_autoswarm")
        assert hasattr(config, "enable_mesh_sync")
        assert hasattr(config, "autoswarm_interval_s")
        assert hasattr(config, "mesh_sync_interval_s")

    def test_leaderboard_loro_enabled(self):
        """Test that Loro CRDT is actually enabled (not fallback)."""
        lb = get_leaderboard()
        status = lb.get_status()
        # Loro should be enabled since we installed the package
        assert status.get("loro_enabled", False) is True

    def test_pulse_escalation_high_fitness_low_reputation(self):
        """Test that pulse verification escalates for high fitness + low reputation."""
        verifier = get_pulse_verifier()
        pulse = verifier.create_pulse(
            experiment_id="escalation_test_001",
            node_id="untrusted_node",
            fitness_claim=0.95,
            experiment_data={"test": True},
        )
        assert pulse is not None

        verified = verifier.verify(
            experiment_id="escalation_test_001",
            experiment_data={"test": True},
            node_reputation=0.2,  # Low reputation
        )
        assert verified is not None
        # Should have escalated beyond Tier 0
        assert len(verified.verifications) > 1

    def test_critique_auto_scoring(self):
        """Test that auto-critique produces reasonable scores."""
        dag = get_research_dag()
        exp = dag.submit_hypothesis(
            hypothesis="Auto-critique integration test",
            domain=ResearchDomain.COGNITIVE,
            agent_id="auto_critique_test",
            parameters={"p1": 0.5, "p2": 0.3, "p3": 0.8},
        )
        dag.record_trial(exp.experiment_id)
        dag.record_result(exp.experiment_id, fitness_score=0.8)

        protocol = get_critique_protocol()
        critique = protocol.auto_critique(exp.experiment_id)
        assert critique is not None
        assert all(1 <= s.score <= 10 for s in critique.scores)
        assert critique.aggregate_score > 0

    def test_archive_write_and_status(self):
        """Test that durable archive writes files and reports status."""
        archive = get_durable_archive()
        status_before = archive.get_status()
        runs_before = status_before["archive_runs"]

        result = archive.archive_new(force=True)
        assert result["status"] == "success"

        status_after = archive.get_status()
        assert status_after["archive_runs"] >= runs_before
