"""Tests for Batch 3: Resonance & Synergies."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestEnhancedGanYingBus:
    """Test enhanced GanYing bus."""

    def test_init(self):
        from whitemagic.core.resonance.gan_ying_enhanced_recovered import (
            EnhancedGanYingBus,
        )

        bus = EnhancedGanYingBus()
        assert bus.event_count == 0
        assert bus.listener_count() == 0

    def test_emit_and_listen(self):
        from whitemagic.core.resonance.gan_ying_enhanced_recovered import (
            EnhancedGanYingBus,
        )

        bus = EnhancedGanYingBus()
        received = []
        bus.on("test_event", lambda e: received.append(e))
        bus.emit(source="test", event_type="test_event", data={"x": 1})
        assert len(received) == 1
        assert received[0]["data"]["x"] == 1
        assert bus.event_count == 1

    def test_cascade(self):
        from whitemagic.core.resonance.gan_ying_enhanced_recovered import (
            CascadeTrigger,
            EnhancedGanYingBus,
            ExtendedEventType,
        )

        bus = EnhancedGanYingBus()
        received = []
        bus.on(ExtendedEventType.JOY_TRIGGERED.value, lambda e: received.append(e))
        bus.add_cascade(
            CascadeTrigger(
                trigger_event=ExtendedEventType.BEAUTY_DETECTED,
                target_events=[ExtendedEventType.JOY_TRIGGERED],
                strength=0.8,
            )
        )
        bus.emit(source="test", event_type=ExtendedEventType.BEAUTY_DETECTED.value)
        assert len(received) == 1

    def test_recent_events(self):
        from whitemagic.core.resonance.gan_ying_enhanced_recovered import (
            EnhancedGanYingBus,
        )

        bus = EnhancedGanYingBus()
        bus.emit(source="test", event_type="e1")
        bus.emit(source="test", event_type="e2")
        recent = bus.recent_events()
        assert len(recent) == 2


class TestCascadeProtocols:
    """Test cascade protocols."""

    def test_init_all(self):
        from whitemagic.core.resonance.cascade_protocols_recovered import (
            init_all_cascades,
        )
        from whitemagic.core.resonance.gan_ying_enhanced_recovered import (
            get_enhanced_bus,
        )

        init_all_cascades()
        bus = get_enhanced_bus()
        assert len(bus._cascades) > 0


class TestPatternDreamBridge:
    """Test pattern-dream bridge."""

    def test_queue_and_process(self, tmp_path):
        from whitemagic.synergies.pattern_dream_bridge import PatternDreamBridge

        bridge = PatternDreamBridge(data_dir=tmp_path)
        bridge.queue_pattern({"type": "test", "pattern": "p1"})
        bridge.queue_pattern({"type": "test", "pattern": "p2"})
        syntheses = bridge.process_queue()
        assert len(syntheses) >= 1

    def test_summary(self, tmp_path):
        from whitemagic.synergies.pattern_dream_bridge import PatternDreamBridge

        bridge = PatternDreamBridge(data_dir=tmp_path)
        summary = bridge.summary()
        assert "pending_patterns" in summary


class TestSecurityHomeostasisLink:
    """Test security-homeostasis link."""

    def test_process_threats(self):
        from whitemagic.synergies.security_homeostasis_link import (
            SecurityHomeostasisLink,
        )

        link = SecurityHomeostasisLink()
        actions = link.process_threats()
        assert isinstance(actions, list)

    def test_summary(self):
        from whitemagic.synergies.security_homeostasis_link import (
            SecurityHomeostasisLink,
        )

        link = SecurityHomeostasisLink()
        summary = link.summary()
        assert "total_linked" in summary


class TestCLISuggestionLearner:
    """Test CLI suggestion learner."""

    def test_record_and_suggest(self, tmp_path):
        from whitemagic.synergies.cli_suggestion_learner import CLISuggestionLearner

        learner = CLISuggestionLearner(data_dir=tmp_path)
        learner.record("wm status")
        learner.record("wm status")
        learner.record("wm dream")
        suggestions = learner.suggest()
        assert len(suggestions) > 0
        assert suggestions[0]["command"] == "wm status"

    def test_suggest_next(self, tmp_path):
        from whitemagic.synergies.cli_suggestion_learner import CLISuggestionLearner

        learner = CLISuggestionLearner(data_dir=tmp_path)
        learner.record("wm status", sequence=["wm status", "wm dream"])
        learner.record("wm status", sequence=["wm status", "wm coherence"])
        next_cmds = learner.suggest_next("wm status")
        assert len(next_cmds) > 0

    def test_summary(self, tmp_path):
        from whitemagic.synergies.cli_suggestion_learner import CLISuggestionLearner

        learner = CLISuggestionLearner(data_dir=tmp_path)
        summary = learner.summary()
        assert "unique_commands" in summary
