"""Tests for Objective M — Elixir Actor-Based Concurrent Outcome Processing."""
from __future__ import annotations

from whitemagic.core.evolution.actor_outcome import (
    ActorSupervisor,
    HypothesisActor,
)


class TestHypothesisActor:
    def test_initial_state(self):
        actor = HypothesisActor(hypothesis_id="h1", prior=0.5)
        assert actor.posterior == 0.5
        assert actor.outcome_count == 0

    def test_handle_outcome_success(self):
        actor = HypothesisActor(hypothesis_id="h1", prior=0.5)
        actor.handle_outcome(success=True)
        assert actor.outcome_count == 1
        assert actor.success_count == 1
        assert actor.posterior > 0.5  # Beta(2,1) mean = 2/3

    def test_handle_outcome_failure(self):
        actor = HypothesisActor(hypothesis_id="h1", prior=0.5)
        actor.handle_outcome(success=False)
        assert actor.outcome_count == 1
        assert actor.posterior < 0.5  # Beta(1,2) mean = 1/3

    def test_handle_query(self):
        actor = HypothesisActor(hypothesis_id="h1", prior=0.7)
        assert actor.handle_query("prior") == 0.7
        assert actor.handle_query("posterior") == 0.5

    def test_handle_transfer(self):
        actor_a = HypothesisActor(hypothesis_id="h1", prior=0.8, alpha=5, beta=1)
        actor_b = HypothesisActor(hypothesis_id="h2", prior=0.3, alpha=1, beta=5)
        actor_b.handle_transfer(actor_a, weight=0.5)
        # Blended prior should be between 0.3 and 0.8
        assert 0.3 < actor_b.prior < 0.8

    def test_mailbox(self):
        actor = HypothesisActor(hypothesis_id="h1")
        actor.send(("outcome", (True, 0.5)))
        actor.send(("query", "posterior"))
        results = actor.process_mailbox()
        assert len(results) == 2
        assert actor.outcome_count == 1


class TestActorSupervisor:
    def test_start_actor(self):
        sup = ActorSupervisor()
        actor = sup.start_actor("h1", prior=0.6)
        assert actor.prior == 0.6
        assert sup.get_actor("h1") is not None

    def test_send_outcome(self):
        sup = ActorSupervisor()
        sup.start_actor("h1")
        result = sup.send_outcome("h1", success=True)
        assert result is not None
        assert result["outcome_count"] == 1

    def test_send_outcome_nonexistent(self):
        sup = ActorSupervisor()
        assert sup.send_outcome("h1", success=True) is None

    def test_broadcast(self):
        sup = ActorSupervisor()
        sup.start_actor("h1")
        sup.start_actor("h2")
        results = sup.broadcast_outcome(success=True)
        assert len(results) == 2
        assert "h1" in results
        assert "h2" in results

    def test_transfer_belief(self):
        sup = ActorSupervisor()
        sup.start_actor("h1", prior=0.8)
        sup.start_actor("h2", prior=0.3)
        assert sup.transfer_belief("h1", "h2", weight=0.5) is True
        actor_b = sup.get_actor("h2")
        assert actor_b.prior > 0.3  # Should have moved toward h1's prior

    def test_transfer_nonexistent(self):
        sup = ActorSupervisor()
        assert sup.transfer_belief("h1", "h2") is False

    def test_restart_actor(self):
        sup = ActorSupervisor()
        sup.start_actor("h1", prior=0.7)
        sup.mark_failed("h1")
        assert sup.get_active_count() == 0
        sup.restart_actor("h1")
        assert sup.get_active_count() == 1
        # Prior should be preserved
        assert sup.get_actor("h1").prior == 0.7

    def test_get_all_posteriors(self):
        sup = ActorSupervisor()
        sup.start_actor("h1")
        sup.start_actor("h2")
        sup.send_outcome("h1", success=True)
        posteriors = sup.get_all_posteriors()
        assert "h1" in posteriors
        assert "h2" in posteriors
        assert posteriors["h1"] != posteriors["h2"]

    def test_stats(self):
        sup = ActorSupervisor()
        sup.start_actor("h1")
        sup.start_actor("h2")
        sup.send_outcome("h1", success=True)
        stats = sup.get_stats()
        assert stats["total_actors"] == 2
        assert stats["total_outcomes"] == 1
