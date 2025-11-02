"""
WhiteMagic constants and configuration.
"""

from pathlib import Path
from typing import Dict, Set

# Version
VERSION = "2.1.0"  # Phases 1A & 1B complete

# Memory types
MEMORY_TYPE_SHORT_TERM = "short_term"
MEMORY_TYPE_LONG_TERM = "long_term"
MEMORY_TYPE_ARCHIVE = "archive"

VALID_MEMORY_TYPES = {MEMORY_TYPE_SHORT_TERM, MEMORY_TYPE_LONG_TERM}
ALL_MEMORY_TYPES = {MEMORY_TYPE_SHORT_TERM, MEMORY_TYPE_LONG_TERM, MEMORY_TYPE_ARCHIVE}

# Memory status
STATUS_ACTIVE = "active"
STATUS_ARCHIVED = "archived"

VALID_STATUSES = {STATUS_ACTIVE, STATUS_ARCHIVED}

# Default paths (relative to base_dir)
DEFAULT_MEMORY_DIR = "memory"
DEFAULT_SHORT_TERM_DIR = "memory/short_term"
DEFAULT_LONG_TERM_DIR = "memory/long_term"
DEFAULT_ARCHIVE_DIR = "memory/archive"
DEFAULT_METADATA_FILE = "memory/metadata.json"

# Retention and consolidation
DEFAULT_SHORT_TERM_RETENTION_DAYS = 7
DEFAULT_CONSOLIDATION_THRESHOLD = 5  # Minimum memories to trigger consolidation

# Auto-promotion tags
AUTO_PROMOTION_TAGS: Set[str] = {
    "heuristic",
    "pattern",
    "proven",
    "decision",
    "insight",
}

# Tag normalization
DEFAULT_NORMALIZE_TAGS = True

# Sorting options
SORT_BY_CREATED = "created"
SORT_BY_UPDATED = "updated"
SORT_BY_ACCESSED = "accessed"

VALID_SORT_OPTIONS = {SORT_BY_CREATED, SORT_BY_UPDATED, SORT_BY_ACCESSED}

# Tier context rules (tokens allocated per tier)
TIER_CONTEXT_RULES: Dict[int, Dict] = {
    0: {
        "short_term": {"limit": 2, "mode": "summary", "max_chars": 400},
        "long_term": {"limit": 0, "mode": "summary", "max_chars": 0},
    },
    1: {
        "short_term": {"limit": 5, "mode": "detailed", "max_chars": 1200},
        "long_term": {"limit": 2, "mode": "summary", "max_chars": 800},
    },
    2: {
        "short_term": {"limit": 10, "mode": "full", "max_chars": 2000},
        "long_term": {"limit": 5, "mode": "full", "max_chars": 2000},
    },
}

# API Configuration
API_KEY_LENGTH = 32  # bytes (64 hex characters)
API_KEY_PREFIX = "wm_"

# Rate limiting (requests per minute)
RATE_LIMIT_FREE = 60
RATE_LIMIT_PRO = 600
RATE_LIMIT_TEAM = 6000
RATE_LIMIT_ENTERPRISE = None  # Unlimited

# Storage limits (number of memories)
STORAGE_LIMIT_FREE = 10000
STORAGE_LIMIT_PRO = None  # Unlimited
STORAGE_LIMIT_TEAM = None  # Unlimited
STORAGE_LIMIT_ENTERPRISE = None  # Unlimited

# API Plans
PLAN_FREE = "free"
PLAN_PRO = "pro"
PLAN_TEAM = "team"
PLAN_ENTERPRISE = "enterprise"

VALID_PLANS = {PLAN_FREE, PLAN_PRO, PLAN_TEAM, PLAN_ENTERPRISE}

# File extensions
MEMORY_FILE_EXTENSION = ".md"

# Metadata fields
REQUIRED_METADATA_FIELDS = {"filename", "title", "type", "path", "created"}
OPTIONAL_METADATA_FIELDS = {
    "updated",
    "accessed",
    "tags",
    "status",
    "archived_at",
    "restored_at",
    "promoted_from",
}
