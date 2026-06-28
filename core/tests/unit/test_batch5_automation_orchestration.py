"""Tests for Batch 5: Automation & Orchestration."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestConsolidationEngine:
    """Test memory consolidation engine."""

    def test_should_consolidate(self, tmp_path):
        from whitemagic.core.automation.consolidation_recovered import ConsolidationEngine
        engine = ConsolidationEngine(data_dir=tmp_path)
        should, reason = engine.should_consolidate()
        assert isinstance(should, bool)
        assert isinstance(reason, str)

    def test_consolidate_force(self, tmp_path):
        from whitemagic.core.automation.consolidation_recovered import ConsolidationEngine
        engine = ConsolidationEngine(data_dir=tmp_path)
        result = engine.consolidate(force=True)
        assert result.duration_s >= 0

    def test_summary(self, tmp_path):
        from whitemagic.core.automation.consolidation_recovered import ConsolidationEngine
        engine = ConsolidationEngine(data_dir=tmp_path)
        summary = engine.summary()
        assert "threshold" in summary


class TestPreCommitAutoFix:
    """Test pre-commit auto-fix loop."""

    def test_run(self):
        from whitemagic.core.automation.precommit import PreCommitAutoFix
        fixer = PreCommitAutoFix(max_retries=1)
        result = fixer.run()
        assert "success" in result
        assert "attempts" in result


class TestAutomationOrchestra:
    """Test automation orchestra."""

    def test_register_and_conduct(self):
        from whitemagic.core.automation.orchestra_recovered import AutomationOrchestra
        orchestra = AutomationOrchestra()
        orchestra.register_system("test", lambda: "ok")
        result = orchestra.conduct()
        assert result["cycle"] == 1
        assert result["results"]["test"] == "ok"

    def test_status(self):
        from whitemagic.core.automation.orchestra_recovered import AutomationOrchestra
        orchestra = AutomationOrchestra()
        status = orchestra.status()
        assert "systems" in status
        assert "cycle_count" in status


class TestConsolidationTriggers:
    """Test consolidation triggers."""

    def test_defaults(self):
        from whitemagic.core.automation.triggers_recovered import ConsolidationTriggers
        triggers = ConsolidationTriggers()
        assert "session_end" in triggers.triggers
        assert "memory_count" in triggers.triggers

    def test_enable_disable(self):
        from whitemagic.core.automation.triggers_recovered import ConsolidationTriggers
        triggers = ConsolidationTriggers()
        assert triggers.disable("session_end") is True
        assert triggers.triggers["session_end"]["enabled"] is False
        assert triggers.enable("session_end") is True

    def test_fire_trigger(self):
        from whitemagic.core.automation.triggers_recovered import ConsolidationTriggers
        triggers = ConsolidationTriggers()
        assert triggers.fire_trigger("session_end") is True
        assert triggers.fire_trigger("nonexistent") is False

    def test_check_triggers(self):
        from whitemagic.core.automation.triggers_recovered import ConsolidationTriggers
        triggers = ConsolidationTriggers()
        active = triggers.check_triggers()
        assert isinstance(active, list)


class TestIncrementalBackup:
    """Test incremental backup."""

    def test_backup(self, tmp_path):
        from whitemagic.core.automation.incremental_backup import IncrementalBackup
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.py").write_text("print('hello')")
        backup_dir = tmp_path / "backups"
        backup = IncrementalBackup(backup_dir=backup_dir)
        result = backup.backup(source_dir=source, label="test")
        assert result["files_backed_up"] == 1

    def test_incremental_skip(self, tmp_path):
        from whitemagic.core.automation.incremental_backup import IncrementalBackup
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.py").write_text("print('hello')")
        backup_dir = tmp_path / "backups"
        backup = IncrementalBackup(backup_dir=backup_dir)
        backup.backup(source_dir=source, label="first")
        result = backup.backup(source_dir=source, label="second")
        assert result["files_backed_up"] == 0
        assert result["files_skipped"] == 1

    def test_list_backups(self, tmp_path):
        from whitemagic.core.automation.incremental_backup import IncrementalBackup
        source = tmp_path / "source"
        source.mkdir()
        (source / "test.py").write_text("print('hello')")
        backup = IncrementalBackup(backup_dir=tmp_path / "backups")
        backup.backup(source_dir=source, label="test")
        backups = backup.list_backups()
        assert len(backups) == 1


class TestTestWatcher:
    """Test test watcher."""

    def test_check_changes(self, tmp_path):
        from whitemagic.core.automation.test_watcher import TestWatcher
        watcher = TestWatcher(watch_dir=tmp_path, test_cmd=["echo", "ok"])
        (tmp_path / "test.py").write_text("print('test')")
        changed = watcher.check_changes()
        assert len(changed) >= 1

    def test_no_changes(self, tmp_path):
        from whitemagic.core.automation.test_watcher import TestWatcher
        watcher = TestWatcher(watch_dir=tmp_path, test_cmd=["echo", "ok"])
        watcher.check_changes()  # Initial scan
        changed = watcher.check_changes()
        assert len(changed) == 0

    def test_summary(self, tmp_path):
        from whitemagic.core.automation.test_watcher import TestWatcher
        watcher = TestWatcher(watch_dir=tmp_path)
        summary = watcher.summary()
        assert "tracked_files" in summary


class TestToolSharpening:
    """Test tool sharpening."""

    def test_sharpen_all(self):
        from whitemagic.core.automation.tool_sharpening import ToolSharpening
        ts = ToolSharpening()
        results = ts.sharpen_all()
        assert "mcp_tools" in results
        assert "dispatch_table" in results
        assert "grimoire" in results
        assert "tests" in results

    def test_summary(self):
        from whitemagic.core.automation.tool_sharpening import ToolSharpening
        ts = ToolSharpening()
        ts.sharpen_all()
        summary = ts.summary()
        assert summary["sharpening_cycles"] == 1


class TestDailyNarrative:
    """Test daily narrative."""

    def test_check_daily_journal(self):
        from whitemagic.core.automation.daily_narrative import check_daily_journal
        result = check_daily_journal()
        assert "status" in result


class TestZodiacalProcession:
    """Test zodiacal procession."""

    def test_advance(self):
        from whitemagic.core.orchestration.zodiacal_procession_recovered import ZodiacalProcession
        proc = ZodiacalProcession()
        assert proc.current_sign == "aries"
        proc.advance()
        assert proc.current_sign == "taurus"

    def test_full_cycle(self):
        from whitemagic.core.orchestration.zodiacal_procession_recovered import ZodiacalProcession
        proc = ZodiacalProcession()
        for _ in range(12):
            proc.advance()
        assert proc.current_sign == "aries"
        assert proc.cycle_count == 12

    def test_set_sign(self):
        from whitemagic.core.orchestration.zodiacal_procession_recovered import ZodiacalProcession
        proc = ZodiacalProcession()
        assert proc.set_sign("leo") is True
        assert proc.current_sign == "leo"
        assert proc.set_sign("invalid") is False

    def test_status(self):
        from whitemagic.core.orchestration.zodiacal_procession_recovered import ZodiacalProcession
        proc = ZodiacalProcession()
        status = proc.status()
        assert "current_sign" in status
        assert "direction" in status


class TestYinPhase:
    """Test yin phase."""

    def test_enter_observe_exit(self):
        from whitemagic.core.orchestration.yin_phase import YinPhase
        yin = YinPhase()
        yin.enter()
        assert yin.active is True
        yin.observe("memory", "pattern detected")
        yin.observe("memory", "similar pattern")
        yin.observe("memory", "third occurrence")
        result = yin.exit()
        assert result["observations"] == 3
        assert len(result["insights"]) >= 1
        assert yin.active is False

    def test_status(self):
        from whitemagic.core.orchestration.yin_phase import YinPhase
        yin = YinPhase()
        status = yin.status()
        assert "active" in status


class TestDreamStateOrchestration:
    """Test dream state orchestration."""

    def test_dream(self):
        from whitemagic.core.orchestration.dream_state import DreamStateOrchestration
        dream = DreamStateOrchestration()
        result = dream.dream()
        assert result["dream_number"] == 1

    def test_status(self):
        from whitemagic.core.orchestration.dream_state import DreamStateOrchestration
        dream = DreamStateOrchestration()
        status = dream.status()
        assert "dream_count" in status


class TestSystemMonitor:
    """Test system monitor."""

    def test_register_and_collect(self):
        from whitemagic.systems.monitoring.system_monitor import SystemMonitor
        monitor = SystemMonitor()
        monitor.register_subsystem("test", type("S", (), {"summary": lambda self: {"ok": True}})())
        metrics = monitor.collect_metrics()
        assert "test" in metrics
        assert metrics["test"]["ok"] is True

    def test_health_report(self):
        from whitemagic.systems.monitoring.system_monitor import SystemMonitor
        monitor = SystemMonitor()
        report = monitor.health_report()
        assert "status" in report
        assert report["status"] == "unknown"  # no subsystems

    def test_summary(self):
        from whitemagic.systems.monitoring.system_monitor import SystemMonitor
        monitor = SystemMonitor()
        summary = monitor.summary()
        assert "registered_subsystems" in summary
