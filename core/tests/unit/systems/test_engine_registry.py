"""Tests for Engine Registry (Leap 7d)."""

from whitemagic.core.engines.registry import (
    ENGINE_REGISTRY,
    EngineEntry,
    EngineStatus,
    Quadrant,
    get_engine_entry,
    get_engine_stats,
    get_engines_by_quadrant,
    get_engines_by_status,
    get_parent_engine,
)


class TestEngineRegistryStructure:
    def test_exactly_28_engines(self):
        assert len(ENGINE_REGISTRY) == 28

    def test_slots_are_sequential(self):
        for i, engine in enumerate(ENGINE_REGISTRY):
            assert engine.slot == i, (
                f"Engine {engine.engine_name} has slot {engine.slot}, expected {i}"
            )

    def test_all_entries_are_engine_entry(self):
        for engine in ENGINE_REGISTRY:
            assert isinstance(engine, EngineEntry)

    def test_gardens_match_truth_table(self):
        """Gardens must match the canonical grimoire/TRUTH_TABLE.md mapping."""
        expected = [
            "courage",
            "stillness",
            "healing",
            "sanctuary",
            "love",
            "wonder",
            "wisdom",
            "grief",
            "humor",
            "voice",
            "sangha",
            "beauty",
            "adventure",
            "joy",
            "awe",
            "gratitude",
            "creation",
            "presence",
            "play",
            "practice",
            "reverence",
            "dharma",
            "patience",
            "connection",
            "mystery",
            "protection",
            "transformation",
            "truth",
        ]
        actual = [e.garden for e in ENGINE_REGISTRY]
        assert actual == expected, (
            f"Garden mismatch at indices: {[i for i, (a, e) in enumerate(zip(actual, expected)) if a != e]}"
        )

    def test_all_engine_names_unique(self):
        names = [e.engine_name for e in ENGINE_REGISTRY]
        assert len(names) == len(set(names)), (
            f"Duplicate names: {[n for n in names if names.count(n) > 1]}"
        )

    def test_all_mansion_names_unique(self):
        mansions = [e.mansion_name for e in ENGINE_REGISTRY]
        assert len(mansions) == len(set(mansions))

    def test_grimoire_chapters_are_1_to_28(self):
        chapters = sorted(e.grimoire_chapter for e in ENGINE_REGISTRY)
        assert chapters == list(range(1, 29))

    def test_handler_ids_are_100_to_127(self):
        handlers = sorted(e.handler_id for e in ENGINE_REGISTRY)
        assert handlers == list(range(100, 128))


class TestQuadrantDistribution:
    def test_east_has_7(self):
        assert len(get_engines_by_quadrant(Quadrant.EAST)) == 7

    def test_south_has_7(self):
        assert len(get_engines_by_quadrant(Quadrant.SOUTH)) == 7

    def test_west_has_7(self):
        assert len(get_engines_by_quadrant(Quadrant.WEST)) == 7

    def test_north_has_7(self):
        assert len(get_engines_by_quadrant(Quadrant.NORTH)) == 7

    def test_east_is_wood(self):
        for e in get_engines_by_quadrant(Quadrant.EAST):
            assert e.wu_xing == "wood"

    def test_south_is_fire(self):
        for e in get_engines_by_quadrant(Quadrant.SOUTH):
            assert e.wu_xing == "fire"

    def test_west_is_metal(self):
        for e in get_engines_by_quadrant(Quadrant.WEST):
            assert e.wu_xing == "metal"

    def test_north_is_water(self):
        for e in get_engines_by_quadrant(Quadrant.NORTH):
            assert e.wu_xing == "water"


class TestLookups:
    def test_lookup_by_slot(self):
        e = get_engine_entry(0)
        assert e is not None
        assert e.engine_name == "SessionEngine"

    def test_lookup_by_engine_name(self):
        e = get_engine_entry("ResonanceEngine")
        assert e is not None
        assert e.slot == 13
        assert e.garden == "joy"

    def test_lookup_by_garden(self):
        e = get_engine_entry("wisdom")
        assert e is not None
        assert e.engine_name == "SerendipityEngine"

    def test_lookup_by_mansion(self):
        e = get_engine_entry("Wall")
        assert e is not None
        assert e.engine_name == "EmergenceEngine"
        assert e.slot == 27

    def test_lookup_invalid(self):
        assert get_engine_entry("nonexistent") is None
        assert get_engine_entry(999) is None


