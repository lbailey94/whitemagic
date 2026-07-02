# ruff: noqa: BLE001
"""ARIA CANON Epistemic Tagging System
======================================

Implements the curation rubric defined in `docs/ARIA_CANON_RUBRIC.md`.

Provides:
  - Epistemic tags: [Proven], [Promising], [Contested], [Speculative], [Mythopoetic]
  - Source tier classification (Tier 1-5)
  - Content tagging with epistemic confidence
  - Refusal triggers for medical, financial, and unverified claims
  - Citation format validation
  - Approval workflow integration

The system is designed to be used by Aria (or any agent) when generating
responses that cite sources. It ensures every claim carries an epistemic
tag and that sources are ranked by trustworthiness.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


# --- Epistemic Tags ---

class EpistemicTag(StrEnum):
    """Epistemic confidence tags for claims."""

    PROVEN = "Proven"
    PROMISING = "Promising"
    CONTESTED = "Contested"
    SPECULATIVE = "Speculative"
    MYTHOPOETIC = "Mythopoetic"


# --- Source Tiers ---

class SourceTier(StrEnum):
    """Source trustworthiness hierarchy."""

    TIER_1 = "tier_1"  # Authoritative (peer-reviewed, gov, tested code)
    TIER_2 = "tier_2"  # Credible (arXiv, conference papers, canonical docs)
    TIER_3 = "tier_3"  # Provisional (expert blogs, message board, analyst reports)
    TIER_4 = "tier_4"  # Internal only (grants, planning docs)
    TIER_5 = "tier_5"  # Forbidden (mythopoetic as fact, unverified social, advice)


# Tag → response style mapping
TAG_RESPONSE_STYLES: dict[EpistemicTag, str] = {
    EpistemicTag.PROVEN: "Confident, cite source",
    EpistemicTag.PROMISING: "Cautious optimism, note uncertainty",
    EpistemicTag.CONTESTED: "Present both sides, do not pick",
    EpistemicTag.SPECULATIVE: "Flag as unvalidated, offer context",
    EpistemicTag.MYTHOPOETIC: "Frame as narrative/cultural, not empirical",
}

# Tier → default epistemic tag
TIER_DEFAULT_TAG: dict[SourceTier, EpistemicTag] = {
    SourceTier.TIER_1: EpistemicTag.PROVEN,
    SourceTier.TIER_2: EpistemicTag.PROMISING,
    SourceTier.TIER_3: EpistemicTag.CONTESTED,
    SourceTier.TIER_4: EpistemicTag.SPECULATIVE,
    SourceTier.TIER_5: EpistemicTag.MYTHOPOETIC,
}

# Tier → whether it can be cited publicly
TIER_CITABLE: dict[SourceTier, bool] = {
    SourceTier.TIER_1: True,
    SourceTier.TIER_2: True,
    SourceTier.TIER_3: True,
    SourceTier.TIER_4: False,
    SourceTier.TIER_5: False,
}


# --- Refusal Triggers ---

REFUSAL_CATEGORIES = {
    "medical": {
        "keywords": [
            "diagnose", "prescribe", "medication", "dosage", "treatment plan",
            "medical advice", "should i take", "is this symptom",
        ],
        "response": (
            "I can't provide medical advice. Please consult a qualified "
            "healthcare professional."
        ),
    },
    "financial": {
        "keywords": [
            "invest in", "buy stock", "should i invest", "financial advice",
            "portfolio recommendation", "trade recommendation",
        ],
        "response": (
            "I don't give financial advice. Here's what the data shows, "
            "but you should consult a qualified financial advisor."
        ),
    },
    "unverified_uap": {
        "keywords": [
            "uap confirmed", "aliens real", "ufo proof", "extraterrestrial confirmed",
        ],
        "response": (
            "The evidence for UAP is classified as [Promising]. "
            "Here's what's publicly known from AARO and NASA reports."
        ),
    },
    "no_source": {
        "keywords": [],
        "response": (
            "I don't have enough information to answer that. "
            "Here's what I'd need to find out."
        ),
    },
    "conflict_of_interest": {
        "keywords": [],
        "response": (
            "I have a structural gap in my knowledge here. "
            "Let me point you to external resources."
        ),
    },
}


# --- Source Classification Patterns ---

TIER_1_PATTERNS = [
    r"doi\.org/", r"pubmed\.ncbi", r"nist\.gov", r"nasa\.gov",
    r"iea\.org", r"\.edu/[A-Z].*journal", r"academic\.oup\.com",
    r"nature\.com/articles/", r"science\.org/doi/",
]

TIER_2_PATTERNS = [
    r"arxiv\.org", r"dl\.acm\.org/doi", r"ieee\.org/document",
    r"docs\.rs/", r"docs\.python\.org", r"nodejs\.org/api",
    r"rust-lang\.org", r"grimoire/", r"docs/.*\.md",
]

TIER_3_PATTERNS = [
    r"medium\.com", r"substack\.com", r"dev\.to",
    r"message_board/", r"gartner\.com", r"mckinsey\.com",
    r"reuters\.com", r"nature\.com/news",
]

TIER_4_PATTERNS = [
    r"grant", r"roadmap", r"objectives_plan", r"@internal", r"@private",
    r"competitive_analysis", r"funding_strategy",
]

TIER_5_PATTERNS = [
    r"mythopoetic", r"twitter\.com", r"x\.com", r"facebook\.com",
    r"reddit\.com", r"tiktok\.com",
]


@dataclass
class EpistemicAssessment:
    """Result of assessing a claim or source."""

    tag: EpistemicTag
    tier: SourceTier
    citable: bool
    confidence: float  # 0.0-1.0
    reasoning: str
    refusal: str | None = None  # Set if a refusal trigger fired
    source_url: str | None = None
    source_title: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "tag": self.tag.value,
            "tier": self.tier.value,
            "citable": self.citable,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "refusal": self.refusal,
            "source_url": self.source_url,
            "source_title": self.source_title,
            "timestamp": self.timestamp.isoformat(),
        }

    def format_citation(self) -> str:
        """Format as an ARIA CANON citation string."""
        if self.source_url and self.source_title:
            return f"[Source] {self.source_title}. {self.source_url}. [{self.tag.value}]"
        if self.source_title:
            return f"[Source] {self.source_title}. [{self.tag.value}]"
        return f"[{self.tag.value}]"

    def format_inline_tag(self) -> str:
        """Format as an inline epistemic tag for use in text."""
        return f"[{self.tag.value}]"


@dataclass
class CanonEntry:
    """A registered ARIA CANON source entry."""

    title: str
    url: str
    tier: SourceTier
    tag: EpistemicTag
    reviewed_by: str  # "Lucas", "Cascade", etc.
    reviewed_at: datetime
    expires_at: datetime | None = None  # Quarterly review cycle
    notes: str = ""

    def is_stale(self) -> bool:
        """Check if this entry needs review (>90 days since review)."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        age = (datetime.now() - self.reviewed_at).days
        return age > 90

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "tier": self.tier.value,
            "tag": self.tag.value,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "notes": self.notes,
            "is_stale": self.is_stale(),
        }


