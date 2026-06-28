"""Feedback Controller - The Observer that Acts.
============================================

"The wise man adapts himself to circumstances, as water shapes itself to the vessel that contains it."

This module implements the missing feedback loop that connects observation (Patterns, Emergence)
to action (Behavior Modification, Session Context).
"""

from __future__ import annotations

import logging
from datetime import datetime

from whitemagic.core.intelligence.multi_spectral_reasoning import MultiSpectralReasoner
from whitemagic.core.resonance.gan_ying_enhanced import (
    EventType,
    ResonanceEvent,
    get_bus,
)
from whitemagic.session.manager import SessionManager

logger = logging.getLogger(__name__)

class FeedbackController:
    """Control loop that listens for system insights and adapts behavior.
    """

    def __init__(self) -> None:
        self._bus = get_bus()
        self._session_manager = SessionManager()
        self._reasoner = MultiSpectralReasoner()
        self._is_active = False
        self._pattern_counts: dict[str, int] = {}
        self._pattern_threshold = 5
        self._gain = 1.0

    def start(self) -> None:
        """Start the feedback loop."""
        if self._is_active:
            return

        logger.info("🧠 Feedback Controller ACTIVATED. Listening for insights...")

        # Subscribe to high-level cognitive events
        self._bus.listen(EventType.BREAKTHROUGH_ACHIEVED, self._on_breakthrough)
        self._bus.listen(EventType.PATTERN_DETECTED, self._on_pattern)
        self._bus.listen(EventType.INSIGHT_FLASH, self._on_insight)

        # Subscribe to state changes for session tracking
        self._bus.listen(EventType.SYSTEM_STATE_CHANGE, self._on_state_change)

        self._is_active = True

    def _on_breakthrough(self, event: ResonanceEvent) -> None:
        """Handle major breakthroughs.
        Action: Store in Session Context + Consult Council for Integration.
        """
        data = event.data
        pattern = data.get("core_pattern")

        logger.info("⚡ FeedbackController handling BREAKTHROUGH: %s", pattern)

        # 1. Enrich Active Session
        session = self._session_manager.get_active_session()
        if session:
            # Add to breakthroughs list
            if "breakthroughs" not in session.metrics:
                session.metrics["breakthroughs"] = []

            breakthrough = {
                "pattern": pattern,
                "timestamp": datetime.now().isoformat(),
                "confidence": event.confidence,
            }
            session.metrics["breakthroughs"].append(breakthrough)

            # Sync with accumulated_context
            session.accumulated_context.append(f"BREAKTHROUGH: {pattern}")

            self._session_manager.update_session(
                session.id,
                metrics=session.metrics,
                accumulated_context=session.accumulated_context,
            )

        # 2. Inject into Autonomous Awareness (lazy import — module is optional)
        try:
            from whitemagic.autonomous.continuous_awareness import (
                get_awareness,  # type: ignore[import-not-found]
            )
            awareness = get_awareness()
            awareness.inject_insight(f"BREAKTHROUGH: {pattern} (Confidence: {event.confidence})")
        except (ImportError, ModuleNotFoundError) as e:
            logger.warning("Could not inject insight into awareness: %s", e, exc_info=True)

        # 3. Consult Wisdom Council on how to integrate this
        # (Async dispatch to avoid blocking the event bus thread if not async)
        # For now, we log the intent.
        # self._consult_integration(pattern, data)

    def _on_pattern(self, event: ResonanceEvent) -> None:
        """Handle repeated patterns.
        Action: Track pattern frequency and adjust feedback gain.
        """
        pattern = event.data.get("pattern", "unknown")
        frequency = event.data.get("frequency", 1)

        # Update pattern tracking metrics
        if pattern not in self._pattern_counts:
            self._pattern_counts[pattern] = 0
        self._pattern_counts[pattern] += 1

        # If pattern is recurring frequently, increase feedback gain
        if frequency > self._pattern_threshold:
            self._gain = min(1.0, self._gain * 1.1)
            logger.debug("Pattern '%s' recurring (freq=%d) — gain increased to %.2f",
                        pattern, frequency, self._gain)

    def _on_insight(self, event: ResonanceEvent) -> None:
        """Handle sudden insights (Flash).
        Action: Highlight in Session.
        """
        content = event.data.get("content")
        session = self._session_manager.get_active_session()
        if session and content:
            if "insights" not in session.context:
                session.context["insights"] = []
            session.context["insights"].append(content)

            # Also add to accumulated context for cross-session coherence
            session.accumulated_context.append(f"INSIGHT: {content}")

            self._session_manager.update_session(
                session.id,
                context=session.context,
                accumulated_context=session.accumulated_context,
            )

    def _on_state_change(self, event: ResonanceEvent) -> None:
        """Monitor system state for stability.
        Action: Log state transitions and detect instability patterns.
        """
        state = event.data.get("state", "unknown")
        stability = event.data.get("stability", 1.0)

        # Log state transition
        logger.debug("System state changed: %s (stability=%.2f)", state, stability)

        # If stability drops below threshold, reduce feedback gain
        if stability < 0.3:
            self._gain = max(0.1, self._gain * 0.9)
            logger.warning("System instability detected (stability=%.2f) — gain reduced to %.2f",
                          stability, self._gain)

        # Update session with state change
        session = self._session_manager.get_active_session()
        if session:
            if "state_history" not in session.context:
                session.context["state_history"] = []
            session.context["state_history"].append({
                "state": state,
                "stability": stability,
                "timestamp": datetime.now().isoformat(),
            })

_controller = None

def get_feedback_controller() -> FeedbackController:
    """
    Get the feedback controller.

    Returns:
        FeedbackController
    """
    global _controller
    if _controller is None:
        _controller = FeedbackController()
    return _controller
