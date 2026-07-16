"""Tests for the HexagramState cognitive state machine."""

from __future__ import annotations

import threading
import time

import pytest

from whitemagic.core.consciousness.hexagram_state import (
    HexagramState,
    TRIGRAM_BITS,
    TRIGRAM_CORE,
    TRIGRAM_ELEMENT,
    TRIGRAM_FUNCTION,
    _BINARY_TO_KING_WEN,
    _KING_WEN_NAMES,
)


class TestTrigramConstants:
    """Test trigram constant mappings."""

    def test_all_8_trigrams_present(self):
        assert len(TRIGRAM_BITS) == 8
        assert len(TRIGRAM_FUNCTION) == 8
        assert len(TRIGRAM_ELEMENT) == 8
        assert len(TRIGRAM_CORE) == 8

    def test_trigram_bits_unique(self):
        bits = list(TRIGRAM_BITS.values())
        assert len(set(bits)) == 8

    def test_trigram_functions_unique(self):
        functions = list(TRIGRAM_FUNCTION.values())
        assert len(set(functions)) == 8

    def test_core_ids_in_range(self):
        for core in TRIGRAM_CORE.values():
            assert 0 <= core <= 3

    def test_two_trigrams_per_core(self):
        from collections import Counter

        core_counts = Counter(TRIGRAM_CORE.values())
        assert all(count == 2 for count in core_counts.values())
        assert len(core_counts) == 4


class TestHexagramStateInit:
    """Test HexagramState initialization and defaults."""

    def test_default_state(self):
        state = HexagramState()
        assert state.lower == "Kun"
        assert state.upper == "Gen"

    def test_default_king_wen(self):
        state = HexagramState()
        # Kun (0b000) lower, Gen (0b100) upper
        # binary = (0b100 << 3) | 0b000 = 0b100000 = 32
        # _BINARY_TO_KING_WEN[32] should give the King Wen number
        expected_kw = _BINARY_TO_KING_WEN[0b100000]
        assert state.king_wen_number == expected_kw

    def test_initial_transition_count(self):
        state = HexagramState()
        assert state.transition_count == 0

    def test_hexagram_name(self):
        state = HexagramState()
        assert state.hexagram_name is not None
        assert len(state.hexagram_name) > 0


class TestHexagramTransitions:
    """Test state transitions."""

    def test_basic_transition(self):
        state = HexagramState()
        record = state.transition(new_lower="Qian", new_upper="Li", reason="test")
        assert state.lower == "Qian"
        assert state.upper == "Li"
        assert record["from_lower"] == "Kun"
        assert record["to_lower"] == "Qian"
        assert record["reason"] == "test"
        assert state.transition_count == 1

    def test_partial_transition_lower_only(self):
        state = HexagramState()
        state.transition(new_lower="Qian", reason="lower only")
        assert state.lower == "Qian"
        assert state.upper == "Gen"

    def test_partial_transition_upper_only(self):
        state = HexagramState()
        state.transition(new_upper="Li", reason="upper only")
        assert state.lower == "Kun"
        assert state.upper == "Li"

    def test_invalid_trigram_name(self):
        state = HexagramState()
        with pytest.raises(ValueError, match="Invalid trigram"):
            state.transition(new_lower="Invalid")

    def test_all_64_states_reachable(self):
        """Verify all 64 hexagram states are reachable via transitions."""
        state = HexagramState()
        reached = set()

        for lower in TRIGRAM_BITS:
            for upper in TRIGRAM_BITS:
                state.transition(new_lower=lower, new_upper=upper, reason=f"test {lower}/{upper}")
                reached.add(state.king_wen_number)

        assert len(reached) == 64
        assert all(1 <= kw <= 64 for kw in reached)

    def test_transition_count_increments(self):
        state = HexagramState()
        for i in range(10):
            state.transition(new_lower="Qian", reason=f"transition {i}")
        assert state.transition_count == 10

    def test_same_state_transition_still_logged(self):
        state = HexagramState()
        state.transition(new_lower="Kun", new_upper="Gen", reason="same state")
        assert state.transition_count == 1
        log = state.get_audit_log()
        assert len(log) == 1


