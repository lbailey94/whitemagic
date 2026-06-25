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
        from whitemagic.core.resonance import ResonanceEvent, get_bus
        bus = get_bus()
        bus.emit(ResonanceEvent(source="codegenome.vault", event_type=event_type, data=data))  # type: ignore[arg-type]
    except (ImportError, AttributeError):
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

    def generate_with_llm(
        self,
        prompt: str,
        repo_path: str | None = None,
        write_output: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Generate code with LLM refinement: template → git patterns → LLM → optional write.

        Args:
            prompt: Vibe prompt describing what to generate
            repo_path: Optional repo path for git history mining (Geneseed patterns)
            write_output: Optional target file path; if set, writes via CodeWritingClone

        Returns:
            Dict with status, code, template info, patterns, and write result
        """
        # Step 1: Render template
        render_result = self.vibe_render(prompt, **kwargs)
        if render_result.get("status") != "success":
            return render_result

        base_code = render_result["code"]
        template_name = render_result["template_name"]
        tier = render_result["tier"]

        # Step 2: Mine git patterns for context (if repo provided)
        patterns_context = ""
        patterns_count = 0
        if repo_path:
            try:
                from whitemagic.optimization.rust_mining import mine_geneseed_patterns
                patterns = mine_geneseed_patterns(repo_path, 0.3, 50)
                if patterns:
                    pattern_lines = []
                    for p in patterns[:5]:
                        ptype = getattr(p, "pattern_type", str(p))
                        conf = getattr(p, "confidence", 0.0)
                        files = getattr(p, "files_changed", [])
                        pattern_lines.append(f"  - {ptype} (confidence={conf:.2f}, files={files})")
                    patterns_context = "\n\nRelevant optimization patterns from git history:\n" + "\n".join(pattern_lines)
                    patterns_count = len(patterns)
            except Exception as e:
                logger.debug("Geneseed pattern mining skipped: %s", e)

        # Step 3: LLM refinement
        llm_refined = False
        final_code = base_code
        try:
            from whitemagic.inference.local_llm import LocalLLM
            llm = LocalLLM()
            if llm.is_available:
                llm_prompt = (
                    f"You are refining code generated from a template.\n"
                    f"Template: {template_name}\n"
                    f"Prompt: {prompt}\n\n"
                    f"Generated code:\n{base_code}\n"
                    f"{patterns_context}\n\n"
                    f"Improve this code: fix issues, add missing error handling, "
                    f"optimize performance. Return ONLY the improved code."
                )
                response = llm.complete(llm_prompt)
                if response and response.strip():
                    final_code = response.strip()
                    llm_refined = True
        except Exception as e:
            logger.debug("LLM refinement skipped: %s", e)

        # Step 4: Write via CodeWritingClone (if requested)
        write_result = None
        if write_output:
            try:
                from whitemagic.optimization.rust_code_writing import write_file
                import os
                base_path = os.path.dirname(write_output) or "."
                rel_path = os.path.basename(write_output)
                write_result = write_file(base_path, rel_path, final_code)
            except Exception as e:
                write_result = {"success": False, "error": str(e)}
                logger.warning("CodeWritingClone write failed: %s", e)

        _emit_gan_ying("geneseed.llm_generate", {
            "template": template_name,
            "tier": tier,
            "llm_refined": llm_refined,
            "patterns_mined": patterns_count,
            "written": write_result is not None,
        })

        return {
            "status": "success",
            "template_name": template_name,
            "tier": tier,
            "code": final_code,
            "base_code": base_code,
            "llm_refined": llm_refined,
            "patterns_mined": patterns_count,
            "write_result": write_result,
            "variables": render_result.get("variables", {}),
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
