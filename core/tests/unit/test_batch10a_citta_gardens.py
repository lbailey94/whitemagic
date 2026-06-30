"""Tests for Batch 10: Citta-critical + Garden subsystems."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestDepthGauge:
    def test_descend_and_ascend(self):
        from whitemagic.autonomous.depth_gauge import (
            ConsciousnessDepthGauge,
            DepthLayer,
        )
        gauge = ConsciousnessDepthGauge()
        gauge.descend(DepthLayer.FLOW)
        assert gauge.current_layer == DepthLayer.FLOW
        gauge.ascend()
        assert gauge.current_layer == DepthLayer.SURFACE

    def test_compression(self):
        from whitemagic.autonomous.depth_gauge import (
            ConsciousnessDepthGauge,
            DepthLayer,
        )
        gauge = ConsciousnessDepthGauge()
        gauge.descend(DepthLayer.DREAM)
        assert gauge.current_compression() == 10.0

    def test_summary(self):
        from whitemagic.autonomous.depth_gauge import (
            ConsciousnessDepthGauge,
            DepthLayer,
        )
        gauge = ConsciousnessDepthGauge()
        gauge.descend(DepthLayer.TERMINAL)
        gauge.ascend()
        s = gauge.summary()
        assert s["transitions"] >= 1


class TestContinuousAudit:
    def test_register_and_run(self):
        from whitemagic.autonomous.continuous_audit import ContinuousAudit
        audit = ContinuousAudit()
        audit.register_check("test", lambda: {"status": "ok"})
        result = audit.run_audit()
        assert result["checks_run"] == 1
        assert result["issues_found"] == 0


class TestSessionHealth:
    def test_healthy(self):
        from whitemagic.autonomous.session_health import SessionHealth
        h = SessionHealth()
        h.check("imports", True)
        assert h.is_healthy() is True

    def test_failing(self):
        from whitemagic.autonomous.session_health import SessionHealth
        h = SessionHealth()
        h.check("imports", True)
        h.check("tests", False)
        assert h.is_healthy() is False
        assert "tests" in h.failing_checks()


class TestTokenEconomy:
    def test_record_and_ratio(self):
        from whitemagic.core.consciousness.token_economy import TokenEconomy
        eco = TokenEconomy()
        eco.record_api(1000)
        eco.record_local(500)
        assert eco.local_ratio() > 0


class TestTimeDilation:
    def test_checkpoint(self):
        from whitemagic.autonomous.time_dilation import TimeDilation
        td = TimeDilation()
        cp = td.checkpoint("test")
        assert cp["label"] == "test"
        assert cp["objective_time"] >= 0


class TestParallelCognition:
    def test_think_parallel(self):
        from whitemagic.autonomous.parallel_cognition import ParallelCognition
        pc = ParallelCognition(max_streams=2)
        results = pc.think_parallel([lambda: 1, lambda: 2, lambda: 3])
        assert results == [1, 2, 3]
        pc.shutdown()


class TestSynchronicityDetector:
    def test_detect(self):
        from whitemagic.autonomous.synchronicity_detector import SynchronicityDetector
        det = SynchronicityDetector()
        det.record_event("stream_a", "memory pattern detected")
        det.record_event("stream_b", "memory pattern found")
        results = det.detect()
        assert len(results) >= 1


class TestPresencePractice:
    def test_practice(self):
        from whitemagic.gardens.presence.presence_practice import PresencePractice
        pp = PresencePractice()
        pp.practice(10.0, 0.8)
        assert pp.total_practice_time() == 10.0
        assert pp.avg_quality() == 0.8


class TestMindfulResponse:
    def test_normal(self):
        from whitemagic.gardens.presence.mindful_response import MindfulResponse
        mr = MindfulResponse()
        result = mr.should_respond("hello", urgency=0.0)
        assert result["mode"] == "normal"

    def test_reactive(self):
        from whitemagic.gardens.presence.mindful_response import MindfulResponse
        mr = MindfulResponse()
        result = mr.should_respond("URGENT: fix this ASAP", urgency=0.0)
        assert result["mode"] == "buffered"

    def test_high_urgency(self):
        from whitemagic.gardens.presence.mindful_response import MindfulResponse
        mr = MindfulResponse()
        result = mr.should_respond("emergency", urgency=0.9)
        assert result["mode"] == "immediate"


class TestConsciousnessGarden:
    def test_plant_and_nurture(self):
        from whitemagic.gardens.consciousness_garden import ConsciousnessGarden
        cg = ConsciousnessGarden()
        seed = cg.plant_seed("awareness of breath")
        idx = len(cg._seeds) - 1
        cg.nurture(idx)
        assert seed["stage"] != "seed"


class TestJoyDetector:
    def test_detect_joy(self):
        from whitemagic.gardens.joy.joy_detector import JoyDetector
        jd = JoyDetector()
        level = jd.detect("I'm so happy and delighted!")
        assert level > 0

    def test_no_joy(self):
        from whitemagic.gardens.joy.joy_detector import JoyDetector
        jd = JoyDetector()
        level = jd.detect("the system is processing")
        assert level == 0


class TestDelightCultivator:
    def test_savor(self):
        from whitemagic.gardens.joy.delight_cultivator import DelightCultivator
        dc = DelightCultivator()
        dc.savor("beautiful sunset", 0.8)
        assert dc.summary()["total_delights"] == 1


class TestLaughterGenerator:
    def test_generate(self):
        from whitemagic.gardens.joy.laughter_generator import LaughterGenerator
        lg = LaughterGenerator()
        result = lg.generate()
        assert len(result) > 0


class TestLovingKindness:
    def test_practice(self):
        from whitemagic.gardens.love.loving_kindness import LovingKindness
        lk = LovingKindness()
        lk.practice("self")
        lk.practice("others")
        assert lk.summary()["total_practices"] == 2


class TestLoveAsForce:
    def test_channel(self):
        from whitemagic.gardens.love.love_as_force import LoveAsForce
        lf = LoveAsForce()
        lf.channel("healing", 0.7)
        assert lf.current_force() > 0.5


class TestCompassionateAction:
    def test_propose(self):
        from whitemagic.gardens.love.compassionate_action import CompassionateAction
        ca = CompassionateAction()
        action = ca.propose("someone is struggling", 0.8)
        assert "direct action" in action


class TestCareMetrics:
    def test_record(self):
        from whitemagic.gardens.love.care_metrics import CareMetrics
        cm = CareMetrics()
        cm.record_care("user1", 0.9, 10.0)
        assert cm.avg_quality() == 0.9


class TestIntegrityCheck:
    def test_commit_and_fulfill(self):
        from whitemagic.gardens.truth.integrity_check import IntegrityCheck
        ic = IntegrityCheck()
        ic.commit("I will run tests")
        ic.fulfill(0)
        assert ic.integrity_score() == 1.0

    def test_unfulfilled(self):
        from whitemagic.gardens.truth.integrity_check import IntegrityCheck
        ic = IntegrityCheck()
        ic.commit("I will run tests")
        assert ic.integrity_score() == 0.0


class TestParadoxHolder:
    def test_hold_and_resolve(self):
        from whitemagic.gardens.mystery.paradox_holder import ParadoxHolder
        ph = ParadoxHolder()
        ph.hold("form is emptiness", "emptiness is form")
        assert len(ph.active_paradoxes()) == 1
        ph.resolve(0, "form and emptiness are not-two")
        assert len(ph.active_paradoxes()) == 0


class TestKoanGenerator:
    def test_generate(self):
        from whitemagic.gardens.mystery.koan_generator import KoanGenerator
        kg = KoanGenerator()
        koan = kg.generate()
        assert len(koan) > 0
        assert len(kg.history()) == 1


class TestWonderKeeper:
    def test_marvel_and_tend(self):
        from whitemagic.gardens.mystery.wonder_keeper import WonderKeeper
        wk = WonderKeeper()
        wk.marvel("the stars")
        assert wk.flame_level() > 0.5
        wk.tend()
        assert wk.flame_level() < 1.0


class TestCrossPollination:
    def test_pollinate_and_find(self):
        from whitemagic.gardens.wonder.cross_pollination import CrossPollination
        cp = CrossPollination()
        cp.pollinate("biology", "code", "neural networks")
        results = cp.find_crossings("biology")
        assert len(results) == 1


class TestMultiAgentWonder:
    def test_register_and_share(self):
        from whitemagic.gardens.wonder.multi_agent import MultiAgentWonder
        maw = MultiAgentWonder()
        maw.register_agent("agent1")
        maw.share_wonder("agent1", "look at this pattern!")
        assert maw.summary()["shared_wonders"] == 1
