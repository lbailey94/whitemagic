"""Grimoire Engine - Unified 12-Phase Spellbook

Integrated with the PRAT dispatch interfaces and the autonomous Unified Progression Daemon.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from whitemagic.core.governance.unified_progression import (
    WuXingPhase,
    YinYangPhase,
    get_progression_daemon,
)

logger = logging.getLogger(__name__)


class GrimoireState(Enum):
    """Current state of the grimoire"""
    DORMANT = "dormant"      # Not active
    LISTENING = "listening"  # Monitoring context
    CASTING = "casting"      # Actively casting spell
    LEARNING = "learning"    # Processing outcomes


@dataclass
class GrimoireContext:
    """Current context for spell selection"""
    task: str = ""
    emotional_state: str = "neutral"
    zodiac_sign: str = "aries"
    hexagram: int = 1
    keywords: list[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def wu_xing(self) -> WuXingPhase:
        """Dynamically pull from progression daemon"""
        daemon = get_progression_daemon()
        return daemon.state.wu_xing

    @property
    def yin_yang(self) -> YinYangPhase:
        """Dynamically pull from progression daemon"""
        daemon = get_progression_daemon()
        return daemon.state.yin_yang

    def to_dict(self) -> dict[str, Any]:
        """
        Convert to/from dict.
        
        Returns:
            dict[str, Any]
        """
        return {
            "task": self.task,
            "emotional_state": self.emotional_state,
            "wu_xing": self.wu_xing.value,
            "yin_yang": self.yin_yang.value,
            "zodiac_sign": self.zodiac_sign,
            "hexagram": self.hexagram,
            "keywords": self.keywords,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SpellRecommendation:
    """A recommended spell with confidence"""
    spell_name: str
    chapter: int
    confidence: float
    reason: str
    auto_cast: bool = False

    def __str__(self) -> str:
        cast = "⚡ AUTO-CAST" if self.auto_cast else "📖 Suggested"
        return f"{cast}: {self.spell_name} (Ch.{self.chapter}) - {self.confidence:.0%} - {self.reason}"


class Grimoire:
    """The Living Grimoire 2.0 - Engine"""

    CHAPTER_DOMAINS = {
        1: ["session", "start", "begin", "init", "bootstrap", "handoff"],
        2: ["memory", "create", "update", "store", "consolidate"],
        3: ["health", "foundation", "root", "integrity", "diagnosis"],
        4: ["lock", "resource", "sanctuary", "sandbox", "privacy"],
        5: ["context", "connection", "scratchpad", "pulse"],
        6: ["performance", "acceleration", "rust", "zig", "speed"],
        7: ["search", "recall", "wisdom", "filter", "vector"],
        8: ["introspect", "gnosis", "metrics", "telemetry", "self-model"],
        9: ["dream", "play", "resilience", "flexibility", "grimoire"],
        10: ["governance", "dharma", "rules", "karma", "ethics"],
        11: ["pattern", "connection", "association", "cluster", "learning"],
        12: ["export", "deploy", "expand", "adventure", "audit"],
        13: ["archaeology", "code", "navigation", "history", "transformation"],
        14: ["dream", "regeneration", "serendipity", "entity", "joy"],
        15: ["ethics", "balance", "harmony", "consent", "boundaries"],
        16: ["metrics", "hologram", "yin-yang", "gratitude", "accumulation"],
        17: ["pipeline", "task", "energy", "healing", "digestion"],
        18: ["detail", "debug", "anomaly", "salience", "presence"],
        19: ["prompt", "capture", "filter", "mystery", "pattern"],
        20: ["precision", "validation", "inference", "voice", "edge"],
        21: ["judgment", "council", "ensemble", "reasoning", "kaizen"],
        22: ["strategy", "governance", "maturity", "homeostasis"],
        23: ["swarm", "endurance", "worker", "persistence"],
        24: ["agent", "nurture", "register", "trust", "wonder"],
        25: ["galaxy", "stillness", "void", "meditation", "garden"],
        26: ["ollama", "shelter", "protection", "local", "ai"],
        27: ["sangha", "community", "chat", "broker", "encampment"],
        28: ["vote", "boundary", "wall", "air", "invisible"],
    }

    KEYWORD_BOOSTS = {
        "urgent": ["action", "speed", "efficiency"],
        "confused": ["clarity", "analysis", "wisdom"],
        "stuck": ["flow", "creativity", "emergence"],
        "tired": ["rest", "dream", "yin"],
        "excited": ["creation", "manifestation", "yang"],
        "grateful": ["connection", "love", "dharma"],
        "curious": ["wonder", "mystery", "exploration"],
        "anxious": ["presence", "grounding", "breath"],
    }

    def __init__(self) -> None:
        self.state = GrimoireState.DORMANT
        self.context = GrimoireContext()
        self.cast_history: list[dict[str, Any]] = []

    def awaken(self) -> Grimoire:
        """
        Perform the awaken operation.
        
        Returns:
            Grimoire
        """
        self.state = GrimoireState.LISTENING
        return self

    def update_context(self, **kwargs: Any) -> Grimoire:
        """
        Update the context.
        
        Returns:
            Grimoire
        """
        for key, value in kwargs.items():
            if hasattr(self.context, key):
                setattr(self.context, key, value)
        self.context.timestamp = datetime.now()
        return self

    def recommend_spells(self, max_results: int = 3) -> list[SpellRecommendation]:
        """
        Perform the recommend spells operation.
        
        Args:
            max_results: Parameter description.
        
        Returns:
            list[SpellRecommendation]
        """
        recommendations = []

        # Pull dynamic phase
        current_wu_xing = self.context.wu_xing

        for chapter_num, domains in self.CHAPTER_DOMAINS.items():
            score = 0.0
            reason_parts = []

            task_lower = self.context.task.lower()
            for domain in domains:
                if domain in task_lower:
                    score += 0.3
                    reason_parts.append(f"task matches '{domain}'")

            for keyword in self.context.keywords:
                if keyword.lower() in domains:
                    score += 0.2
                    reason_parts.append(f"keyword '{keyword}'")

            emotion = self.context.emotional_state.lower()
            if emotion in self.KEYWORD_BOOSTS:
                for boost_domain in self.KEYWORD_BOOSTS[emotion]:
                    if boost_domain in domains:
                        score += 0.25
                        reason_parts.append(f"emotional state '{emotion}'")

            wu_xing_mappings = {
                WuXingPhase.WOOD: [0, 1, 15],
                WuXingPhase.FIRE: [3, 9, 18],
                WuXingPhase.EARTH: [10, 11, 5],
                WuXingPhase.METAL: [6, 8, 17],
                WuXingPhase.WATER: [7, 12, 14],
            }
            if chapter_num in wu_xing_mappings.get(current_wu_xing, []):
                score += 0.15
                reason_parts.append(f"Wu Xing {current_wu_xing.value}")

            if score > 0:
                recommendations.append(SpellRecommendation(
                    spell_name=f"Chapter {chapter_num} Spells",
                    chapter=chapter_num,
                    confidence=min(score, 1.0),
                    reason=", ".join(reason_parts) if reason_parts else "general match",
                    auto_cast=score >= 0.7,
                ))

        recommendations.sort(key=lambda r: r.confidence, reverse=True)
        return recommendations[:max_results]


_grimoire_engine_instance: Grimoire | None = None

def get_grimoire_engine() -> Grimoire:
    """
    Get the grimoire engine.
    
    Returns:
        Grimoire
    """
    global _grimoire_engine_instance
    if _grimoire_engine_instance is None:
        _grimoire_engine_instance = Grimoire()
    return _grimoire_engine_instance
