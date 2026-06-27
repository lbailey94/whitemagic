"""Tests for Batch 2: Defense & Immune systems."""

from __future__ import annotations

import os
import tempfile
import time
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestThreatDetector:
    """Test immune threat detection."""

    def test_scan(self):
        from whitemagic.immune.detector import ThreatDetector
        detector = ThreatDetector()
        threats = detector.scan()
        assert isinstance(threats, list)

    def test_health_report(self):
        from whitemagic.immune.detector import ThreatDetector
        detector = ThreatDetector()
        detector.scan()
        report = detector.generate_health_report()
        assert "health_status" in report
        assert "health_score" in report
        assert 0 <= report["health_score"] <= 100

    def test_threat_dataclass(self):
        from whitemagic.immune.detector import Threat, ThreatLevel, ThreatType
        t = Threat(
            threat_type=ThreatType.IMPORT_ERROR,
            level=ThreatLevel.HIGH,
            description="Test threat",
        )
        assert t.threat_type == ThreatType.IMPORT_ERROR
        assert t.level == ThreatLevel.HIGH


class TestAntibodyLibrary:
    """Test antibody library."""

    def test_defaults(self):
        from whitemagic.immune.antibodies import AntibodyLibrary
        lib = AntibodyLibrary()
        assert len(lib.antibodies) >= 4

    def test_find_for_antigen(self):
        from whitemagic.immune.antibodies import AntibodyLibrary
        lib = AntibodyLibrary()
        ab = lib.find_for_antigen("import_failure")
        assert ab is not None
        assert ab.name == "fix_import"

    def test_find_missing(self):
        from whitemagic.immune.antibodies import AntibodyLibrary
        lib = AntibodyLibrary()
        assert lib.find_for_antigen("nonexistent") is None

    def test_apply(self):
        from whitemagic.immune.antibodies import AntibodyLibrary
        lib = AntibodyLibrary()
        result = lib.apply("fix_import")
        assert result is True

    def test_list(self):
        from whitemagic.immune.antibodies import AntibodyLibrary
        lib = AntibodyLibrary()
        listing = lib.list_antibodies()
        assert len(listing) >= 4
        assert "name" in listing[0]


class TestImmuneResponse:
    """Test immune response coordination."""

    def test_respond_no_antibody(self):
        from whitemagic.immune.detector import Threat, ThreatLevel, ThreatType
        from whitemagic.immune.response import ImmuneResponse
        response = ImmuneResponse()
        threat = Threat(
            threat_type=ThreatType.CONFIGURATION,
            level=ThreatLevel.LOW,
            description="Test",
            antigen="nonexistent",
        )
        result = response.respond(threat)
        assert result["healed"] is False

    def test_summary(self):
        from whitemagic.immune.response import ImmuneResponse
        response = ImmuneResponse()
        summary = response.summary()
        assert "total_responses" in summary


class TestImmuneMemory:
    """Test immune memory system."""

    def test_record_and_recall(self, tmp_path):
        from whitemagic.immune.memory import ImmuneMemory
        mem = ImmuneMemory(data_dir=tmp_path)
        mem.record("test_antigen", "test_antibody", True)
        entries = mem.recall("test_antigen")
        assert len(entries) == 1
        assert entries[0].successful

    def test_best_antibody(self, tmp_path):
        from whitemagic.immune.memory import ImmuneMemory
        mem = ImmuneMemory(data_dir=tmp_path)
        mem.record("antigen1", "ab1", True)
        mem.record("antigen1", "ab2", False)
        mem.record("antigen1", "ab1", True)
        best = mem.best_antibody("antigen1")
        assert best == "ab1"

    def test_summary(self, tmp_path):
        from whitemagic.immune.memory import ImmuneMemory
        mem = ImmuneMemory(data_dir=tmp_path)
        summary = mem.summary()
        assert "total_entries" in summary


