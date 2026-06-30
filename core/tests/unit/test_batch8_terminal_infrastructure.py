"""Tests for Batch 8: Terminal & Infrastructure modules."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

os.environ.setdefault("WM_STATE_ROOT", str(Path(tempfile.mkdtemp())))


class TestAllowlist:
    def test_is_allowed(self):
        from whitemagic.terminal.allowlist import Allowlist, Profile

        al = Allowlist(Profile.STANDARD)
        assert al.is_allowed("ls -la") is True
        assert al.is_allowed("rm -rf /") is False

    def test_block(self):
        from whitemagic.terminal.allowlist import Allowlist, Profile

        al = Allowlist(Profile.ELEVATED)
        al.block("rm")
        assert al.is_allowed("rm file") is False

    def test_summary(self):
        from whitemagic.terminal.allowlist import Allowlist, Profile

        al = Allowlist(Profile.RESTRICTED)
        summary = al.summary()
        assert summary["profile"] == "restricted"


class TestAuditLogger:
    def test_log_and_recent(self, tmp_path):
        from whitemagic.terminal.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        logger.log("ls", 0, 0.1, "output")
        entries = logger.recent()
        assert len(entries) == 1
        assert entries[0].command == "ls"

    def test_summary(self, tmp_path):
        from whitemagic.terminal.audit import AuditLogger

        logger = AuditLogger(log_dir=tmp_path)
        logger.log("ls", 0, 0.1)
        logger.log("bad", 1, 0.1)
        summary = logger.summary()
        assert summary["total_entries"] == 2
        assert summary["successful"] == 1


class TestExecutor:
    def test_execute_success(self):
        from whitemagic.terminal.executor import Executor

        ex = Executor(timeout=5)
        result = ex.execute("echo hello")
        assert result.exit_code == 0
        assert "hello" in result.stdout

    def test_execute_failure(self):
        from whitemagic.terminal.executor import Executor

        ex = Executor(timeout=5)
        result = ex.execute("false")
        assert result.exit_code != 0


class TestTerminalConfig:
    def test_history(self):
        from whitemagic.terminal.config import TerminalConfig

        cfg = TerminalConfig()
        cfg.add_to_history("ls")
        cfg.add_to_history("pwd")
        history = cfg.get_history()
        assert len(history) == 2


class TestTerminalMultiplexer:
    def test_create_and_switch(self):
        from whitemagic.terminal.multiplexer import TerminalMultiplexer

        mux = TerminalMultiplexer()
        assert mux.create_channel("work") is True
        assert mux.switch("work") is True
        assert mux.active_channel == "work"

    def test_write_and_read(self):
        from whitemagic.terminal.multiplexer import TerminalMultiplexer

        mux = TerminalMultiplexer()
        mux.write("hello")
        mux.write("world")
        content = mux.read()
        assert content == ["hello", "world"]

    def test_close_channel(self):
        from whitemagic.terminal.multiplexer import TerminalMultiplexer

        mux = TerminalMultiplexer()
        mux.create_channel("temp")
        assert mux.close_channel("temp") is True
        assert mux.close_channel("default") is False


class TestTerminalMCPTools:
    def test_run_command_allowed(self):
        from whitemagic.terminal.mcp_tools import TerminalMCPTools

        tools = TerminalMCPTools()
        result = tools.run_command("echo test")
        assert result["status"] == "success"

    def test_run_command_blocked(self):
        from whitemagic.terminal.mcp_tools import TerminalMCPTools

        tools = TerminalMCPTools()
        result = tools.run_command("rm -rf /")
        assert result["status"] == "error"


class TestHomeostasisMetrics:
    def test_record_and_check(self):
        from whitemagic.homeostasis.metrics import HomeostasisMetrics

        m = HomeostasisMetrics()
        m.record("memory_balance", 0.5)
        assert m.is_in_range("memory_balance") is True

    def test_out_of_range(self):
        from whitemagic.homeostasis.metrics import HomeostasisMetrics

        m = HomeostasisMetrics()
        m.record("memory_balance", 0.9)
        assert m.is_in_range("memory_balance") is False

    def test_deviations(self):
        from whitemagic.homeostasis.metrics import HomeostasisMetrics

        m = HomeostasisMetrics()
        m.record("memory_balance", 0.7)
        devs = m.deviations()
        assert "memory_balance" in devs


class TestFeedbackLoop:
    def test_register_and_check(self):
        from whitemagic.homeostasis.feedback import FeedbackLoop
        from whitemagic.homeostasis.metrics import HomeostasisMetrics

        m = HomeostasisMetrics()
        loop = FeedbackLoop(metrics=m)
        called: list[float] = []
        loop.register_action("memory_balance", lambda d: called.append(d))
        m.record("memory_balance", 0.9)  # Out of range
        corrections = loop.check_and_correct()
        assert len(corrections) == 1
        assert len(called) == 1


class TestEquilibriumDetector:
    def test_at_equilibrium(self):
        from whitemagic.homeostasis.equilibrium import EquilibriumDetector
        from whitemagic.homeostasis.metrics import HomeostasisMetrics

        m = HomeostasisMetrics()
        m.record("memory_balance", 0.5)
        det = EquilibriumDetector(metrics=m)
        assert det.is_at_equilibrium() is True

    def test_stability_score(self):
        from whitemagic.homeostasis.equilibrium import EquilibriumDetector

        det = EquilibriumDetector()
        det.equilibrium_history = [True, True, False, True]
        assert det.stability_score() == 0.75


class TestDashboardServer:
    def test_handle_request(self):
        from whitemagic.dashboard.server import DashboardServer

        server = DashboardServer()
        result = server.handle_request("/api/health")
        assert result["status"] == "ok"

    def test_not_found(self):
        from whitemagic.dashboard.server import DashboardServer

        server = DashboardServer()
        result = server.handle_request("/unknown")
        assert result["status"] == "not_found"

    def test_list_endpoints(self):
        from whitemagic.dashboard.server import DashboardServer

        server = DashboardServer()
        endpoints = server.list_endpoints()
        assert "/api/health" in endpoints


class TestHarmonyMetrics:
    def test_update_and_get(self):
        from whitemagic.dashboard.harmony_metrics import HarmonyMetrics

        hm = HarmonyMetrics()
        hm.update_garden("joy", 0.8)
        assert hm.get_harmony("joy") == 0.8

    def test_overall(self):
        from whitemagic.dashboard.harmony_metrics import HarmonyMetrics

        hm = HarmonyMetrics()
        hm.update_garden("joy", 0.6)
        hm.update_garden("truth", 0.8)
        overall = hm.get_harmony()
        assert 0.6 < overall < 0.8

    def test_trend(self):
        from whitemagic.dashboard.harmony_metrics import HarmonyMetrics

        hm = HarmonyMetrics()
        hm.update_garden("joy", 0.5)
        hm.update_garden("joy", 0.7)
        trend = hm.trend()
        assert len(trend) == 2


class TestZodiacCoreSystem:
    def test_init_all_signs(self):
        from whitemagic.connection.zodiac_cores import ZodiacCoreSystem

        system = ZodiacCoreSystem()
        assert len(system.cores) == 12

    def test_activate(self):
        from whitemagic.connection.zodiac_cores import ZodiacCoreSystem

        system = ZodiacCoreSystem()
        system.activate("leo")
        assert "leo" in system.active_cores()

    def test_set_energy(self):
        from whitemagic.connection.zodiac_cores import ZodiacCoreSystem

        system = ZodiacCoreSystem()
        system.set_energy("aries", 0.9)
        assert system.cores["aries"].energy == 0.9


class TestEvolutionaryCores:
    def test_all_signs(self):
        from whitemagic.connection.zodiac_cores_c import get_evolutionary_cores

        cores = get_evolutionary_cores()
        assert len(cores) == 12

    def test_matches_task(self):
        from whitemagic.connection.zodiac_cores_c import get_evolutionary_cores

        cores = get_evolutionary_cores()
        assert cores["aries"].matches_task("start") is True
        assert cores["aries"].matches_task("heal") is False


class TestSynastryGovernor:
    def test_complementary(self):
        from whitemagic.connection.synastry_governor import SynastryGovernor

        gov = SynastryGovernor()
        result = gov.resolve("aries", "libra", "direction")
        assert result["is_complementary"] is True

    def test_non_complementary(self):
        from whitemagic.connection.synastry_governor import SynastryGovernor

        gov = SynastryGovernor()
        result = gov.resolve("aries", "taurus", "resources")
        assert result["is_complementary"] is False
        assert result["strategy"] == "synthesis"

    def test_summary(self):
        from whitemagic.connection.synastry_governor import SynastryGovernor

        gov = SynastryGovernor()
        gov.resolve("aries", "libra", "test")
        summary = gov.summary()
        assert summary["total_resolutions"] == 1
