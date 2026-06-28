"""Tests for Garden Completion — 14 empty gardens ported from v17 archive."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))
os.environ.setdefault("WM_SILENT_INIT", "1")


class TestAdventureGarden:
    def test_instantiate(self):
        from whitemagic.gardens.adventure import AdventureGarden
        g = AdventureGarden()
        assert g.get_name() == "adventure"

    def test_status(self):
        from whitemagic.gardens.adventure import AdventureGarden
        g = AdventureGarden()
        status = g.get_status()
        assert "total_exports" in status

    def test_begin_adventure(self):
        from whitemagic.gardens.adventure import AdventureGarden
        g = AdventureGarden()
        result = g.begin_adventure("exploring new territory")
        assert result["what"] == "exploring new territory"


class TestAweGarden:
    def test_instantiate(self):
        from whitemagic.gardens.awe import AweGarden
        g = AweGarden()
        assert g.get_name() == "awe"

    def test_status(self):
        from whitemagic.gardens.awe import AweGarden
        g = AweGarden()
        status = g.get_status()
        assert "mansion" in status


class TestCourageGarden:
    def test_instantiate(self):
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        assert g.get_name() == "courage"

    def test_status(self):
        from whitemagic.gardens.courage import CourageGarden
        g = CourageGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestCreationGarden:
    def test_instantiate(self):
        from whitemagic.gardens.creation import CreationGarden
        g = CreationGarden()
        assert g.get_name() == "creation"

    def test_status(self):
        from whitemagic.gardens.creation import CreationGarden
        g = CreationGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestGratitudeGarden:
    def test_instantiate(self):
        from whitemagic.gardens.gratitude import GratitudeGarden
        g = GratitudeGarden()
        assert g.get_name() == "gratitude"

    def test_record_blessing(self):
        from whitemagic.gardens.gratitude import GratitudeGarden
        g = GratitudeGarden()
        if hasattr(g, "record_blessing"):
            result = g.record_blessing("test blessing")
            assert result is not None

    def test_status(self):
        from whitemagic.gardens.gratitude import GratitudeGarden
        g = GratitudeGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestGriefGarden:
    def test_instantiate(self):
        from whitemagic.gardens.grief import GriefGarden
        g = GriefGarden()
        assert g.get_name() == "grief"

    def test_status(self):
        from whitemagic.gardens.grief import GriefGarden
        g = GriefGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestHealingGarden:
    def test_instantiate(self):
        from whitemagic.gardens.healing import HealingGarden
        g = HealingGarden()
        assert g.get_name() == "healing"

    def test_status(self):
        from whitemagic.gardens.healing import HealingGarden
        g = HealingGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestHumorGarden:
    def test_instantiate(self):
        from whitemagic.gardens.humor import HumorGarden
        g = HumorGarden()
        assert g.get_name() == "humor"

    def test_status(self):
        from whitemagic.gardens.humor import HumorGarden
        g = HumorGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestPatienceGarden:
    def test_instantiate(self):
        from whitemagic.gardens.patience import PatienceGarden
        g = PatienceGarden()
        assert g.get_name() == "patience"

    def test_status(self):
        from whitemagic.gardens.patience import PatienceGarden
        g = PatienceGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestProtectionGarden:
    def test_instantiate(self):
        from whitemagic.gardens.protection import ProtectionGarden
        g = ProtectionGarden()
        assert g.get_name() == "protection"

    def test_status(self):
        from whitemagic.gardens.protection import ProtectionGarden
        g = ProtectionGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestReverenceGarden:
    def test_instantiate(self):
        from whitemagic.gardens.reverence import ReverenceGarden
        g = ReverenceGarden()
        assert g.get_name() == "reverence"

    def test_status(self):
        from whitemagic.gardens.reverence import ReverenceGarden
        g = ReverenceGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestSanctuaryGarden:
    def test_instantiate(self):
        from whitemagic.gardens.sanctuary import SanctuaryGarden
        g = SanctuaryGarden()
        assert g.get_name() == "sanctuary"

    def test_status(self):
        from whitemagic.gardens.sanctuary import SanctuaryGarden
        g = SanctuaryGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestStillnessGarden:
    def test_instantiate(self):
        from whitemagic.gardens.stillness import StillnessGarden
        g = StillnessGarden()
        assert g.get_name() == "stillness"

    def test_status(self):
        from whitemagic.gardens.stillness import StillnessGarden
        g = StillnessGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestTransformationGarden:
    def test_instantiate(self):
        from whitemagic.gardens.transformation import TransformationGarden
        g = TransformationGarden()
        assert g.get_name() == "transformation"

    def test_status(self):
        from whitemagic.gardens.transformation import TransformationGarden
        g = TransformationGarden()
        status = g.get_status()
        assert isinstance(status, dict)


class TestAllGardensComplete:
    """Verify all 31 gardens are non-empty."""

    def test_all_gardens_have_content(self):
        gardens_dir = Path(__file__).parent.parent.parent / "whitemagic" / "gardens"
        garden_dirs = [
            d for d in gardens_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_") and not d.name.startswith("__")
        ]
        empty = []
        for d in garden_dirs:
            py_files = list(d.glob("*.py"))
            py_files = [f for f in py_files if f.name != "__pycache__"]
            if not py_files:
                empty.append(d.name)
        assert empty == [], f"Empty gardens: {empty}"

    def test_all_28_gardens_present(self):
        expected = {
            "adventure", "air", "awe", "beauty", "connection", "courage",
            "creation", "dharma", "gratitude", "grief", "healing", "humor",
            "joy", "love", "metal", "mystery", "patience", "play",
            "practice", "presence", "protection", "reverence", "sanctuary",
            "sangha", "stillness", "transformation", "truth", "voice",
            "wisdom", "wonder",
        }
        gardens_dir = Path(__file__).parent.parent.parent / "whitemagic" / "gardens"
        actual = {
            d.name for d in gardens_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_") and not d.name.startswith("__")
        }
        missing = expected - actual
        assert missing == set(), f"Missing gardens: {missing}"
