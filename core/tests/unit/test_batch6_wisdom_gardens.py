"""Tests for Batch 6: Wisdom & Gardens."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestWuXing:
    """Test Wu Xing five-element system."""

    def test_balance(self):
        from whitemagic.wisdom.wu_xing import WuXingSystem
        system = WuXingSystem()
        balance = system.assess()
        assert balance.is_balanced() is True  # All 0.5

    def test_nourish(self):
        from whitemagic.wisdom.wu_xing import Element, WuXingSystem
        system = WuXingSystem()
        system.nourish(Element.WATER)
        balance = system.assess()
        assert balance.water > 0.5

    def test_dominant(self):
        from whitemagic.wisdom.wu_xing import Element, WuXingSystem
        system = WuXingSystem()
        system.nourish(Element.FIRE)
        system.nourish(Element.FIRE)
        assert system.balance.dominant() == Element.FIRE

    def test_recommend(self):
        from whitemagic.wisdom.wu_xing import WuXingSystem
        system = WuXingSystem()
        rec = system.recommend()
        assert "dominant" in rec
        assert "deficient" in rec
        assert "recommendation" in rec

    def test_summary(self):
        from whitemagic.wisdom.wu_xing import WuXingSystem
        system = WuXingSystem()
        summary = system.summary()
        assert "balance" in summary
        assert "is_balanced" in summary


class TestIChing:
    """Test I Ching oracle system."""

    def test_cast(self):
        from whitemagic.wisdom.i_ching import IChingSystem
        system = IChingSystem()
        hexagram = system.cast()
        assert 1 <= hexagram.number <= 64
        assert len(hexagram.lines) == 6

    def test_interpret(self):
        from whitemagic.wisdom.i_ching import Hexagram, IChingSystem
        system = IChingSystem()
        hexagram = Hexagram(
            number=1,
            lines=[1, 1, 1, 1, 1, 1],
            lower_trigram="qian",
            upper_trigram="qian",
            name="Qian",
            judgment="The Creative",
        )
        interpretation = system.interpret(hexagram)
        assert interpretation["number"] == 1
        assert "lower" in interpretation
        assert "upper" in interpretation

    def test_consult(self):
        from whitemagic.wisdom.i_ching import IChingSystem
        system = IChingSystem()
        result = system.consult("Should I proceed?")
        assert result["question"] == "Should I proceed?"
        assert "name" in result


class TestIChingAdvisor:
    """Test I Ching advisor."""

    def test_advise(self):
        from whitemagic.wisdom.i_ching_advisor import IChingAdvisor
        advisor = IChingAdvisor()
        result = advisor.advise("What should I do?")
        assert "advice" in result
        assert len(result["advice"]) > 0

    def test_history(self):
        from whitemagic.wisdom.i_ching_advisor import IChingAdvisor
        advisor = IChingAdvisor()
        advisor.advise("Question 1")
        advisor.advise("Question 2")
        history = advisor.history()
        assert len(history) == 2

    def test_summary(self):
        from whitemagic.wisdom.i_ching_advisor import IChingAdvisor
        advisor = IChingAdvisor()
        summary = advisor.summary()
        assert "total_consultations" in summary


class TestWisdomAutoIngester:
    """Test wisdom auto-ingester."""

    def test_ingest(self, tmp_path):
        from whitemagic.wisdom.auto_ingester import WisdomAutoIngester
        ingester = WisdomAutoIngester(data_dir=tmp_path)
        entry = ingester.ingest("I learned something valuable", source="test")
        assert entry["content"] == "I learned something valuable"

    def test_search(self, tmp_path):
        from whitemagic.wisdom.auto_ingester import WisdomAutoIngester
        ingester = WisdomAutoIngester(data_dir=tmp_path)
        ingester.ingest("I discovered a pattern", tags=["test"])
        ingester.ingest("Random content")
        results = ingester.search("discovered")
        assert len(results) == 1

    def test_summary(self, tmp_path):
        from whitemagic.wisdom.auto_ingester import WisdomAutoIngester
        ingester = WisdomAutoIngester(data_dir=tmp_path)
        ingester.ingest("content", tags=["a"])
        summary = ingester.summary()
        assert summary["total_ingested"] == 1


class TestGardenSynthesis:
    """Test garden synthesis."""

    def test_register_and_synthesize(self):
        from whitemagic.gardens.synthesis import GardenSynthesis
        synth = GardenSynthesis()
        synth.register_garden("test", type("G", (), {"summary": lambda self: {"ok": True}})())
        result = synth.synthesize()
        assert result["gardens_synthesized"] == 1
        assert result["dominant_theme"] == "test"

    def test_summary(self):
        from whitemagic.gardens.synthesis import GardenSynthesis
        synth = GardenSynthesis()
        summary = synth.summary()
        assert "registered_gardens" in summary


class TestJoyCore:
    """Test joy garden core."""

    def test_detect_joy(self):
        from whitemagic.gardens.joy.core import JoyCore
        core = JoyCore()
        level = core.detect_joy("I'm so happy and grateful for this!")
        assert level > 0

    def test_detect_no_joy(self):
        from whitemagic.gardens.joy.core import JoyCore
        core = JoyCore()
        level = core.detect_joy("The system encountered an error")
        assert level == 0.0

    def test_record_and_baseline(self, tmp_path):
        from whitemagic.gardens.joy.core import JoyCore
        core = JoyCore(data_dir=tmp_path)
        core.record_joy("I'm delighted and happy and grateful and joyful!", source="test")
        assert core.baseline > 0.5

    def test_summary(self, tmp_path):
        from whitemagic.gardens.joy.core import JoyCore
        core = JoyCore(data_dir=tmp_path)
        summary = core.summary()
        assert "total_events" in summary
        assert "baseline" in summary


class TestCelebrationPractice:
    """Test celebration practice."""

    def test_celebrate(self, tmp_path):
        from whitemagic.gardens.joy.celebration_practice import CelebrationPractice
        practice = CelebrationPractice(data_dir=tmp_path)
        entry = practice.celebrate("Finished a project", "Hard work paid off")
        assert entry["what"] == "Finished a project"

    def test_streak(self, tmp_path):
        from whitemagic.gardens.joy.celebration_practice import CelebrationPractice
        practice = CelebrationPractice(data_dir=tmp_path)
        practice.celebrate("a")
        practice.celebrate("b")
        assert practice.streak == 2

    def test_suggest(self):
        from whitemagic.gardens.joy.celebration_practice import CelebrationPractice
        practice = CelebrationPractice()
        suggestion = practice.suggest_celebration()
        assert len(suggestion) > 0

    def test_summary(self, tmp_path):
        from whitemagic.gardens.joy.celebration_practice import CelebrationPractice
        practice = CelebrationPractice(data_dir=tmp_path)
        practice.celebrate("test")
        summary = practice.summary()
        assert summary["total_celebrations"] == 1
