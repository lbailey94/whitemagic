"""Tier-specific configuration templates."""

from typing import Dict, Any, Tuple

# Tier information for display
TIER_INFO: Dict[str, Tuple[str, str, str]] = {
    "personal": (
        "Personal AI Companion",
        "For journaling, planning, creativity, and daily life",
        "🌟 Privacy-first, simple, zero-config approach",
    ),
    "power": (
        "Development & Freelance",
        "For project memory, code context, and deep work",
        "⚡ Powerful features, semantic search, auto-archival",
    ),
    "team": (
        "Team Collaboration",
        "For shared knowledge, onboarding, and team brain",
        "👥 Shared spaces, draft-review workflows",
    ),
    "regulated": (
        "Regulated Domain",
        "For medical, legal, government with strict requirements",
        "🔒 Per-case isolation, full audit trails, compliance-ready",
    ),
}

# Tier-specific configuration templates
TIER_CONFIGS: Dict[str, Dict[str, Any]] = {
    "personal": {
        "tier": "personal",
        "lifecycle": {
            "scratch_retention_days": 1,
            "working_retention_days": 30,
            "auto_archive_enabled": False,
            "archive_retention_forever": True,
        },
        "spaces": ["personal"],
        "features": {
            "draft_review_enabled": False,
            "audit_required": False,
            "strict_isolation": False,
        },
        "recommendations": {
            "embeddings": "local",  # Privacy-first
            "auto_archive": False,  # Manual control
        },
    },
    "power": {
        "tier": "power",
        "lifecycle": {
            "scratch_retention_days": 1,
            "working_retention_days": 90,
            "auto_archive_enabled": True,
            "archive_retention_forever": True,
        },
        "spaces": [],  # User creates project spaces
        "features": {
            "draft_review_enabled": False,
            "audit_required": False,
            "strict_isolation": False,
        },
        "recommendations": {
            "embeddings": "local",  # Best of both worlds
            "auto_archive": True,  # Automation
        },
    },
    "team": {
        "tier": "team",
        "lifecycle": {
            "scratch_retention_days": 7,
            "working_retention_days": 180,
            "auto_archive_enabled": True,
            "archive_retention_forever": True,
        },
        "spaces": ["shared"],
        "features": {
            "draft_review_enabled": True,
            "audit_required": False,
            "strict_isolation": False,
        },
        "recommendations": {
            "embeddings": "openai",  # Consistent across team
            "auto_archive": True,
        },
    },
    "regulated": {
        "tier": "regulated",
        "lifecycle": {
            "scratch_retention_days": 0,  # No scratch layer
            "working_retention_days": None,  # Manual only
            "auto_archive_enabled": False,
            "archive_retention_forever": True,
        },
        "spaces": [],  # Per-case isolation
        "features": {
            "draft_review_enabled": False,
            "audit_required": True,
            "strict_isolation": True,
        },
        "recommendations": {
            "embeddings": "local",  # Data stays local
            "auto_archive": False,  # Explicit only
        },
    },
}


def get_tier_display_name(tier: str) -> str:
    """Get display name for a tier."""
    return TIER_INFO[tier][0]


def get_tier_description(tier: str) -> str:
    """Get description for a tier."""
    return TIER_INFO[tier][1]


def get_tier_highlight(tier: str) -> str:
    """Get highlight/benefit for a tier."""
    return TIER_INFO[tier][2]
