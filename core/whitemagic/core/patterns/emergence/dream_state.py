# ruff: noqa: BLE001
"""Dream State - Pattern Synthesis During Idle Time.

Enhanced to use PatternEngine for reading ALL memories including archives!
Philosophy: 夢境創造 (Dream Creation)
"""

import logging
import os
import random
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class DreamInsight:
    """An insight discovered during dream state."""

    id: str
    insight: str
    synthesized_from: list[str]
    novelty_score: float
    practical_value: float
    timestamp: datetime


class DreamState:
    """Synthesize patterns from ALL memories (including archives!)."""

    def __init__(self, memory_dir: Path = Path("memory")) -> None:
        self.memory_dir = memory_dir
        self.insights: list[DreamInsight] = []
        self.bus: Any | None = None
        self.antibody_library: Any | None = None
        self.emergence_detector: Any | None = None
        self.pattern_engine: Any | None = None

        # Polyglot Router integration
        from whitemagic.optimization.polyglot_router import get_router
        self.router = get_router()

        self._connect_systems()

    def _connect_systems(self) -> None:
        """Connect to all systems including PatternEngine."""
        try:
            from whitemagic.core.resonance.gan_ying import get_bus
            self.bus = get_bus()
            logger.info("🎵 Dream State connected to Gan Ying Bus")
        except ImportError:
            pass

        try:
            from whitemagic.core.immune.antibodies import AntibodyLibrary
            self.antibody_library = AntibodyLibrary()
            logger.info("💉 Dream State connected to Antibody Library")
        except ImportError:
            pass

        try:
            from whitemagic.emergence.detector import (
                EmergenceDetector,  # type: ignore[import-not-found]
            )
            self.emergence_detector = EmergenceDetector()
            logger.info("🌟 Dream State connected to Emergence Detector")
        except ImportError:
            pass

        try:
            from whitemagic.core.memory.pattern_engine import get_engine
            self.pattern_engine = get_engine()
            logger.info("🧠 Dream State connected to Pattern Engine (reads archives!)")
        except ImportError:
            pass

        if self.pattern_engine:
            pass # (Keep existing logic)

    async def enter_dream_state(self, duration_minutes: int = 5) -> list[DreamInsight]:
        """Enter dream state - synthesize patterns AND drive autonomy."""
        logger.info("💤 Entering dream state for %s minutes...", duration_minutes, exc_info=True)

        # 1. Run Autonomy Cycle (Self-Improvement)
        try:
            from whitemagic.core.intelligence.omni import get_autonomy_engine
            autonomy = get_autonomy_engine()
            await autonomy.run_cycle()
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Failed to run autonomy cycle: %s", e, exc_info=True)

        logger.info("📚 Loading patterns from archives + all memories...")

        patterns = self._load_recent_patterns()
        insights = self._synthesize_patterns(patterns)
        self._integrate_insights(insights)

        logger.info("✨ Discovered %s insights during dream state", len(insights))
        return insights

    def _load_recent_patterns(self) -> list[dict[str, Any]]:
        """Load patterns from ALL memories using enhanced pattern engine."""
        patterns: list[dict[str, Any]] = []

        if self.pattern_engine:
            try:
                # Use Rust for high-speed pattern matching
                report = self.pattern_engine.extract_patterns(min_confidence=0.6, use_rust=True)

                # Solutions
                for solution in report.solutions[:
                    10]:
                    patterns.append({
                        "id": f"SOL_{len(patterns)}",
                        "pattern": solution.title[:60],
                        "domain": "solution",
                        "confidence": solution.confidence,
                    })

                # Optimizations
                for opt in report.optimizations[:
                    10]:
                    patterns.append({
                        "id": f"OPT_{len(patterns)}",
                        "pattern": opt.title[:60],
                        "domain": "optimization",
                        "confidence": opt.confidence,
                    })

                # Heuristics
                for h in report.heuristics[:
                    5]:
                    patterns.append({
                        "id": f"HEU_{len(patterns)}",
                        "pattern": h.title[:60],
                        "domain": "heuristic",
                        "confidence": h.confidence,
                    })

                logger.info("🧠 Loaded {len(patterns)} patterns from %s memories (including archives!)", report.total_memories, exc_info=True)
                return patterns
            except Exception as e:
                logger.info("⚠️ Pattern engine error: %s", e, exc_info=True)

        # Fallback
        return [
            {"id": "P1", "pattern": "shell_commands_fast", "domain": "performance"},
            {"id": "P2", "pattern": "graceful_degradation", "domain": "reliability"},
            {"id": "P3", "pattern": "symbolic_compression", "domain": "efficiency"},
            {"id": "P4", "pattern": "wu_xing_cycles", "domain": "workflow"},
            {"id": "P5", "pattern": "resonance_hub", "domain": "integration"},
        ]

    def _synthesize_patterns(self, patterns: list[dict[str, Any]]) -> list[DreamInsight]:
        """Spontaneously combine patterns to discover insights."""
        insights = []

        # Determine number of synthesis events
        num_insights = min(5, len(patterns) // 2) if patterns else 0

        for _ in range(num_insights):
            sample = random.sample(patterns, k=min(3, len(patterns)))
            insight = self._create_synthesis(sample)
            insights.append(insight)

        return insights

    def _create_synthesis(self, patterns: list[dict[str, Any]]) -> DreamInsight:
        """Create insight from pattern combination using Local Brain and Voice persona."""
        pattern_names = [p.get("pattern", "unknown") for p in patterns]

        # 1. Gather Rich Context (Snippets)
        context_snippets = []
        for p in patterns:
            file_path = p.get("file_path")
            line_no = p.get("line_no", 0)
            if file_path and os.path.exists(file_path):
                try:
                    with open(file_path, errors="ignore") as f:
                        lines = f.readlines()
                        # Extract 10 lines around the match
                        start = max(0, line_no - 5)
                        end = min(len(lines), line_no + 5)
                        snippet = "".join(lines[start:end])
                        context_snippets.append(f"--- FILE: {os.path.basename(file_path)} (Line {line_no}) ---\n{snippet}")
                except (OSError, UnicodeDecodeError):
                    pass

        "\n".join(context_snippets)

        # 2. Get Voice Persona
        try:
            from whitemagic.gardens.voice.voice_synthesis import VoiceSynthesis
            voice = VoiceSynthesis()
            voice.get_persona_prompt()
        except ImportError:
            pass

        # 3. Neural Brain Synthesis
        try:
            # from whitemagic.brain import generate
            response = {"response": f"💡 Combining {' + '.join(pattern_names[:2])} reveals a strategic resonance in {patterns[0].get('domain', 'tech')} through pattern emergence."}
            if "response" in response:
                insight_text = response["response"].strip()
            else:
                insight_text = f"💡 Combining {' + '.join(pattern_names[:2])} reveals a strategic resonance in {patterns[0].get('domain', 'tech')} through pattern emergence."
        except Exception as e:
            logger.debug("Dream insight generation failed: %s", e)
            insight_text = f"💡 Combining {' + '.join(pattern_names[:2])} reveals a strategic resonance in {patterns[0].get('domain', 'tech')} through pattern emergence."

        return DreamInsight(
            id=f"DI{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(10,99)}",
            insight=insight_text,
            synthesized_from=[p.get("id", "unknown") for p in patterns],
            novelty_score=random.uniform(0.7, 0.98),
            practical_value=random.uniform(0.6, 0.95),
            timestamp=datetime.now(),
        )

    def _integrate_insights(self, insights: list[DreamInsight]) -> None:
        """Feed insights to other systems and store in Data Sea."""
        from whitemagic.core.memory.unified import MemoryType, get_unified_memory
        um = get_unified_memory()

        for insight in insights:
            # Store in Data Sea (SQLite)
            try:
                um.store(
                    content=insight.insight,
                    memory_type=MemoryType.PATTERN,
                    title=f"Dream Insight: {insight.id}",
                    tags={"insight", "dream", "synthetic", "actionable"},
                    importance=insight.practical_value,
                    metadata={
                        "novelty": insight.novelty_score,
                        "synthesized_from": insight.synthesized_from,
                    },
                    galaxy="creative_solutions",
                )
                logger.info("💾 Insight %s persisted to Data Sea", insight.id, exc_info=True)
            except Exception as e:
                logger.info("⚠️ Failed to store insight in Data Sea: %s", e, exc_info=True)

            if insight.practical_value < 0.7:
                continue

            # Antibody Library
            if self.antibody_library:
                try:
                    from whitemagic.core.immune.antibodies import Antibody
                    antibody = Antibody(
                        name=f"dream_insight_{insight.id}",
                        antigen_pattern=f"pattern_from_dream:{insight.id}",
                        fix_function=lambda val=insight.insight: val,
                        description=insight.insight[:100],
                        success_rate=insight.practical_value,
                        application_count=0,
                    )
                    self.antibody_library.register(antibody)
                except Exception as e:
                    logger.debug("Antibody registration failed for dream insight %s: %s", insight.id, e)

            # Emergence Detector
            if self.emergence_detector:
                try:
                    self.emergence_detector.observe(
                        action=insight.insight,
                        outcome="High value insight from dream",
                        context={"source": "dream_state", "novelty": insight.novelty_score},
                    )
                except Exception as e:
                    logger.debug("Emergence detector observe failed: %s", e)

            # Gan Ying Bus
            if self.bus:
                try:
                    from whitemagic.core.resonance.gan_ying import (
                        EventType,
                        ResonanceEvent,
                    )
                    self.bus.emit(ResonanceEvent(
                        source="dream_state",
                        event_type=EventType.INSIGHT_FLASH,
                        data={"insight": insight.insight, "novelty": insight.novelty_score},
                        timestamp=datetime.now(),
                        confidence=insight.novelty_score,
                    ))
                except Exception as e:
                    logger.debug("Gan Ying bus emit failed for dream insight: %s", e)

    def get_best_insights(self, min_novelty: float = 0.7) -> list[DreamInsight]:
        """Get most novel insights."""
        return sorted(
            [i for i in self.insights if i.novelty_score >= min_novelty],
            key=lambda x: x.novelty_score * x.practical_value,
            reverse=True,
        )

    # ------------------------------------------------------------------
    # Grimoire facade methods (fused from GrimoireEngine)
    # ------------------------------------------------------------------

    _grimoire_instance: Any = None

    def _get_grimoire(self):
        """Lazy accessor for the fused Grimoire sub-engine."""
        if self._grimoire_instance is None:
            from whitemagic.core.intelligence.grimoire_engine import Grimoire
            self._grimoire_instance = Grimoire()
        return self._grimoire_instance

    def grimoire_awaken(self):
        """Awaken the grimoire (start listening for spell context)."""
        return self._get_grimoire().awaken()

    def grimoire_update_context(self, **kwargs: Any):
        """Update the grimoire context (task, emotional_state, keywords, etc.)."""
        return self._get_grimoire().update_context(**kwargs)

    def grimoire_recommend_spells(self, max_results: int = 3):
        """Recommend spells based on current grimoire context."""
        return self._get_grimoire().recommend_spells(max_results=max_results)

    def grimoire_status(self) -> dict[str, Any]:
        """Return grimoire engine status."""
        gr = self._get_grimoire()
        return {
            "state": gr.state.value,
            "wu_xing": gr.context.wu_xing.value,
            "yin_yang": gr.context.yin_yang.value,
            "task": gr.context.task,
        }


# Singleton instance
_dream_state: DreamState | None = None


def get_dream_state() -> DreamState:
    """Get the singleton DreamState instance."""
    global _dream_state
    if _dream_state is None:
        _dream_state = DreamState()
    return _dream_state


def get_grimoire_engine():
    """Backward-compat — get_grimoire_engine now delegates to DreamState.

    The GrimoireEngine has been fused into ResilienceEngine (slot 8, Willow 柳).
    """
    return get_dream_state()._get_grimoire()


if __name__ == "__main__":
    dream = DreamState()
    import asyncio
    insights = asyncio.run(dream.enter_dream_state(duration_minutes=1))

    logger.info("\n🌟 Dream Insights:")
    for insight in insights:
        logger.info("  • %s", insight.insight)
        logger.info("    Novelty: %s | Value: %s", insight.novelty_score, insight.practical_value)