class TestEngineEntryProperties:
    def test_handler_id(self):
        e = get_engine_entry(0)
        assert e.handler_id == 100

    def test_season(self):
        east = get_engine_entry(0)
        assert east.season == "spring"
        south = get_engine_entry(7)
        assert south.season == "summer"
        west = get_engine_entry(14)
        assert west.season == "autumn"
        north = get_engine_entry(21)
        assert north.season == "winter"

    def test_celestial_animal(self):
        east = get_engine_entry(0)
        assert "Azure Dragon" in east.celestial_animal
        south = get_engine_entry(7)
        assert "Vermilion Bird" in south.celestial_animal


class TestEngineStatus:
    def test_most_engines_exist(self):
        existing = get_engines_by_status(EngineStatus.EXISTS)
        assert len(existing) >= 27  # All but one are EXISTS

    def test_distributed_engine(self):
        e = get_engine_entry("AccelerationEngine")
        assert e is not None
        assert e.status == EngineStatus.DISTRIBUTED


class TestEngineStats:
    def test_total_is_28(self):
        stats = get_engine_stats()
        assert stats["total_engines"] == 28

    def test_quadrant_distribution(self):
        stats = get_engine_stats()
        by_q = stats["by_quadrant"]
        assert by_q["east"] == 7
        assert by_q["south"] == 7
        assert by_q["west"] == 7
        assert by_q["north"] == 7

    def test_wu_xing_distribution(self):
        stats = get_engine_stats()
        by_wx = stats["by_wu_xing"]
        assert by_wx["wood"] == 7
        assert by_wx["fire"] == 7
        assert by_wx["metal"] == 7
        assert by_wx["water"] == 7


class TestKnownEngines:
    """Verify specific engines are correctly mapped."""

    def test_session_engine(self):
        e = get_engine_entry("SessionEngine")
        assert e.mansion_chinese == "角"
        assert e.garden == "courage"
        assert e.quadrant == Quadrant.EAST

    def test_kaizen_engine(self):
        e = get_engine_entry("KaizenEngine")
        assert e.mansion_chinese == "昴"
        assert e.garden == "presence"
        assert e.quadrant == Quadrant.WEST

    def test_predictive_engine(self):
        e = get_engine_entry("PredictiveEngine")
        assert e.mansion_chinese == "斗"
        assert e.garden == "dharma"
        assert e.quadrant == Quadrant.NORTH

    def test_clone_army_engine(self):
        e = get_engine_entry("CloneArmyEngine")
        assert e.mansion_chinese == "女"
        assert e.garden == "connection"
        assert e.quadrant == Quadrant.NORTH

    def test_resonance_engine(self):
        e = get_engine_entry("ResonanceEngine")
        assert e.mansion_chinese == "豐"
        assert e.garden == "joy"
        assert e.quadrant == Quadrant.SOUTH

    def test_emergence_engine(self):
        e = get_engine_entry("EmergenceEngine")
        assert e.mansion_chinese == "壁"
        assert e.garden == "truth"
        assert e.quadrant == Quadrant.NORTH
        assert e.grimoire_chapter == 28

    def test_boundary_engine(self):
        e = get_engine_entry("BoundaryEngine")
        assert e.mansion_chinese == "氐"
        assert e.garden == "healing"
        assert e.quadrant == Quadrant.EAST


