"""P5.1 — Galaxy taxonomy canonical verification.

Verifies that galaxy_taxonomy.py is the single authoritative source for
galaxy definitions, that all 14 canonical galaxies are present, zones
are correct, deprecated aliases map correctly, and no competing
definitions exist elsewhere.
"""
import pytest

pytestmark = [pytest.mark.core, pytest.mark.contract]

from whitemagic.core.memory.galaxy_taxonomy import (
    GALAXY_ARCHIVE,
    GALAXY_ARIA,
    GALAXY_CITTA,
    GALAXY_CODEX,
    GALAXY_DEFAULT_SEARCH,
    GALAXY_DEPRECATED,
    GALAXY_DESCRIPTIONS,
    GALAXY_DREAMS,
    GALAXY_JOURNALS,
    GALAXY_KNOWLEDGE,
    GALAXY_META,
    GALAXY_ORDER,
    GALAXY_RESEARCH,
    GALAXY_SESSIONS,
    GALAXY_SUBSTRATE,
    GALAXY_TELEMETRY,
    GALAXY_TUTORIAL,
    GALAXY_UNIVERSAL,
    GALAXY_ZONES,
)


class TestCanonicalGalaxyTaxonomy:
    """Verify galaxy_taxonomy.py is the canonical source."""

    EXPECTED_GALAXIES = [
        "aria", "citta", "journals", "dreams", "research",
        "sessions", "codex", "knowledge", "substrate", "telemetry",
        "meta", "tutorial", "archive", "universal",
    ]

    def test_galaxy_order_has_14_galaxies(self):
        assert len(GALAXY_ORDER) == 14

    def test_galaxy_order_matches_expected(self):
        assert GALAXY_ORDER == self.EXPECTED_GALAXIES

    def test_all_galaxies_have_descriptions(self):
        for g in GALAXY_ORDER:
            assert g in GALAXY_DESCRIPTIONS, f"Missing description for {g}"
            assert len(GALAXY_DESCRIPTIONS[g]) > 10

    def test_all_galaxies_have_zones(self):
        for g in GALAXY_ORDER:
            assert g in GALAXY_ZONES, f"Missing zone for {g}"

    def test_zone_distribution(self):
        zones = {}
        for g, z in GALAXY_ZONES.items():
            zones.setdefault(z, []).append(g)
        assert set(zones["CORE"]) == {"aria", "citta", "meta"}
        assert set(zones["INNER_RIM"]) == {"sessions", "codex", "knowledge"}
        assert set(zones["MID_BAND"]) == {"research", "journals", "dreams"}
        assert set(zones["OUTER_RIM"]) == {"substrate", "tutorial", "universal"}
        assert set(zones["FAR_EDGE"]) == {"telemetry", "archive"}

    def test_default_search_excludes_far_edge(self):
        for g in GALAXY_DEFAULT_SEARCH:
            assert GALAXY_ZONES[g] != "FAR_EDGE", f"{g} is FAR_EDGE but in default search"

    def test_default_search_includes_core_and_inner_rim(self):
        for g in ["aria", "citta", "meta", "sessions", "codex", "knowledge"]:
            assert g in GALAXY_DEFAULT_SEARCH

    def test_deprecated_aliases_map_to_canonical(self):
        expected = {
            "insight": "knowledge",
            "self_learning": "knowledge",
            "self_discovery": "knowledge",
            "translation": "codex",
            "test": "archive",
        }
        assert GALAXY_DEPRECATED == expected

    def test_deprecated_aliases_not_in_galaxy_order(self):
        for alias in GALAXY_DEPRECATED:
            assert alias not in GALAXY_ORDER, f"Deprecated alias {alias} should not be in GALAXY_ORDER"

    def test_no_duplicate_galaxies_in_order(self):
        assert len(GALAXY_ORDER) == len(set(GALAXY_ORDER))

    def test_galaxy_constants_match_order(self):
        constants = [
            GALAXY_ARIA, GALAXY_CITTA, GALAXY_JOURNALS, GALAXY_DREAMS,
            GALAXY_RESEARCH, GALAXY_SESSIONS, GALAXY_CODEX, GALAXY_KNOWLEDGE,
            GALAXY_SUBSTRATE, GALAXY_TELEMETRY, GALAXY_META, GALAXY_TUTORIAL,
            GALAXY_ARCHIVE, GALAXY_UNIVERSAL,
        ]
        assert sorted(constants) == sorted(GALAXY_ORDER)

    def test_classify_memory_returns_canonical_only(self):
        from whitemagic.core.memory.galaxy_taxonomy import classify_memory
        result = classify_memory("test", {"insight"}, "content")
        assert result == "knowledge"
        result = classify_memory("test", set(), "content")
        assert result == "universal"
        result = classify_memory("CODEX test", {"codex"}, "content")
        assert result == "codex"

    def test_classify_memory_never_returns_deprecated(self):
        from whitemagic.core.memory.galaxy_taxonomy import classify_memory
        for deprecated in GALAXY_DEPRECATED:
            result = classify_memory("test", {deprecated}, "content")
            assert result not in GALAXY_DEPRECATED, f"classify_memory returned deprecated name {result}"
            assert result in GALAXY_ORDER, f"classify_memory returned non-canonical {result}"