class TestAuditLog:
    """Test audit log functionality."""

    def test_audit_log_order(self):
        state = HexagramState()
        state.transition(new_lower="Qian", reason="first")
        state.transition(new_lower="Li", reason="second")
        state.transition(new_lower="Kan", reason="third")

        log = state.get_audit_log()
        assert len(log) == 3
        # Most recent first
        assert log[0]["reason"] == "third"
        assert log[2]["reason"] == "first"

    def test_audit_log_limit(self):
        state = HexagramState()
        for i in range(100):
            state.transition(new_lower="Qian", reason=f"transition {i}")

        log = state.get_audit_log(limit=10)
        assert len(log) == 10
        # Should be the 10 most recent
        assert log[0]["reason"] == "transition 99"

    def test_audit_log_record_fields(self):
        state = HexagramState()
        record = state.transition(new_lower="Qian", new_upper="Li", reason="field test")
        log = state.get_audit_log()

        assert log[0]["transition_id"] == 1
        assert "timestamp" in log[0]
        assert "from_lower" in log[0]
        assert "to_lower" in log[0]
        assert "from_upper" in log[0]
        assert "to_upper" in log[0]
        assert "from_king_wen" in log[0]
        assert "to_king_wen" in log[0]
        assert "from_name" in log[0]
        assert "to_name" in log[0]
        assert "reason" in log[0]


class TestActiveFunctions:
    """Test active function/element/core queries."""

    def test_active_functions(self):
        state = HexagramState()
        state.transition(new_lower="Qian", new_upper="Li")
        functions = state.get_active_functions()
        assert "draft" in functions  # Qian → draft
        assert "verify" in functions  # Li → verify

    def test_active_elements(self):
        state = HexagramState()
        state.transition(new_lower="Qian", new_upper="Li")
        elements = state.get_active_elements()
        assert "fire" in elements  # Both Qian and Li → fire

    def test_active_cores(self):
        state = HexagramState()
        state.transition(new_lower="Qian", new_upper="Li")
        cores = state.get_active_cores()
        assert 0 in cores  # Qian → core 0
        assert 1 in cores  # Li → core 1

    def test_active_functions_same_trigram(self):
        state = HexagramState()
        state.transition(new_lower="Qian", new_upper="Qian")
        functions = state.get_active_functions()
        assert functions == {"draft"}


class TestStateVector:
    """Test HRR state vector retrieval."""

    def test_state_vector_length(self):
        state = HexagramState()
        vec = state.get_state_vector()
        assert len(vec) == 64

    def test_state_vector_normalized(self):
        import math

        state = HexagramState()
        vec = state.get_state_vector()
        norm = math.sqrt(sum(v * v for v in vec))
        assert abs(norm - 1.0) < 0.01  # approximately unit-normalized


class TestStatus:
    """Test status reporting."""

    def test_status_dict(self):
        state = HexagramState()
        state.transition(new_lower="Qian", new_upper="Li", reason="status test")
        status = state.get_status()

        assert status["lower_trigram"] == "Qian"
        assert status["upper_trigram"] == "Li"
        assert "king_wen_number" in status
        assert "hexagram_name" in status
        assert "draft" in status["active_functions"]
        assert "verify" in status["active_functions"]
        assert status["transition_count"] == 1
        assert "uptime_seconds" in status


class TestReset:
    """Test reset functionality."""

    def test_reset(self):
        state = HexagramState()
        state.transition(new_lower="Qian", new_upper="Li", reason="before reset")
        state.reset()
        assert state.lower == "Kun"
        assert state.upper == "Gen"


class TestThreadSafety:
    """Test concurrent access."""

    def test_concurrent_transitions(self):
        state = HexagramState()
        errors: list[Exception] = []

        def worker():
            try:
                for i in range(50):
                    state.transition(new_lower="Qian", reason=f"concurrent {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert state.transition_count == 200

    def test_concurrent_read_write(self):
        state = HexagramState()
        errors: list[Exception] = []

        def writer():
            try:
                for i in range(50):
                    state.transition(new_lower="Qian", reason=f"write {i}")
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for _ in range(50):
                    state.get_audit_log()
                    state.get_status()
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer), threading.Thread(target=reader)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestKingWenConsistency:
    """Test King Wen number consistency with hexagram_vectors.py."""

    def test_king_wen_in_range(self):
        state = HexagramState()
        for lower in TRIGRAM_BITS:
            for upper in TRIGRAM_BITS:
                state.transition(new_lower=lower, new_upper=upper)
                assert 1 <= state.king_wen_number <= 64

    def test_all_king_wen_names_present(self):
        state = HexagramState()
        for lower in TRIGRAM_BITS:
            for upper in TRIGRAM_BITS:
                state.transition(new_lower=lower, new_upper=upper)
                name = state.hexagram_name
                assert name is not None
                assert name != f"Hexagram {state.king_wen_number}"  # Should have a real name
