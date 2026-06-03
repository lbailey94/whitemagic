"""Geneseed Vault — Integration layer for the Vibe Coding God-Kit.

Thin wrapper around CodeGenomeEngine that:
- Loads templates from $WM_STATE_ROOT/codegenome/
- Tracks usage statistics
- Emits Gan Ying events on template fork/merge
- Provides a unified API for template discovery, rendering, and lineage.

Usage:
    vault = get_geneseed_vault()
    result = vault.vibe_render("I need a FastAPI endpoint for items")
    # -> {"code": "@router.get('/items')\ndef get_items(): ...", "tier": "xianfeng", ...}
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

logger = logging.getLogger(__name__)


def _emit_gan_ying(event_type: str, data: dict[str, Any]) -> None:
    """Emit a Gan Ying event if the bus is available."""
    try:
        from whitemagic.core.resonance.gan_ying import get_bus
        bus = get_bus()
        bus.emit(event_type, data)
    except Exception:
        pass  # Graceful degradation if Gan Ying is unavailable


class GeneseedVault:
    """Unified vault for code template management with audit trail."""

    def __init__(self) -> None:
        from .engine import get_codegenome_engine
        from .vibe_parser import get_vibe_parser

        self._engine = get_codegenome_engine()
        self._parser = get_vibe_parser()
        self._lock = threading.Lock()
        self._usage_stats: dict[str, dict[str, Any]] = {}

    def vibe_render(self, prompt: str, **kwargs: Any) -> dict[str, Any]:
        """End-to-end: parse vibe prompt -> find template -> render code."""
        query = self._parser.parse(prompt)

        if query.get("status") != "matched":
            return {
                "status": "error",
                "error_code": "no_template_match",
                "details": query,
            }

        template_name = query["template_name"]
        tier = query.get("tier", "xianfeng")
        variables = {**query.get("variables", {}), **kwargs}

        # Render
        code = self._engine.render(template_name, tier=tier, **variables)

        # Track usage
        self._record_usage(template_name, tier, variables)

        # Emit audit event
        _emit_gan_ying("geneseed.render", {
            "template": template_name,
            "tier": tier,
            "variables": list(variables.keys()),
        })

        template = self._engine.get_template(template_name)
        return {
            "status": "success",
            "template_name": template_name,
            "tier": tier,
            "code": code,
            "dependencies": template.dependencies if template else [],
            "signature": template.signature if template else "",
            "variables": variables,
        }

    def fork(self, parent_name: str, new_name: str, body_delta: str = "") -> dict[str, Any]:
        """Fork a template and emit an audit event."""
        child = self._engine.fork_template(parent_name, new_name, body_delta)
        if child is None:
            return {
                "status": "error",
                "error_code": "template_not_found",
                "details": {"parent": parent_name},
            }

        _emit_gan_ying("geneseed.fork", {
            "parent": parent_name,
            "child": new_name,
            "version": child.version,
        })

        return {
            "status": "success",
            "template": child.to_dict(),
        }

    def list_templates(self, tag: str | None = None) -> list[dict[str, Any]]:
        """List all templates, optionally filtered by tag."""
        return self._engine.list_templates(tag=tag)

    def get_template(self, name: str) -> dict[str, Any] | None:
        """Get a single template by name."""
        t = self._engine.get_template(name)
        return t.to_dict() if t else None

    def status(self) -> dict[str, Any]:
        """Get vault status including engine and parser state."""
        return {
            "engine": self._engine.status(),
            "parser": self._parser.status(),
            "usage_stats": dict(self._usage_stats),
        }

    def _record_usage(self, template_name: str, tier: str, variables: dict[str, Any]) -> None:
        """Track template usage for internal analytics."""
        with self._lock:
            if template_name not in self._usage_stats:
                self._usage_stats[template_name] = {
                    "render_count": 0,
                    "tiers": {},
                    "last_render": "",
                }
            stats = self._usage_stats[template_name]
            stats["render_count"] += 1
            stats["last_render"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            stats["tiers"][tier] = stats["tiers"].get(tier, 0) + 1


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_vault: GeneseedVault | None = None
_vault_lock = threading.Lock()


def get_geneseed_vault() -> GeneseedVault:
    """Get the global GeneseedVault instance."""
    global _vault
    if _vault is None:
        with _vault_lock:
            if _vault is None:
                _vault = GeneseedVault()
    return _vault
