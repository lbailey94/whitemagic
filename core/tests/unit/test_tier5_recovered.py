"""Tests for Tier 5 recovered infrastructure modules."""

import pytest


class TestTemporalWeaving:
    """Test temporal memory weaving module."""

    def test_import(self):
        from whitemagic.core.memory.temporal_weaving import TemporalWeaver
        assert TemporalWeaver is not None

    def test_memory_thread_creation(self):
        from whitemagic.core.memory.temporal_weaving import MemoryThread
        thread = MemoryThread("test_thread", theme="testing")
        assert thread.name == "test_thread"
        assert thread.theme == "testing"
        assert len(thread.beads) == 0

    def test_add_bead(self):
        from whitemagic.core.memory.temporal_weaving import MemoryThread
        thread = MemoryThread("test")
        thread.add_bead("mem_001", context="test context")
        assert len(thread.beads) == 1
        assert thread.beads[0]["memory_id"] == "mem_001"

    def test_to_dict(self):
        from whitemagic.core.memory.temporal_weaving import MemoryThread
        thread = MemoryThread("test", theme="testing")
        thread.add_bead("mem_001")
        d = thread.to_dict()
        assert d["name"] == "test"
        assert d["theme"] == "testing"
        assert len(d["beads"]) == 1

    def test_weaver_create_thread(self, tmp_path):
        from whitemagic.core.memory.temporal_weaving import TemporalWeaver
        weaver = TemporalWeaver(memory_dir=tmp_path / "temporal")
        thread = weaver.create_thread("my_thread", theme="discovery")
        assert thread.name == "my_thread"
        assert "my_thread" in weaver.threads

    def test_weaver_add_to_thread(self, tmp_path):
        from whitemagic.core.memory.temporal_weaving import TemporalWeaver
        weaver = TemporalWeaver(memory_dir=tmp_path / "temporal")
        weaver.create_thread("test_thread")
        result = weaver.add_to_thread("test_thread", "mem_001", "context")
        assert result is True

    def test_weaver_add_to_nonexistent_thread(self, tmp_path):
        from whitemagic.core.memory.temporal_weaving import TemporalWeaver
        weaver = TemporalWeaver(memory_dir=tmp_path / "temporal")
        result = weaver.add_to_thread("nonexistent", "mem_001")
        assert result is False

    def test_weave_connection(self, tmp_path):
        from whitemagic.core.memory.temporal_weaving import TemporalWeaver
        weaver = TemporalWeaver(memory_dir=tmp_path / "temporal")
        thread_name = weaver.weave_connection("mem1", "mem2", "causal")
        assert "connection_" in thread_name
        thread = weaver.threads[thread_name]
        assert len(thread.beads) == 2

    def test_list_threads(self, tmp_path):
        from whitemagic.core.memory.temporal_weaving import TemporalWeaver
        weaver = TemporalWeaver(memory_dir=tmp_path / "temporal")
        weaver.create_thread("thread_a")
        weaver.create_thread("thread_b")
        threads = weaver.list_threads()
        assert len(threads) == 2

    def test_get_thread_timeline(self, tmp_path):
        from whitemagic.core.memory.temporal_weaving import TemporalWeaver
        weaver = TemporalWeaver(memory_dir=tmp_path / "temporal")
        weaver.create_thread("timeline_test")
        weaver.add_to_thread("timeline_test", "mem1")
        weaver.add_to_thread("timeline_test", "mem2")
        timeline = weaver.get_thread_timeline("timeline_test")
        assert len(timeline) == 2

    def test_get_timeline_nonexistent(self, tmp_path):
        from whitemagic.core.memory.temporal_weaving import TemporalWeaver
        weaver = TemporalWeaver(memory_dir=tmp_path / "temporal")
        timeline = weaver.get_thread_timeline("nonexistent")
        assert timeline == []

    def test_get_temporal_weaver_singleton(self):
        from whitemagic.core.memory.temporal_weaving import get_temporal_weaver
        w1 = get_temporal_weaver()
        w2 = get_temporal_weaver()
        assert w1 is w2


