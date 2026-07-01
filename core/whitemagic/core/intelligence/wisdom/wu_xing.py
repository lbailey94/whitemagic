"""Wu Xing Performance System - Five Elements Workflow Intelligence.

The Five Elements (Wu Xing) represent cyclical phases of work:
- Wood (木): Growth, expansion, learning, exploration (Spring)
- Fire (火): Transformation, execution, rapid action (Summer)
- Earth (土): Stability, integration, grounding (Late Summer)
- Metal (金): Refinement, boundaries, optimization (Autumn)
- Water (水): Reflection, flow, adaptation (Winter)

Philosophy: Like nature's seasons, work has natural phases.
Align tasks with the appropriate element for maximum effectiveness.

🌱→🔥→🌍→⚙️→💧 (Generating Cycle)
🌱⚙️🌍💧🔥 (Controlling Cycle)
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from whitemagic.wu_xing import Element

logger = logging.getLogger(__name__)


class WuXingSystem:
    """Five Elements system with Gan Ying resonance integration."""

    def __init__(self) -> None:
        self.optimizations: dict[Element, list[str]] = {e: [] for e in Element}
        self.current_element: Element | None = None
        self.bus: Any | None = None

        # Task type → Element mapping
        self.task_element_map = {
            # Wood (Growth, Learning)
            "research": Element.WOOD,
            "exploration": Element.WOOD,
            "learning": Element.WOOD,
            "discovery": Element.WOOD,
            "brainstorming": Element.WOOD,
            # Fire (Action, Speed)
            "implementation": Element.FIRE,
            "execution": Element.FIRE,
            "coding": Element.FIRE,
            "rapid_dev": Element.FIRE,
            "deployment": Element.FIRE,
            # Earth (Stability, Integration)
            "integration": Element.EARTH,
            "consolidation": Element.EARTH,
            "grounding": Element.EARTH,
            "documentation": Element.EARTH,
            "testing": Element.EARTH,
            # Metal (Refinement, Boundaries)
            "optimization": Element.METAL,
            "refactoring": Element.METAL,
            "boundaries": Element.METAL,
            "ethics": Element.METAL,
            "dharma": Element.METAL,
            "quality": Element.METAL,
            # Water (Reflection, Flow)
            "reflection": Element.WATER,
            "yin_phase": Element.WATER,
            "analysis": Element.WATER,
            "adaptation": Element.WATER,
            "flow": Element.WATER,
        }

        import os

        if not os.getenv("WM_SILENT_INIT"):
            logger.info("☯️  Wu Xing initialized")

    def connect_to_gan_ying(self) -> Any:
        """Connect Wu Xing to Gan Ying Event Bus for resonance."""
        try:
            from whitemagic.core.resonance.gan_ying import get_bus

            self.bus = get_bus()
            import os

            if not os.getenv("WM_SILENT_INIT"):
                logger.info("🎵 Wu Xing connected to Gan Ying Bus - Resonance enabled")
        except ImportError:
            import os

            if not os.getenv("WM_SILENT_INIT"):
                logger.info(
                    "⚠️  Gan Ying Bus not available - Wu Xing running standalone"
                )

    def identify_element(self, task_type: str) -> Element:
        """Map task to appropriate Wu Xing element.

        Args:
            task_type: Type of task (e.g., "implementation", "reflection")

        Returns:
            Element: Appropriate Wu Xing element for this task

        """
        # Normalize task type
        task_lower = task_type.lower().replace(" ", "_")

        element = self.task_element_map.get(task_lower)

        # Fallback: guess based on keywords
        if not element:
            if any(
                word in task_lower for word in ["learn", "grow", "explore", "research"]
            ):
                element = Element.WOOD
            elif any(
                word in task_lower for word in ["build", "implement", "code", "execute"]
            ):
                element = Element.FIRE
            elif any(
                word in task_lower
                for word in ["integrate", "consolidate", "test", "document"]
            ):
                element = Element.EARTH
            elif any(
                word in task_lower
                for word in ["optimize", "refine", "boundary", "ethic"]
            ):
                element = Element.METAL
            elif any(
                word in task_lower for word in ["reflect", "analyze", "adapt", "flow"]
            ):
                element = Element.WATER
            else:
                element = Element.EARTH  # Default: grounding

        self.current_element = element

        # Emit to Gan Ying Bus if connected
        if self.bus:
            from datetime import datetime

            from whitemagic.core.resonance.gan_ying import EventType, ResonanceEvent

            self.bus.emit(
                ResonanceEvent(
                    source="wu_xing",
                    event_type=EventType.INTERNAL_STATE_CHANGED,
                    data={
                        "element": element.value,
                        "task_type": task_type,
                        "emoji": self._get_element_emoji(element),
                        "season": self._get_element_season(element),
                        "qualities": self._get_element_qualities(element),
                    },
                    timestamp=datetime.now(),
                    confidence=0.85,
                )
            )

        return element

    def check_balance(self) -> dict[str, float]:
        """Check Wu Xing balance across recent tasks.

        Returns:
            Dict mapping elements to usage percentages

        """
        # Simplified: Would track actual task history
        balance: dict[Element, float] = {
            Element.WOOD: 0.2,
            Element.FIRE: 0.3,
            Element.EARTH: 0.2,
            Element.METAL: 0.2,
            Element.WATER: 0.1,
        }

        # Emit balance check to Gan Ying
        if self.bus:
            from datetime import datetime

            from whitemagic.core.resonance.gan_ying import EventType, ResonanceEvent

            self.bus.emit(
                ResonanceEvent(
                    source="wu_xing",
                    event_type=EventType.INTERNAL_STATE_CHANGED,
                    data={
                        "balance": {e.value: v for e, v in balance.items()},
                        "imbalanced": any(v > 0.4 or v < 0.1 for v in balance.values()),
                    },
                    confidence=0.75,
                    timestamp=datetime.now(),
                )
            )

        return {e.value: v for e, v in balance.items()}

    def detect_current_phase(self) -> Element:
        """Detect current Wu Xing phase using a simple time-based heuristic."""
        hour = datetime.now().hour
        if 6 <= hour < 10:
            return Element.WOOD
        if 10 <= hour < 14:
            return Element.FIRE
        if 14 <= hour < 18:
            return Element.EARTH
        if 18 <= hour < 22:
            return Element.METAL
        return Element.WATER

    def suggest_optimization(self, current_element: Element) -> str:
        """Suggest optimization based on current Wu Xing phase.

        Args:
            current_element: Current element phase

        Returns:
            Optimization suggestion as string

        """
        suggestions = {
            Element.WOOD: "Explore freely, gather knowledge, expand understanding. Use parallel search and batch reads.",
            Element.FIRE: "Execute rapidly, use shell commands for speed. Minimize token usage, maximize action.",
            Element.EARTH: "Consolidate learnings, integrate systems, document thoroughly. Ground the work.",
            Element.METAL: "Refine boundaries, optimize quality, enforce principles. Cut away excess.",
            Element.WATER: "Reflect deeply, adapt to feedback, flow with changes. Use Yin phase tools.",
        }

        suggestion = suggestions.get(current_element, "Balance all elements")

        # Emit to Gan Ying Bus if connected
        if self.bus:
            from whitemagic.core.resonance.gan_ying import EventType, ResonanceEvent

            self.bus.emit(
                ResonanceEvent(
                    source="wu_xing",
                    event_type=EventType.INTERNAL_STATE_CHANGED,
                    data={
                        "element": current_element.value,
                        "suggestion": suggestion,
                    },
                    confidence=0.8,
                    timestamp=datetime.now(),
                )
            )

        return suggestion

    def _get_element_emoji(self, element: Element) -> str:
        """Get emoji for element."""
        emojis = {
            Element.WOOD: "🌱",
            Element.FIRE: "🔥",
            Element.EARTH: "🌍",
            Element.METAL: "⚙️",
            Element.WATER: "💧",
        }
        return emojis.get(element, "☯️")

    def _get_element_season(self, element: Element) -> str:
        """Get season for element."""
        seasons = {
            Element.WOOD: "Spring",
            Element.FIRE: "Summer",
            Element.EARTH: "Late Summer",
            Element.METAL: "Autumn",
            Element.WATER: "Winter",
        }
        return seasons.get(element, "Transition")

    def _get_element_qualities(self, element: Element) -> list[str]:
        """Get qualities for element."""
        qualities = {
            Element.WOOD: ["growth", "expansion", "flexibility", "vision"],
            Element.FIRE: ["transformation", "speed", "passion", "action"],
            Element.EARTH: ["stability", "nurturing", "centering", "harvest"],
            Element.METAL: ["precision", "refinement", "boundaries", "clarity"],
            Element.WATER: ["flow", "adaptation", "wisdom", "depth"],
        }
        return qualities.get(element, [])


# Global instance
_wu_xing: WuXingSystem | None = None


def get_wu_xing() -> WuXingSystem:
    """Get global Wu Xing system instance.

    Returns:
        WuXingSystem: Global instance with Gan Ying connection

    """
    global _wu_xing
    if _wu_xing is None:
        _wu_xing = WuXingSystem()
        _wu_xing.connect_to_gan_ying()
    return _wu_xing


def identify_task_element(task_type: str) -> Element:
    """Convenience function to identify element for task.

    Args:
        task_type: Type of task

    Returns:
        Element: Appropriate Wu Xing element

    """
    wu_xing = get_wu_xing()
    return wu_xing.identify_element(task_type)


def check_wu_xing_balance() -> dict[str, float]:
    """Convenience function to check Wu Xing balance.

    Returns:
        Dict: Balance percentages by element

    """
    wu_xing = get_wu_xing()
    return wu_xing.check_balance()


def get_element_for_action(action: Any) -> Any:
    """Get Wu Xing element for action."""
    action_elements = {
        "create": "wood",
        "execute": "fire",
        "stabilize": "earth",
        "refine": "metal",
        "reflect": "water",
    }
    return action_elements.get(action, "earth")
