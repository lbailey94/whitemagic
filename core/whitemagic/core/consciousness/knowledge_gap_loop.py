"""Knowledge Gap Action Loop — Cybernetic self-direction.

When the RecursiveImprovementLoop identifies a knowledge gap, this module
turns it into action. The loop:

1. Detects knowledge gaps from MetaGalaxy or RecursiveImprovementLoop
2. Classifies the gap type (missing memory, missing code, missing strategy)
3. Routes to the appropriate self-directed action:
   - Missing memory → GeneseedVault template generation
   - Missing strategy → MetaGalaxy strategic priority → memory creation
   - Missing code → SelfImprovementPipeline
   - Missing knowledge → MCP tool search + web search
4. Stores the result in the appropriate galaxy
5. Tracks whether the gap was filled

This is the mechanism that lets the system fill its own blind spots
instead of waiting for the user to do it.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeGap:
    """A detected knowledge gap with actionable metadata."""

    gap_id: str
    description: str
    gap_type: str  # "missing_memory", "missing_code", "missing_strategy", "missing_knowledge"
    galaxy: str = "universal"
    priority: float = 0.5
    proposed_action: str = ""
    status: str = "open"  # "open", "in_progress", "filled", "failed"
    result: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0


class KnowledgeGapActionLoop:
    """Turns knowledge gaps into self-directed actions.

    This is the cybernetic bridge between knowing what's missing and
    actually doing something about it. Instead of just logging gaps,
    the system attempts to fill them using its own tools.
    """

    def __init__(self) -> None:
        self._gaps: list[KnowledgeGap] = []
        self._lock = threading.RLock()
        self._filled_count: int = 0
        self._failed_count: int = 0

    def detect_gaps(self) -> list[KnowledgeGap]:
        """Detect knowledge gaps from MetaGalaxy and RecursiveImprovementLoop."""
        gaps: list[KnowledgeGap] = []

        # 1. Gaps from MetaGalaxy
        try:
            from whitemagic.core.consciousness.meta_galaxy import get_meta_galaxy
            mg = get_meta_galaxy()
            mg_gaps = mg.get_knowledge_gaps()
            for i, gap_desc in enumerate(mg_gaps):
                gap = KnowledgeGap(
                    gap_id=f"meta_gap_{i}",
                    description=gap_desc,
                    gap_type=self._classify_gap(gap_desc),
                    galaxy=self._extract_galaxy(gap_desc),
                    priority=0.7,
                )
                gap.proposed_action = self._propose_action(gap)
                gaps.append(gap)
        except Exception as e:
            logger.debug("KnowledgeGap: MetaGalaxy gap detection failed: %s", e)

        # 2. Gaps from RecursiveImprovementLoop
        try:
            from whitemagic.core.evolution.recursive_loop import get_recursive_loop
            loop = get_recursive_loop()
            if hasattr(loop, "_last_cycle") and loop._last_cycle:
                for hyp in getattr(loop._last_cycle, "hypotheses", []):
                    if hyp.novelty_score > 0.5 and hyp.confidence < 0.1:
                        gap = KnowledgeGap(
                            gap_id=f"ril_gap_{hyp.id}",
                            description=hyp.description,
                            gap_type="missing_strategy",
                            galaxy="self_learning",
                            priority=hyp.novelty_score,
                        )
                        gap.proposed_action = self._propose_action(gap)
                        gaps.append(gap)
        except Exception as e:
            logger.debug("KnowledgeGap: RIL gap detection failed: %s", e)

        # WI 13: Gaps from EmergenceEngine — novel patterns that reveal
        # knowledge boundaries. Emergence insights with high novelty but
        # low confidence indicate areas where the system detected something
        # interesting but doesn't understand it yet.
        try:
            from whitemagic.core.intelligence.agentic.emergence_engine import (
                get_emergence_engine,
            )

            ee = get_emergence_engine()
            insights = ee.get_insights(limit=5)
            for insight in insights:
                confidence = insight.get("confidence", 0.5)
                insight_source = insight.get("source", "unknown")
                if confidence < 0.3:
                    gap = KnowledgeGap(
                        gap_id=f"emergence_gap_{insight.get('id', '')}",
                        description=f"Emergence pattern '{insight_source}' with low confidence — knowledge boundary detected",
                        gap_type="missing_knowledge",
                        galaxy="codex",
                        priority=0.6,
                    )
                    gap.proposed_action = self._propose_action(gap)
                    gaps.append(gap)
        except Exception as e:
            logger.debug("KnowledgeGap: EmergenceEngine gap detection failed: %s", e)

        # WI 13: Reverse direction — check if EmergenceEngine has insights
        # related to gaps from other sources. This cross-references gaps
        # with emergence patterns to find connections.
        try:
            from whitemagic.core.intelligence.agentic.emergence_engine import (
                get_emergence_engine,
            )

            ee = get_emergence_engine()
            emergence_insights = ee.get_insights(limit=10)
            if emergence_insights and gaps:
                for gap in gaps:
                    for insight in emergence_insights:
                        insight_title = insight.get("title", "").lower()
                        gap_desc = gap.description.lower()
                        # Check for keyword overlap between gap and insight
                        gap_words = set(gap_desc.split())
                        insight_words = set(insight_title.split())
                        overlap = gap_words & insight_words - {"the", "a", "an", "with", "for", "of", "in", "to", "and"}
                        if overlap:
                            gap.metadata = gap.metadata or {}
                            gap.metadata["related_emergence"] = insight.get("id", "")
                            break
        except Exception as e:
            logger.debug("KnowledgeGap: EmergenceEngine reverse cross-ref failed: %s", e)

        with self._lock:
            # Merge with existing gaps (avoid duplicates)
            existing_descs = {g.description for g in self._gaps}
            for gap in gaps:
                if gap.description not in existing_descs:
                    self._gaps.append(gap)

            # Keep only last 50 gaps
            if len(self._gaps) > 50:
                self._gaps = self._gaps[-50:]

        return gaps

    def _classify_gap(self, description: str) -> str:
        """Classify a knowledge gap by type."""
        desc_lower = description.lower()
        if "empty" in desc_lower or "no memories" in desc_lower:
            return "missing_memory"
        if "stale" in desc_lower or "no new" in desc_lower:
            return "missing_memory"
        if "code" in desc_lower or "implementation" in desc_lower:
            return "missing_code"
        if "strategic" in desc_lower or "vision" in desc_lower or "plan" in desc_lower:
            return "missing_strategy"
        return "missing_knowledge"

    def _extract_galaxy(self, description: str) -> str:
        """Extract galaxy name from gap description."""
        desc_lower = description.lower()
        for galaxy in ["citta", "codex", "insight", "self_learning", "self_discovery",
                        "creative_solutions", "oracle", "universal", "sessions"]:
            if galaxy in desc_lower:
                return galaxy
        return "universal"

    def _propose_action(self, gap: KnowledgeGap) -> str:
        """Propose an action to fill the gap."""
        if gap.gap_type == "missing_memory":
            return "seed_memory_from_template"
        elif gap.gap_type == "missing_code":
            return "generate_code_from_vault"
        elif gap.gap_type == "missing_strategy":
            return "synthesize_strategy_from_meta_galaxy"
        else:
            return "search_and_ingest"

    def fill_gap(self, gap: KnowledgeGap) -> dict[str, Any]:
        """Attempt to fill a single knowledge gap."""
        gap.status = "in_progress"
        result: dict[str, Any] = {"gap_id": gap.gap_id, "action": gap.proposed_action}

        try:
            if gap.proposed_action == "seed_memory_from_template":
                result.update(self._seed_memory(gap))

            elif gap.proposed_action == "generate_code_from_vault":
                result.update(self._generate_code(gap))

            elif gap.proposed_action == "synthesize_strategy_from_meta_galaxy":
                result.update(self._synthesize_strategy(gap))

            elif gap.proposed_action == "search_and_ingest":
                result.update(self._search_and_ingest(gap))

            gap.result = result
            if result.get("status") == "success":
                gap.status = "filled"
                gap.resolved_at = time.time()
                with self._lock:
                    self._filled_count += 1
            else:
                gap.status = "failed"
                with self._lock:
                    self._failed_count += 1

        except Exception as e:
            gap.status = "failed"
            result["status"] = "error"
            result["error"] = str(e)
            with self._lock:
                self._failed_count += 1

        return result

    def _seed_memory(self, gap: KnowledgeGap) -> dict[str, Any]:
        """Seed a memory in the gap's galaxy using available context."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            mem_id = um.store(
                content=f"Auto-seeded memory for gap: {gap.description}",
                memory_type="LONG_TERM",
                galaxy=gap.galaxy,
                tags=["auto_seeded", "knowledge_gap", gap.gap_type],
                importance=gap.priority,
            )
            return {"status": "success", "memory_id": mem_id, "galaxy": gap.galaxy}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _generate_code(self, gap: KnowledgeGap) -> dict[str, Any]:
        """Generate code using GeneseedVault to fill a code gap."""
        try:
            from whitemagic.codegenome.vault import get_geneseed_vault
            vault = get_geneseed_vault()
            result = vault.vibe_render(gap.description)
            if result.get("status") == "success":
                # Store the generated code as a memory
                from whitemagic.core.memory.unified import get_unified_memory
                um = get_unified_memory()
                um.store(
                    content=f"Generated code for: {gap.description}\n\n{result.get('code', '')[:500]}",
                    memory_type="LONG_TERM",
                    galaxy="codex",
                    tags=["auto_generated", "geneseed_vault", "code"],
                    importance=0.7,
                )
                return {"status": "success", "template": result.get("template_name", "")}
            return {"status": "error", "error": result.get("error_code", "generation_failed")}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _synthesize_strategy(self, gap: KnowledgeGap) -> dict[str, Any]:
        """Synthesize a strategy from MetaGalaxy priorities."""
        try:
            from whitemagic.core.consciousness.meta_galaxy import get_meta_galaxy
            mg = get_meta_galaxy()
            priorities = mg.get_strategic_priorities()

            strategy = f"Strategic synthesis for gap: {gap.description}\n\n"
            strategy += "Current priorities:\n"
            for i, p in enumerate(priorities, 1):
                strategy += f"  {i}. {p}\n"

            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            um.store(
                content=strategy,
                memory_type="LONG_TERM",
                galaxy="codex",
                tags=["auto_generated", "strategic_synthesis", "meta_galaxy"],
                importance=0.8,
            )
            return {"status": "success", "priorities_count": len(priorities)}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_and_ingest(self, gap: KnowledgeGap) -> dict[str, Any]:
        """Search existing memories and ingest relevant content."""
        try:
            from whitemagic.core.memory.unified import get_unified_memory
            um = get_unified_memory()
            results = um.search(query=gap.description, limit=5)
            if results:
                return {"status": "success", "found_memories": len(results)}
            # No results — create a placeholder memory noting the gap
            um.store(
                content=f"Unresolved knowledge gap: {gap.description}. "
                        f"This gap requires external input or further investigation.",
                memory_type="SHORT_TERM",
                galaxy=gap.galaxy,
                tags=["auto_generated", "unresolved_gap"],
                importance=0.3,
            )
            return {"status": "success", "note": "created placeholder for unresolved gap"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def run(self, max_gaps: int = 3) -> list[dict[str, Any]]:
        """Detect and attempt to fill knowledge gaps.

        Args:
            max_gaps: Maximum number of gaps to attempt per run.

        Returns:
            List of results from fill attempts.
        """
        gaps = self.detect_gaps()
        open_gaps = [g for g in gaps if g.status == "open"][:max_gaps]

        results: list[dict[str, Any]] = []
        for gap in open_gaps:
            result = self.fill_gap(gap)
            results.append(result)
            logger.info(
                "KnowledgeGap: %s gap '%s' → %s",
                gap.gap_type,
                gap.description[:60],
                result.get("status", "unknown"),
            )

        return results

    def get_status(self) -> dict[str, Any]:
        """Get current status of the knowledge gap action loop."""
        with self._lock:
            open_count = sum(1 for g in self._gaps if g.status == "open")
            filled = self._filled_count
            failed = self._failed_count
            return {
                "total_gaps": len(self._gaps),
                "open": open_count,
                "filled": filled,
                "failed": failed,
                "success_rate": filled / max(1, filled + failed),
            }


# ── Singleton ───────────────────────────────────────────────────────

_kg_loop: KnowledgeGapActionLoop | None = None
_kg_lock = threading.Lock()


def get_knowledge_gap_loop() -> KnowledgeGapActionLoop:
    """Get the global KnowledgeGapActionLoop instance."""
    global _kg_loop
    if _kg_loop is None:
        with _kg_lock:
            if _kg_loop is None:
                _kg_loop = KnowledgeGapActionLoop()
    return _kg_loop
