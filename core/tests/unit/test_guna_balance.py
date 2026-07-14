"""Tests for guna balance metric — biorhythm tracking and correction."""

import os
import tempfile

os.environ.setdefault("WM_STATE_ROOT", tempfile.mkdtemp())
os.environ.setdefault("WM_SKIP_POLYGLOT", "1")
os.environ.setdefault("WM_SILENT_INIT", "1")

import pytest

from whitemagic.core.consciousness.guna_balance import (
    TARGET_RATIOS,
    GunaBalanceMetric,
)


class TestGunaBalanceMetric:
    def test_empty_history_returns_target(self):
        gb = GunaBalanceMetric()
        reading = gb.measure()
        assert reading.balanced is True
        assert abs(reading.sattvic_ratio - TARGET_RATIOS["sattvic"]) < 0.01
        assert abs(reading.rajasic_ratio - TARGET_RATIOS["rajasic"]) < 0.01
        assert abs(reading.tamasic_ratio - TARGET_RATIOS["tamasic"]) < 0.01

    def test_record_and_measure(self):
        gb = GunaBalanceMetric(window_size=10)
        for _ in range(3):
            gb.record_tone("sattvic")
        for _ in range(6):
            gb.record_tone("rajasic")
        for _ in range(1):
            gb.record_tone("tamasic")

        reading = gb.measure()
        assert reading.sattvic_ratio == pytest.approx(0.3, abs=0.01)
        assert reading.rajasic_ratio == pytest.approx(0.6, abs=0.01)
        assert reading.tamasic_ratio == pytest.approx(0.1, abs=0.01)
        assert reading.dominant_guna == "rajasic"

    def test_tone_classification(self):
        gb = GunaBalanceMetric()
        assert gb._classify_tone("calm") == "sattvic"
        assert gb._classify_tone("excited") == "rajasic"
        assert gb._classify_tone("drowsy") == "tamasic"
        assert gb._classify_tone("dreaming") == "tamasic"
        assert gb._classify_tone("active") == "rajasic"
        assert gb._classify_tone("unknown_tone") == "sattvic"

    def test_balance_detection(self):
        gb = GunaBalanceMetric(window_size=12)
        # Record at target ratio: 2 sattvic, 4 rajasic, 6 tamasic
        for _ in range(2):
            gb.record_tone("sattvic")
        for _ in range(4):
            gb.record_tone("rajasic")
        for _ in range(6):
            gb.record_tone("tamasic")

        reading = gb.measure()
        assert reading.balanced is True
        assert not reading.deficits
        assert not reading.surpluses

    def test_imbalance_detection(self):
        gb = GunaBalanceMetric(window_size=10)
        # All rajasic — should detect tamasic deficit
        for _ in range(10):
            gb.record_tone("rajasic")

        reading = gb.measure()
        assert reading.balanced is False
        assert "tamasic" in reading.deficits
        assert "rajasic" in reading.surpluses
        assert reading.correction_action == "trigger_dream_cycle"

    def test_correction_action_too_much_tamasic(self):
        gb = GunaBalanceMetric(window_size=10)
        for _ in range(10):
            gb.record_tone("tamasic")

        reading = gb.measure()
        assert reading.balanced is False
        assert reading.correction_action == "trigger_self_directed_attention"

    def test_correction_action_too_much_sattvic(self):
        gb = GunaBalanceMetric(window_size=10)
        for _ in range(10):
            gb.record_tone("sattvic")

        reading = gb.measure()
        assert reading.balanced is False
        assert reading.correction_action == "trigger_active_processing"

    def test_window_trimming(self):
        gb = GunaBalanceMetric(window_size=5)
        for _ in range(20):
            gb.record_tone("rajasic")

        assert len(gb._tone_history) == 5

    def test_to_dict(self):
        gb = GunaBalanceMetric()
        reading = gb.measure()
        d = reading.to_dict()
        assert "sattvic_ratio" in d
        assert "targets" in d
        assert "balanced" in d

    def test_get_status(self):
        gb = GunaBalanceMetric()
        status = gb.get_status()
        assert "current" in status
        assert "target_ratios" in status
        assert "window_size" in status

    def test_get_report(self):
        gb = GunaBalanceMetric()
        report = gb.get_report()
        assert "GUNA BALANCE" in report
        assert "Target:" in report
        assert "Actual:" in report

    def test_target_ratios_sum_to_one(self):
        total = sum(TARGET_RATIOS.values())
        assert abs(total - 1.0) < 0.001
