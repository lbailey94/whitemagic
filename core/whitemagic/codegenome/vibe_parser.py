"""Vibe Parser — Xianfeng-tier natural language to template query parser.

Maps vague "vibe" prompts ("make a REST endpoint") to specific CodeGenome
template queries using lightweight keyword matching. Designed for the
fast, cheap Xianfeng tier of the AsyncThoughtCloneArmy.

Usage:
    parser = get_vibe_parser()
    query = parser.parse("I need a FastAPI endpoint for items")
    # -> {"template_name": "fastapi_endpoint", "variables": {"path": "/items", "name": "items"}}
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Vibe keyword → template mapping
# ---------------------------------------------------------------------------

_VIBE_MAP: dict[str, str] = {
    # FastAPI / REST
    "fastapi": "fastapi_endpoint",
    "endpoint": "fastapi_endpoint",
    "route": "fastapi_endpoint",
    "api": "fastapi_endpoint",
    "rest": "fastapi_endpoint",
    "get endpoint": "fastapi_endpoint",
    "post endpoint": "fastapi_endpoint",
    "http endpoint": "fastapi_endpoint",
    # Testing
    "pytest": "pytest_fixture",
    "fixture": "pytest_fixture",
    "test fixture": "pytest_fixture",
    "setup fixture": "pytest_fixture",
    # Models
    "pydantic": "pydantic_model",
    "model": "pydantic_model",
    "schema": "pydantic_model",
    "validation": "pydantic_model",
    "dataclass": "pydantic_model",
    "pydantic settings": "pydantic_settings",
    "settings": "pydantic_settings",
    "config": "pydantic_settings",
    "env config": "pydantic_settings",
    # Database
    "sqlalchemy": "sqlalchemy_model",
    "orm": "sqlalchemy_model",
    "database model": "sqlalchemy_model",
    "table": "sqlalchemy_model",
    "declarative": "sqlalchemy_model",
    # DevOps
    "docker": "dockerfile",
    "dockerfile": "dockerfile",
    "container": "dockerfile",
    "image": "dockerfile",
    "github action": "github_action",
    "github workflow": "github_action",
    "ci": "github_action",
    "ci/cd": "github_action",
    "workflow": "github_action",
    # Kabbalistic / Gnostic aliases (esoteric keyword layer)
    "sefirah model": "pydantic_model",
    "emanation schema": "pydantic_model",
    "tree schema": "pydantic_model",
    "divine model": "pydantic_model",
    "keter config": "pydantic_settings",
    "crown settings": "pydantic_settings",
    "divine config": "pydantic_settings",
    "supernal config": "pydantic_settings",
    "gevurah gate": "pytest_fixture",
    "severity check": "pytest_fixture",
    "boundary test": "pytest_fixture",
    "qliphoth defense": "pytest_fixture",
    "demiurge gate": "pytest_fixture",
    "binah structure": "sqlalchemy_model",
    "understanding schema": "sqlalchemy_model",
    "form container": "sqlalchemy_model",
    "tiferet endpoint": "fastapi_endpoint",
    "beauty api": "fastapi_endpoint",
    "harmony route": "fastapi_endpoint",
    "balance endpoint": "fastapi_endpoint",
    "yesod container": "dockerfile",
    "foundation image": "dockerfile",
    "malkuth deploy": "dockerfile",
    "kingdom image": "dockerfile",
    "daat workflow": "github_action",
    "knowledge pipeline": "github_action",
    "hidden action": "github_action",
    "pleroma flow": "github_action",
}

# Tier inference from intent keywords
_TIER_HINTS: dict[str, str] = {
    "quick": "xianfeng",
    "fast": "xianfeng",
    "simple": "xianfeng",
    "minimal": "xianfeng",
    "prototype": "xianfeng",
    "draft": "xianfeng",
    "standard": "wei_wuzu",
    "normal": "wei_wuzu",
    "balanced": "wei_wuzu",
    "emanation": "wei_wuzu",
    "tikkun": "wei_wuzu",
    "production": "huben",
    "robust": "huben",
    "full": "huben",
    "complete": "huben",
    "enterprise": "huben",
    "ascent": "huben",
    "keter": "huben",
    "malkuth": "xianfeng",
    "descent": "xianfeng",
}

# Variable extraction patterns
_VAR_PATTERNS: list[tuple[str, str]] = [
    (r"for\s+(\w+)", "name"),
    (r"named\s+(\w+)", "name"),
    (r"called\s+(\w+)", "name"),
    (r"path\s+(['\"]?)([\w/]+)\1", "path"),
    (r"route\s+(['\"]?)([\w/]+)\1", "path"),
]


class VibeParser:
    """Lightweight natural-language intent parser for the God-Kit."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._custom_map: dict[str, str] = {}

    def parse(self, text: str) -> dict[str, Any]:
        """Parse a vibe prompt into a structured template query."""
        text_lower = text.lower()

        # 1. Detect template name
        template_name = self._detect_template(text_lower)

        # 2. Detect tier hint
        tier = self._detect_tier(text_lower)

        # 3. Extract variables
        variables = self._extract_variables(text)

        # 4. If no explicit template, return a fuzzy search suggestion
        if template_name is None:
            return {
                "status": "ambiguous",
                "tier": tier,
                "keywords": self._extract_keywords(text_lower),
                "message": "No exact template match. Try specifying: fastapi, pytest, or pydantic.",
            }

        return {
            "status": "matched",
            "template_name": template_name,
            "tier": tier,
            "variables": variables,
        }

    def _detect_template(self, text: str) -> str | None:
        """Find the best-matching template from vibe keywords."""
        # Check custom overrides first
        with self._lock:
            for keyword, template in self._custom_map.items():
                if keyword in text:
                    return template

        # Check built-in map (longer phrases first to avoid partial matches)
        for keyword in sorted(_VIBE_MAP, key=len, reverse=True):
            if keyword in text:
                return _VIBE_MAP[keyword]
        return None

    def _detect_tier(self, text: str) -> str:
        """Infer tier from adjectives in the prompt."""
        for keyword, tier in sorted(_TIER_HINTS.items(), key=lambda x: len(x[0]), reverse=True):
            if keyword in text:
                return tier
        return "xianfeng"  # Default: fast, cheap reconnaissance

    def _extract_variables(self, text: str) -> dict[str, str]:
        """Pull likely variable values from the prompt text."""
        variables: dict[str, str] = {}
        for pattern, var_name in _VAR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                # Some patterns have a quote group + value group
                groups = match.groups()
                value = groups[-1]  # last group is the actual value
                if value:
                    variables[var_name] = value
        return variables

    def _extract_keywords(self, text: str) -> list[str]:
        """Return significant keywords for fuzzy matching."""
        stopwords = {"the", "a", "an", "i", "need", "want", "make", "create", "get", "for", "to", "and", "or"}
        words = re.findall(r"[a-z]+", text)
        return [w for w in words if w not in stopwords and len(w) > 2]

    def register_alias(self, alias: str, template_name: str) -> None:
        """Register a custom vibe alias at runtime."""
        with self._lock:
            self._custom_map[alias.lower()] = template_name

    def status(self) -> dict[str, Any]:
        """Get parser status."""
        with self._lock:
            custom_count = len(self._custom_map)
        return {
            "builtin_keywords": len(_VIBE_MAP),
            "tier_hints": len(_TIER_HINTS),
            "custom_aliases": custom_count,
        }


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_parser: VibeParser | None = None
_parser_lock = threading.Lock()


def get_vibe_parser() -> VibeParser:
    """Get the global VibeParser instance."""
    global _parser
    if _parser is None:
        with _parser_lock:
            if _parser is None:
                _parser = VibeParser()
    return _parser