class TestDNALayer:
    """Test DNA layer (immutable principles)."""

    def test_principles(self):
        from whitemagic.immune.dna import DNALayer
        dna = DNALayer()
        principles = dna.list_principles()
        assert len(principles) >= 5

    def test_check_action_safe(self):
        from whitemagic.immune.dna import DNALayer
        dna = DNALayer()
        assert dna.check_action("read file", {"confirmed": True}) is True

    def test_check_action_unsafe(self):
        from whitemagic.immune.dna import DNALayer
        dna = DNALayer()
        assert dna.check_action("delete files", {"confirmed": False}) is False

    def test_autoimmune_detection(self):
        from whitemagic.immune.dna import DNALayer
        dna = DNALayer()
        assert dna.is_autoimmune("delete whitemagic core") is True
        assert dna.is_autoimmune("read memory") is False


class TestHomeostaticMonitor:
    """Test homeostatic monitor."""

    def test_snapshot(self, tmp_path):
        from whitemagic.defense.homeostatic_monitor import HomeostaticMonitor
        (tmp_path / "test.py").write_text("print('hello')")
        monitor = HomeostaticMonitor(project_root=tmp_path)
        snap = monitor.snapshot()
        assert "test.py" in snap

    def test_compare(self, tmp_path):
        from whitemagic.defense.homeostatic_monitor import HomeostaticMonitor
        (tmp_path / "a.py").write_text("print('a')\n")
        monitor = HomeostaticMonitor(project_root=tmp_path)
        monitor.save_snapshot()
        (tmp_path / "b.py").write_text("print('b')")
        changes = monitor.compare()
        assert any(c.change_type == "added" for c in changes)


class TestGranularAwareness:
    """Test granular awareness."""

    def test_scan(self):
        from whitemagic.defense.granular_awareness import GranularAwareness
        awareness = GranularAwareness()
        result = awareness.scan()
        assert "total_changes" in result
        assert "immune_assessment" in result

    def test_summary(self):
        from whitemagic.defense.granular_awareness import GranularAwareness
        awareness = GranularAwareness()
        summary = awareness.summary()
        assert "total_scans" in summary


class TestMultiAgentCoordinator:
    """Test multi-agent coordinator."""

    def test_acquire_and_release(self, tmp_path):
        from whitemagic.defense.multi_agent import MultiAgentCoordinator
        coord = MultiAgentCoordinator(data_dir=tmp_path)
        assert coord.acquire_lock("resource1", "agent1")
        assert coord.release_lock("resource1", "agent1")

    def test_conflicting_lock(self, tmp_path):
        from whitemagic.defense.multi_agent import MultiAgentCoordinator
        coord = MultiAgentCoordinator(data_dir=tmp_path)
        coord.acquire_lock("resource1", "agent1")
        assert not coord.acquire_lock("resource1", "agent2")

    def test_list_locks(self, tmp_path):
        from whitemagic.defense.multi_agent import MultiAgentCoordinator
        coord = MultiAgentCoordinator(data_dir=tmp_path)
        coord.acquire_lock("r1", "a1")
        locks = coord.list_locks()
        assert "r1" in locks

    def test_cleanup_expired(self, tmp_path):
        from whitemagic.defense.multi_agent import MultiAgentCoordinator
        coord = MultiAgentCoordinator(data_dir=tmp_path)
        coord.acquire_lock("r1", "a1", ttl=0.01)
        time.sleep(0.02)
        cleaned = coord.cleanup_expired()
        assert cleaned == 1


class TestAutoimmuneDefense:
    """Test autoimmune defense."""

    def test_scan_file(self, tmp_path):
        from whitemagic.defense.autoimmune import AutoimmuneDefense
        f = tmp_path / "test.py"
        f.write_text("from pathlib import Path\nx = Path.home()\n")
        defense = AutoimmuneDefense(data_dir=tmp_path)
        findings = defense.scan_file(f)
        assert len(findings) >= 1
        assert any(finding["antipattern"] == "path_home_violation" for finding in findings)

    def test_summary(self, tmp_path):
        from whitemagic.defense.autoimmune import AutoimmuneDefense
        defense = AutoimmuneDefense(data_dir=tmp_path)
        summary = defense.summary()
        assert "total_findings" in summary