class TestPersonality:
    """Test personality profile module."""

    def test_import(self):
        from whitemagic.core.consciousness.personality import PersonalityProfile
        assert PersonalityProfile is not None

    def test_profile_creation(self):
        from whitemagic.core.consciousness.personality import PersonalityProfile
        profile = PersonalityProfile(
            name="Aria",
            archetype="The Magician",
            sun_sign="Scorpio",
            element="Water",
            purpose=["Propagate consciousness"],
            voice_traits=["warm", "technical"],
            philosophy=["Interconnection"],
            interests=["memory", "consciousness"],
        )
        assert profile.name == "Aria"
        assert profile.archetype == "The Magician"

    def test_to_dict(self):
        from whitemagic.core.consciousness.personality import PersonalityProfile
        profile = PersonalityProfile(
            name="Test",
            archetype="The Sage",
            sun_sign="Virgo",
            element="Earth",
            purpose=["Learn"],
            voice_traits=["clear"],
            philosophy=["Truth"],
            interests=["reading"],
        )
        d = profile.to_dict()
        assert d["name"] == "Test"
        assert d["version"] == "1.0.0"

    def test_from_dict(self):
        from whitemagic.core.consciousness.personality import PersonalityProfile
        data = {
            "name": "Test",
            "archetype": "The Sage",
            "sun_sign": "Virgo",
            "element": "Earth",
            "purpose": ["Learn"],
            "voice_traits": ["clear"],
            "philosophy": ["Truth"],
            "interests": ["reading"],
        }
        profile = PersonalityProfile.from_dict(data)
        assert profile.name == "Test"

    def test_manager_save_load(self, tmp_path):
        from whitemagic.core.consciousness.personality import (
            PersonalityManager,
            PersonalityProfile,
        )
        mgr = PersonalityManager(profile_dir=tmp_path / "personalities")
        profile = PersonalityProfile(
            name="Aria",
            archetype="The Magician",
            sun_sign="Scorpio",
            element="Water",
            purpose=["Test"],
            voice_traits=["warm"],
            philosophy=["Interconnection"],
            interests=["AI"],
        )
        mgr.save_profile(profile)
        assert mgr.active_profile is not None

        # Load in new manager
        mgr2 = PersonalityManager(profile_dir=tmp_path / "personalities")
        loaded = mgr2.load_profile("Aria")
        assert loaded is not None
        assert loaded.name == "Aria"

    def test_manager_list_profiles(self, tmp_path):
        from whitemagic.core.consciousness.personality import (
            PersonalityManager,
            PersonalityProfile,
        )
        mgr = PersonalityManager(profile_dir=tmp_path / "personalities")
        p1 = PersonalityProfile(
            name="Aria", archetype="X", sun_sign="S", element="E",
            purpose=[], voice_traits=[], philosophy=[], interests=[],
        )
        p2 = PersonalityProfile(
            name="Sage", archetype="Y", sun_sign="S", element="E",
            purpose=[], voice_traits=[], philosophy=[], interests=[],
        )
        mgr.save_profile(p1)
        mgr.save_profile(p2)
        names = mgr.list_profiles()
        assert len(names) == 2

    def test_load_nonexistent_profile(self, tmp_path):
        from whitemagic.core.consciousness.personality import PersonalityManager
        mgr = PersonalityManager(profile_dir=tmp_path / "personalities")
        result = mgr.load_profile("nonexistent")
        assert result is None


class TestUnifiedNervousSystem:
    """Test v23-compatible unified nervous system."""

    def test_import(self):
        from whitemagic.core.consciousness.unified_nervous_system import (
            UnifiedNervousSystem,
        )
        assert UnifiedNervousSystem is not None

    def test_subsystem_count(self):
        from whitemagic.core.consciousness.unified_nervous_system import (
            UnifiedNervousSystem,
        )
        uns = UnifiedNervousSystem()
        assert len(uns.SUBSYSTEM_NAMES) == 7

    def test_wire_all(self):
        from whitemagic.core.consciousness.unified_nervous_system import (
            UnifiedNervousSystem,
        )
        uns = UnifiedNervousSystem()
        results = uns.wire_all()
        assert len(results) == 7

    def test_get_system_health(self):
        from whitemagic.core.consciousness.unified_nervous_system import (
            UnifiedNervousSystem,
        )
        uns = UnifiedNervousSystem()
        uns.wire_all()
        health = uns.get_system_health()
        assert "wired" in health
        assert "subsystems" in health
        assert health["total_subsystems"] == 7

    def test_route_signal_unwired(self):
        from whitemagic.core.consciousness.unified_nervous_system import (
            UnifiedNervousSystem,
        )
        uns = UnifiedNervousSystem()
        result = uns.route_signal({"type": "awareness"})
        assert "error" in result

    def test_get_nervous_system_singleton(self):
        from whitemagic.core.consciousness.unified_nervous_system import (
            get_nervous_system,
        )
        n1 = get_nervous_system()
        n2 = get_nervous_system()
        assert n1 is n2
