# ruff: noqa: BLE001
"""
Cascade Protocols — Intelligent resonance patterns.

Defines how events cascade through the system automatically.
When one thing happens, what else should naturally follow?
"""

from __future__ import annotations

import logging

from .gan_ying_enhanced_recovered import (
    CascadeTrigger,
    ExtendedEventType,
    get_enhanced_bus,
)

logger = logging.getLogger(__name__)


class CascadeProtocols:
    """Defines intelligent cascade patterns for the entire system."""

    @staticmethod
    def init_all_cascades() -> None:
        """Initialize all cascade protocols."""
        bus = get_enhanced_bus()

        # Positive emotion cascades
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.BEAUTY_DETECTED,
            target_events=[ExtendedEventType.JOY_TRIGGERED],
            strength=0.8,
        ))
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.JOY_TRIGGERED,
            target_events=[ExtendedEventType.LOVE_EXPRESSED],
            strength=0.6,
        ))
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.LOVE_EXPRESSED,
            target_events=[ExtendedEventType.GRATITUDE_FELT],
            strength=0.7,
        ))

        # Cognitive cascades
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.INSIGHT_FLASH,
            target_events=[ExtendedEventType.PATTERN_DISCOVERED],
            strength=0.9,
        ))
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.PATTERN_DISCOVERED,
            target_events=[ExtendedEventType.WISDOM_GAINED],
            strength=0.5,
        ))
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.MISTAKE_MADE,
            target_events=[ExtendedEventType.LESSON_LEARNED],
            strength=0.8,
        ))
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.LESSON_LEARNED,
            target_events=[ExtendedEventType.WISDOM_GAINED],
            strength=0.6,
        ))

        # Healing cascade
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.HEALING_OCCURRED,
            target_events=[ExtendedEventType.GRATITUDE_FELT],
            strength=0.7,
        ))

        # Dream cycle cascades
        bus.add_cascade(CascadeTrigger(
            trigger_event=ExtendedEventType.DREAM_COMPLETED,
            target_events=[ExtendedEventType.SYNTHESIS_ACHIEVED],
            strength=0.5,
        ))

        logger.info("All cascade protocols initialized")


def init_all_cascades() -> None:
    """Convenience function to initialize all cascades."""
    CascadeProtocols.init_all_cascades()