class TestSubEngineAbsorption:
    """Verify the 39 absorbed sub-engines are correctly mapped."""

    def test_total_absorbed_count(self):
        total = sum(len(e.absorbs) for e in ENGINE_REGISTRY)
        assert total == 39

    def test_all_absorbed_names_unique(self):
        all_absorbed = []
        for e in ENGINE_REGISTRY:
            all_absorbed.extend(e.absorbs)
        assert len(all_absorbed) == len(set(all_absorbed)), (
            f"Duplicate absorbed names: {[n for n in all_absorbed if all_absorbed.count(n) > 1]}"
        )

    def test_known_absorbed_engines(self):
        """Spot-check specific Tier 1 absorptions."""
        # QuantumGraphEngine absorbed by AccelerationEngine (slot 5)
        e = get_parent_engine("QuantumGraphEngine")
        assert e is not None
        assert e.engine_name == "AccelerationEngine"

        # HolographicPatternEngine absorbed by PatternEngine (slot 18)
        e = get_parent_engine("HolographicPatternEngine")
        assert e is not None
        assert e.engine_name == "PatternEngine"

        # GreatYearEngine absorbed by PredictiveEngine (slot 21)
        e = get_parent_engine("GreatYearEngine")
        assert e is not None
        assert e.engine_name == "PredictiveEngine"

        # RuleEngine absorbed by CloneArmyEngine (slot 23)
        e = get_parent_engine("RuleEngine")
        assert e is not None
        assert e.engine_name == "CloneArmyEngine"

        # PolymorphismEngine absorbed by ExportEngine (slot 11)
        e = get_parent_engine("PolymorphismEngine")
        assert e is not None
        assert e.engine_name == "ExportEngine"

        # _PyReplayEngine absorbed by ConsolidationEngine (slot 1)
        e = get_parent_engine("_PyReplayEngine")
        assert e is not None
        assert e.engine_name == "ConsolidationEngine"

    def test_pre_existing_absorbed_still_present(self):
        """Ensure the original 33 absorbed sub-engines are still mapped."""
        for name in (
            "CycleEngine",
            "WuXingEngine",
            "ReconsolidationEngine",
            "HeartEngine",
            "QuantumEngine",
            "ForecastEngine",
            "CapabilityDiscoveryEngine",
            "GrimoireEngine",
            "GraphEngine",
            "GraphEngineNeural",
            "GraphEngineCached",
            "CodeGenomeEngine",
            "PromptEngine",
            "ResonanceTransferEngine",
            "JuliaResonanceEngine",
            "HRREngine",
            "QuantizedHRREngine",
            "HRRCompositionEngine",
            "DGAEngine",
            "ContinuousEvolutionEngine",
            "MetaLearningEngine",
            "ApotheosisEngine",
            "EnhancedPatternEngine",
            "SubClusteringEngine",
            "NarrativeEngineStory",
            "ArtOfWarEngine",
            "MaturityEngine",
            "ForesightEngine",
            "PredictiveMaintenanceEngine",
            "GalacticTelepathyEngine",
            "LocalReasoningEngine",
            "CPUInferenceEngine",
            "NeuroScoreEngine",
        ):
            assert get_parent_engine(name) is not None, f"{name} has no parent engine"


class TestAffiliatedEngines:
    """Verify the 5 affiliated engines are correctly mapped."""

    def test_total_affiliated_count(self):
        total = sum(len(e.affiliated_engines) for e in ENGINE_REGISTRY)
        assert total == 5

    def test_all_affiliated_names_unique(self):
        all_aff = []
        for e in ENGINE_REGISTRY:
            all_aff.extend(e.affiliated_engines)
        assert len(all_aff) == len(set(all_aff))

    def test_known_affiliated_engines(self):
        cases = [
            ("MetaplasticityEngine", "ForgettingEngine"),
            ("HologramEngine", "EmbeddingEngine"),
            ("PersonaEngine", "CloneArmyEngine"),
            ("InteractionEngine", "SwarmEngine"),
            ("SymbolicEngine", "SerendipityEngine"),
        ]
        for sub_name, parent_name in cases:
            e = get_parent_engine(sub_name)
            assert e is not None, f"{sub_name} has no parent"
            assert e.engine_name == parent_name, (
                f"{sub_name} parent is {e.engine_name}, expected {parent_name}"
            )

    def test_affiliated_not_in_absorbs(self):
        """Affiliated engines should not also appear in absorbs."""
        all_absorbed = set()
        for e in ENGINE_REGISTRY:
            all_absorbed.update(e.absorbs)
        for e in ENGINE_REGISTRY:
            for aff in e.affiliated_engines:
                assert aff not in all_absorbed, (
                    f"{aff} is in both absorbs and affiliated_engines"
                )


class TestParentEngineLookup:
    def test_lookup_unknown_sub_engine(self):
        assert get_parent_engine("NonexistentEngine") is None

    def test_lookup_returns_engine_entry(self):
        e = get_parent_engine("QuantumEngine")
        assert isinstance(e, EngineEntry)

    def test_canonical_engines_have_no_parent(self):
        """Canonical engines should not appear as sub-engines of other slots."""
        canonical_names = {e.engine_name for e in ENGINE_REGISTRY}
        all_sub = set()
        for e in ENGINE_REGISTRY:
            all_sub.update(e.absorbs)
            all_sub.update(e.affiliated_engines)
        overlap = canonical_names & all_sub
        assert not overlap, f"Canonical engines also listed as sub-engines: {overlap}"


class TestEngineStatsWithSubEngines:
    def test_stats_include_sub_engine_counts(self):
        stats = get_engine_stats()
        assert stats["total_engines"] == 28
        assert stats["total_absorbed_sub_engines"] == 39
        assert stats["total_affiliated_engines"] == 5
        assert stats["total_all_engines"] == 72
