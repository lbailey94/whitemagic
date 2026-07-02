# ruff: noqa: BLE001
"""Tests for the ARIA CANON epistemic tagging system."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from whitemagic.core.intelligence.epistemic import (
    TAG_RESPONSE_STYLES,
    TIER_CITABLE,
    TIER_DEFAULT_TAG,
    CanonEntry,
    EpistemicAssessment,
    EpistemicTag,
    EpistemicTagger,
    SourceTier,
    get_epistemic_tagger,
)


class TestEpistemicTags:
    """Test epistemic tag definitions and mappings."""

    def test_tag_values(self):
        """All five epistemic tags exist."""
        assert EpistemicTag.PROVEN.value == "Proven"
        assert EpistemicTag.PROMISING.value == "Promising"
        assert EpistemicTag.CONTESTED.value == "Contested"
        assert EpistemicTag.SPECULATIVE.value == "Speculative"
        assert EpistemicTag.MYTHOPOETIC.value == "Mythopoetic"

    def test_tag_response_styles(self):
        """Every tag has a response style."""
        for tag in EpistemicTag:
            assert tag in TAG_RESPONSE_STYLES

    def test_tier_default_tags(self):
        """Every tier maps to a default tag."""
        for tier in SourceTier:
            assert tier in TIER_DEFAULT_TAG

    def test_tier_citable_mapping(self):
        """Tiers 1-3 are citable, 4-5 are not."""
        assert TIER_CITABLE[SourceTier.TIER_1] is True
        assert TIER_CITABLE[SourceTier.TIER_2] is True
        assert TIER_CITABLE[SourceTier.TIER_3] is True
        assert TIER_CITABLE[SourceTier.TIER_4] is False
        assert TIER_CITABLE[SourceTier.TIER_5] is False


class TestEpistemicTagger:
    """Test the epistemic tagger."""

    @pytest.fixture(autouse=True)
    def _reset_tagger(self):
        """Reset the global tagger between tests."""
        import whitemagic.core.intelligence.epistemic as epi_mod
        epi_mod._tagger = None
        yield
        epi_mod._tagger = None

    def test_assess_tier_1_source(self):
        """DOI URL classifies as Tier 1."""
        tagger = EpistemicTagger()
        result = tagger.assess(
            claim="The framework was published in a peer-reviewed journal.",
            source_url="https://doi.org/10.1234/test",
            source_title="Test Paper",
        )
        assert result.tier == SourceTier.TIER_1
        assert result.tag == EpistemicTag.PROVEN
        assert result.citable
        assert result.confidence > 0.9

    def test_assess_arxiv_source(self):
        """arXiv URL classifies as Tier 2."""
        tagger = EpistemicTagger()
        result = tagger.assess(
            claim="Early results suggest promising outcomes.",
            source_url="https://arxiv.org/abs/2026.12345",
        )
        assert result.tier == SourceTier.TIER_2
        assert result.tag == EpistemicTag.PROMISING

    def test_assess_blog_source(self):
        """Medium blog classifies as Tier 3."""
        tagger = EpistemicTagger()
        result = tagger.assess(
            claim="This approach might work.",
            source_url="https://medium.com/@expert/some-post",
        )
        assert result.tier == SourceTier.TIER_3

    def test_assess_internal_source(self):
        """Internal docs classify as Tier 4 and are not citable."""
        tagger = EpistemicTagger()
        result = tagger.assess(
            claim="Our internal strategy document says...",
            source_url="https://example.com/grant_proposal",
        )
        assert result.tier == SourceTier.TIER_4
        assert not result.citable

    def test_assess_forbidden_source(self):
        """Twitter/X classifies as Tier 5."""
        tagger = EpistemicTagger()
        result = tagger.assess(
            claim="Someone tweeted about this.",
            source_url="https://twitter.com/user/status/123",
        )
        assert result.tier == SourceTier.TIER_5
        assert not result.citable

    def test_assess_no_source(self):
        """No source defaults to Tier 3 (provisional)."""
        tagger = EpistemicTagger()
        result = tagger.assess(claim="I think this might be the case.")
        assert result.tier == SourceTier.TIER_3
        assert "No source" in result.reasoning

    def test_assess_with_override_tier(self):
        """Override tier skips URL classification."""
        tagger = EpistemicTagger()
        result = tagger.assess(
            claim="Test claim",
            source_url="https://example.com",
            override_tier=SourceTier.TIER_1,
        )
        assert result.tier == SourceTier.TIER_1
        assert "manually specified" in result.reasoning

    def test_refusal_medical(self):
        """Medical advice triggers refusal."""
        tagger = EpistemicTagger()
        result = tagger.assess(claim="You should take this medication for your symptoms.")
        assert result.refusal is not None
        assert "medical advice" in result.refusal.lower()

    def test_refusal_financial(self):
        """Financial advice triggers refusal."""
        tagger = EpistemicTagger()
        result = tagger.assess(claim="You should invest in this stock.")
        assert result.refusal is not None
        assert "financial advice" in result.refusal.lower()

    def test_refusal_uap(self):
        """UAP claims as fact trigger refusal."""
        tagger = EpistemicTagger()
        result = tagger.assess(claim="UAP confirmed as aliens real")
        assert result.refusal is not None
        assert "Promising" in result.refusal

    def test_no_refusal_for_safe_claim(self):
        """Safe claims don't trigger refusal."""
        tagger = EpistemicTagger()
        result = tagger.assess(claim="The system uses embeddings for search.")
        assert result.refusal is None

    def test_get_refusal_response_directly(self):
        """get_refusal_response works standalone."""
        tagger = EpistemicTagger()
        refusal = tagger.get_refusal_response("should I take this medication?")
        assert refusal is not None
        assert "medical" in refusal.lower()

    def test_register_source(self):
        """Registered sources are stored and retrievable."""
        tagger = EpistemicTagger()
        entry = tagger.register_source(
            title="NIST CAISI Framework",
            url="https://nist.gov/caisi",
            tier=SourceTier.TIER_1,
            reviewed_by="Lucas",
        )
        assert entry.title == "NIST CAISI Framework"
        assert entry.tier == SourceTier.TIER_1

        registry = tagger.get_registry()
        assert "https://nist.gov/caisi" in registry

    def test_registered_source_used_in_assessment(self):
        """Registered sources are used when assessing claims."""
        tagger = EpistemicTagger()
        tagger.register_source(
            title="Known Safe Source",
            url="https://example.com/safe",
            tier=SourceTier.TIER_1,
            reviewed_by="Lucas",
        )

        result = tagger.assess(
            claim="This is a proven fact.",
            source_url="https://example.com/safe",
        )
        assert result.tier == SourceTier.TIER_1
        assert "registry" in result.reasoning.lower()

    def test_stale_source_detection(self):
        """Sources older than 90 days are flagged as stale."""
        tagger = EpistemicTagger()
        entry = tagger.register_source(
            title="Old Source",
            url="https://example.com/old",
            tier=SourceTier.TIER_2,
        )
        # Manually backdate
        entry.reviewed_at = datetime.now() - timedelta(days=100)

        stale = tagger.get_stale_sources()
        assert len(stale) == 1
        assert stale[0]["title"] == "Old Source"

    def test_fresh_source_not_stale(self):
        """Recently reviewed sources are not stale."""
        tagger = EpistemicTagger()
        tagger.register_source(
            title="Fresh Source",
            url="https://example.com/fresh",
            tier=SourceTier.TIER_1,
        )
        stale = tagger.get_stale_sources()
        assert len(stale) == 0

    def test_format_citation(self):
        """Citation formatting works correctly."""
        assessment = EpistemicAssessment(
            tag=EpistemicTag.PROVEN,
            tier=SourceTier.TIER_1,
            citable=True,
            confidence=0.95,
            reasoning="Test",
            source_url="https://nist.gov/caisi",
            source_title="NIST CAISI Framework",
        )
        citation = assessment.format_citation()
        assert "[Source]" in citation
        assert "NIST CAISI Framework" in citation
        assert "[Proven]" in citation

    def test_format_inline_tag(self):
        """Inline tag formatting works."""
        assessment = EpistemicAssessment(
            tag=EpistemicTag.PROMISING,
            tier=SourceTier.TIER_2,
            citable=True,
            confidence=0.8,
            reasoning="Test",
        )
        assert assessment.format_inline_tag() == "[Promising]"

    def test_tag_text_adds_tags(self):
        """tag_text adds epistemic tags to claim-like sentences."""
        tagger = EpistemicTagger()
        text = "Research shows that embeddings improve search. The sky is blue."
        tagged = tagger.tag_text(text)
        # At least one tag should be added (the "Research shows" sentence)
        assert "[" in tagged

    def test_validate_citation_valid(self):
        """Valid citation passes validation."""
        tagger = EpistemicTagger()
        citation = (
            '[Source] NIST, "CAISI: AI Safety Framework," Feb 2026. '
            "https://nist.gov/caisi. [Proven]"
        )
        result = tagger.validate_citation(citation)
        assert result["valid"]
        assert len(result["issues"]) == 0

    def test_validate_citation_missing_tag(self):
        """Citation without epistemic tag fails validation."""
        tagger = EpistemicTagger()
        citation = '[Source] NIST, "CAISI," Feb 2026. https://nist.gov/caisi.'
        result = tagger.validate_citation(citation)
        assert not result["valid"]
        assert "Missing epistemic tag" in result["issues"]

    def test_validate_citation_missing_url(self):
        """Citation without URL fails validation."""
        tagger = EpistemicTagger()
        citation = '[Source] NIST, "CAISI," Feb 2026. [Proven]'
        result = tagger.validate_citation(citation)
        assert not result["valid"]
        assert "Missing URL or DOI" in result["issues"]

    def test_validate_citation_missing_date(self):
        """Citation without date fails validation."""
        tagger = EpistemicTagger()
        citation = '[Source] NIST, "CAISI Framework." https://nist.gov/caisi. [Proven]'
        result = tagger.validate_citation(citation)
        assert not result["valid"]
        assert "Missing publication date" in result["issues"]

    def test_detect_tag_in_content(self):
        """Pre-existing tags in content are detected."""
        assert EpistemicTagger._detect_tag_in_content(
            "This is [Proven] to work."
        ) == EpistemicTag.PROVEN
        assert EpistemicTagger._detect_tag_in_content(
            "This is [Speculative] at best."
        ) == EpistemicTag.SPECULATIVE
        assert EpistemicTagger._detect_tag_in_content("No tags here.") is None

    def test_get_epistemic_tagger_singleton(self):
        """Global tagger is a singleton."""
        t1 = get_epistemic_tagger()
        t2 = get_epistemic_tagger()
        assert t1 is t2

    def test_assessment_to_dict(self):
        """Assessment serializes to dict correctly."""
        assessment = EpistemicAssessment(
            tag=EpistemicTag.CONTESTED,
            tier=SourceTier.TIER_3,
            citable=True,
            confidence=0.6,
            reasoning="Test reasoning",
        )
        d = assessment.to_dict()
        assert d["tag"] == "Contested"
        assert d["tier"] == "tier_3"
        assert d["citable"] is True
        assert d["confidence"] == 0.6

    def test_canon_entry_is_stale(self):
        """CanonEntry staleness check works."""
        entry = CanonEntry(
            title="Test",
            url="https://example.com",
            tier=SourceTier.TIER_1,
            tag=EpistemicTag.PROVEN,
            reviewed_by="Lucas",
            reviewed_at=datetime.now() - timedelta(days=100),
        )
        assert entry.is_stale()

    def test_canon_entry_fresh(self):
        """Fresh CanonEntry is not stale."""
        entry = CanonEntry(
            title="Test",
            url="https://example.com",
            tier=SourceTier.TIER_1,
            tag=EpistemicTag.PROVEN,
            reviewed_by="Lucas",
            reviewed_at=datetime.now() - timedelta(days=10),
        )
        assert not entry.is_stale()