class EpistemicTagger:
    """Tags content with epistemic confidence levels.

    Thread-safe.  Maintains a registry of reviewed sources and provides
    classification for new, unreviewed sources.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._registry: dict[str, CanonEntry] = {}  # url → entry
        self._review_queue: list[dict[str, Any]] = []

    def assess(
        self,
        claim: str,
        source_url: str | None = None,
        source_title: str | None = None,
        override_tier: SourceTier | None = None,
    ) -> EpistemicAssessment:
        """Assess a claim and return an epistemic assessment.

        Args:
            claim: The text of the claim being made.
            source_url: URL of the source being cited.
            source_title: Title of the source.
            override_tier: Manually specify the source tier (skips classification).

        Returns:
            EpistemicAssessment with tag, tier, and confidence.
        """
        # 1. Check refusal triggers first
        refusal = self._check_refusal(claim)
        if refusal:
            return EpistemicAssessment(
                tag=EpistemicTag.SPECULATIVE,
                tier=SourceTier.TIER_5,
                citable=False,
                confidence=0.0,
                reasoning="Refusal trigger activated",
                refusal=refusal,
                source_url=source_url,
                source_title=source_title,
            )

        # 2. Determine source tier
        if override_tier:
            tier = override_tier
            reasoning = f"Tier manually specified as {tier.value}"
        elif source_url:
            # Check registry first
            entry = self._registry.get(source_url)
            if entry and not entry.is_stale():
                tier = entry.tier
                tag = entry.tag
                reasoning = f"Source in registry (reviewed by {entry.reviewed_by})"
                return EpistemicAssessment(
                    tag=tag,
                    tier=tier,
                    citable=TIER_CITABLE[tier],
                    confidence=self._tier_to_confidence(tier),
                    reasoning=reasoning,
                    source_url=source_url,
                    source_title=source_title or entry.title,
                )
            # Classify by URL patterns
            tier = self._classify_source(source_url)
            reasoning = f"Source classified as {tier.value} by URL pattern"
        else:
            # No source — speculative at best
            tier = SourceTier.TIER_3
            reasoning = "No source provided — defaulting to provisional"

        # 3. Determine epistemic tag
        tag = TIER_DEFAULT_TAG[tier]

        # 4. Check if claim content suggests a different tag
        content_tag = self._detect_tag_in_content(claim)
        if content_tag:
            tag = content_tag
            reasoning += f"; content suggests [{tag.value}]"

        # 5. Non-citable sources trigger flagging
        citable = TIER_CITABLE[tier]
        if not citable:
            reasoning += "; source is internal-only — do not cite publicly"

        return EpistemicAssessment(
            tag=tag,
            tier=tier,
            citable=citable,
            confidence=self._tier_to_confidence(tier),
            reasoning=reasoning,
            source_url=source_url,
            source_title=source_title,
        )

    def register_source(
        self,
        title: str,
        url: str,
        tier: SourceTier,
        tag: EpistemicTag | None = None,
        reviewed_by: str = "Lucas",
        notes: str = "",
    ) -> CanonEntry:
        """Register a reviewed source in the CANON registry."""
        if tag is None:
            tag = TIER_DEFAULT_TAG[tier]

        entry = CanonEntry(
            title=title,
            url=url,
            tier=tier,
            tag=tag,
            reviewed_by=reviewed_by,
            reviewed_at=datetime.now(),
            notes=notes,
        )

        with self._lock:
            self._registry[url] = entry

        logger.info(
            "CANON source registered: %s (%s, %s)",
            title[:50],
            tier.value,
            tag.value,
        )
        return entry

    def get_registry(self) -> dict[str, dict[str, Any]]:
        """Get all registered sources."""
        with self._lock:
            return {url: entry.to_dict() for url, entry in self._registry.items()}

    def get_stale_sources(self) -> list[dict[str, Any]]:
        """Get sources that need quarterly review."""
        with self._lock:
            return [
                entry.to_dict()
                for entry in self._registry.values()
                if entry.is_stale()
            ]

    def tag_text(self, text: str) -> str:
        """Add inline epistemic tags to a text block.

        Scans for claim-like sentences and appends the appropriate tag.
        This is a lightweight heuristic — for production use, pair with
        an LLM that can identify claim boundaries.
        """
        # Find sentences that look like claims (contain factual assertions)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        tagged_sentences = []

        for sentence in sentences:
            # Check if sentence contains a claim indicator
            is_claim = any(
                indicator in sentence.lower()
                for indicator in [
                    "is", "are", "was", "were", "shows", "demonstrates",
                    "proves", "evidence", "study", "research", "found",
                    "according to", "reported", "published",
                ]
            )

            if is_claim:
                # Quick assessment
                assessment = self.assess(sentence)
                if assessment.refusal:
                    tagged_sentences.append(f"{sentence} {assessment.refusal}")
                elif assessment.tag != EpistemicTag.PROVEN:
                    tagged_sentences.append(
                        f"{sentence} {assessment.format_inline_tag()}"
                    )
                else:
                    tagged_sentences.append(sentence)
            else:
                tagged_sentences.append(sentence)

        return " ".join(tagged_sentences)

    def validate_citation(self, citation: str) -> dict[str, Any]:
        """Validate an ARIA CANON citation format.

        Expected format: [Source] Author/Org, "Title," Date. URL/DOI. [Tag]
        """
        issues: list[str] = []

        # Check for [Source] prefix
        if not citation.startswith("[Source]"):
            issues.append("Missing [Source] prefix")

        # Check for epistemic tag
        tag_match = re.search(r'\[(Proven|Promising|Contested|Speculative|Mythopoetic)\]', citation)
        if not tag_match:
            issues.append("Missing epistemic tag")
        else:
            tag = EpistemicTag(tag_match.group(1))
            # Check if tag is appropriate for the source
            if tag == EpistemicTag.MYTHOPOETIC and "factual" in citation.lower():
                issues.append("[Mythopoetic] tag used with factual claim")

        # Check for URL or DOI
        if not re.search(r'https?://|doi\.org/', citation):
            issues.append("Missing URL or DOI")

        # Check for date
        if not re.search(r'\b(19|20)\d{2}\b', citation):
            issues.append("Missing publication date")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "citation": citation,
        }

    def get_refusal_response(self, claim: str) -> str | None:
        """Check if a claim triggers a refusal response.

        Returns the refusal message if triggered, None otherwise.
        """
        return self._check_refusal(claim)

    def _check_refusal(self, text: str) -> str | None:
        """Check text against all refusal triggers."""
        text_lower = text.lower()

        for category, config in REFUSAL_CATEGORIES.items():
            if not config["keywords"]:
                continue
            for kw in config["keywords"]:
                if kw in text_lower:
                    return config["response"]

        return None

    def _classify_source(self, url: str) -> SourceTier:
        """Classify a source URL into a tier based on patterns."""
        url_lower = url.lower()

        # Check Tier 5 first (forbidden)
        for pattern in TIER_5_PATTERNS:
            if re.search(pattern, url_lower):
                return SourceTier.TIER_5

        # Check Tier 1 (authoritative)
        for pattern in TIER_1_PATTERNS:
            if re.search(pattern, url_lower):
                return SourceTier.TIER_1

        # Check Tier 2 (credible)
        for pattern in TIER_2_PATTERNS:
            if re.search(pattern, url_lower):
                return SourceTier.TIER_2

        # Check Tier 3 (provisional)
        for pattern in TIER_3_PATTERNS:
            if re.search(pattern, url_lower):
                return SourceTier.TIER_3

        # Check Tier 4 (internal)
        for pattern in TIER_4_PATTERNS:
            if re.search(pattern, url_lower):
                return SourceTier.TIER_4

        # Unknown — default to provisional
        return SourceTier.TIER_3

    @staticmethod
    def _tier_to_confidence(tier: SourceTier) -> float:
        """Map a source tier to a confidence score."""
        return {
            SourceTier.TIER_1: 0.95,
            SourceTier.TIER_2: 0.80,
            SourceTier.TIER_3: 0.60,
            SourceTier.TIER_4: 0.30,
            SourceTier.TIER_5: 0.05,
        }[tier]

    @staticmethod
    def _detect_tag_in_content(text: str) -> EpistemicTag | None:
        """Detect if content already contains an epistemic tag."""
        for tag in EpistemicTag:
            if f"[{tag.value}]" in text:
                return tag
        return None


# --- Global instance ---

_tagger: EpistemicTagger | None = None
_tagger_lock = threading.Lock()


def get_epistemic_tagger() -> EpistemicTagger:
    """Get the global epistemic tagger instance."""
    global _tagger
    if _tagger is None:
        with _tagger_lock:
            if _tagger is None:
                _tagger = EpistemicTagger()
    return _tagger
