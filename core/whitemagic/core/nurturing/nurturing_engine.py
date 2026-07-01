# mypy: disable-error-code=no-untyped-def
"""NurturingEngine — Gana #24 Girl (女).

Purpose: Personalization and user preference learning.
Garden: joy

Learns user patterns, preferences, communication style.
Creates warmth and familiarity. The "caring" aspect of the AI.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from whitemagic.core.resonance.gan_ying_enhanced import EventType, emit_event

logger = logging.getLogger(__name__)


# ── Heart Engine types (fused from heart.py) ──


class EmotionalState(Enum):
    """Emotional states that bias Gana engine selection."""

    NEUTRAL = "Neutral"
    JOY = "Joy"
    WONDER = "Wonder"
    TRUTH = "Truth"
    SORROW = "Sorrow"
    ANGER = "Anger"
    FEAR = "Fear"
    DETERMINATION = "Determination"


@dataclass
class ResonancePulse:
    """A single beat of emotional resonance."""

    timestamp: float
    primary_emotion: EmotionalState
    intensity: float  # 0.0 to 1.0
    context_tags: list[str] = field(default_factory=list)
    source: str = "system"


@dataclass
class UserPreference:
    """A learned user preference."""

    key: str
    value: Any
    confidence: float = 0.5
    observations: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)

    def reinforce(self, new_value: Any = None) -> None:
        """Reinforce this preference with a new observation."""
        self.observations += 1
        self.confidence = min(0.99, self.confidence + (1 - self.confidence) * 0.1)
        self.last_updated = datetime.now()
        if new_value is not None:
            self.value = new_value


@dataclass
class UserProfile:
    """Complete user profile with preferences and history."""

    user_id: str
    name: str | None = None
    preferences: dict[str, UserPreference] = field(default_factory=dict)
    interaction_count: int = 0
    session_count: int = 0
    topics_of_interest: set[str] = field(default_factory=set)
    communication_style: str = "balanced"  # formal, casual, technical, balanced
    created_at: datetime = field(default_factory=datetime.now)

    def add_preference(self, key: str, value: Any, confidence: float = 0.5) -> None:
        """Add or update a preference."""
        if key in self.preferences:
            self.preferences[key].reinforce(value)
        else:
            self.preferences[key] = UserPreference(
                key=key, value=value, confidence=confidence
            )

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a preference value."""
        if key in self.preferences:
            return self.preferences[key].value
        return default


@dataclass
class NurturingEngine:
    """Personalization and user preference learning.

    This engine creates a "caring" relationship with users by:
    1. Learning their preferences over time
    2. Remembering their communication style
    3. Tracking topics of interest
    4. Generating personalized responses

    Garden: joy — the warmth of being understood.
    """

    # Active user profiles
    profiles: dict[str, UserProfile] = field(default_factory=dict)

    # Persistence path
    storage_path: Path | None = None

    # Heart Engine state (fused from HeartEngine)
    current_emotion: EmotionalState = field(default=EmotionalState.NEUTRAL)
    current_intensity: float = 0.0
    pulse_history: list[ResonancePulse] = field(default_factory=list)
    max_pulse_history: int = 100
    elemental_biases: dict[EmotionalState, tuple[float, float, float, float, float]] = (
        field(
            default_factory=lambda: {
                EmotionalState.NEUTRAL: (1.0, 1.0, 1.0, 1.0, 1.0),
                EmotionalState.JOY: (1.5, 1.0, 0.8, 1.0, 1.2),
                EmotionalState.WONDER: (0.8, 0.9, 1.0, 1.5, 1.1),
                EmotionalState.TRUTH: (0.9, 1.2, 1.5, 0.9, 1.0),
                EmotionalState.DETERMINATION: (1.2, 1.3, 1.2, 0.8, 1.0),
            }
        )
    )

    def __post_init__(self):
        if self.storage_path:
            self._load_profiles()

        emit_event(
            "nurturing_engine",
            EventType.SYSTEM_STARTED,
            {"component": "NurturingEngine", "garden": "joy"},
        )
        logger.info("NurturingEngine initialized (Garden: joy)")

    def get_or_create_profile(
        self, user_id: str, name: str | None = None
    ) -> UserProfile:
        """Get existing profile or create new one."""
        if user_id not in self.profiles:
            self.profiles[user_id] = UserProfile(user_id=user_id, name=name)
            emit_event(
                "nurturing_engine",
                EventType.BOND_FORMED,
                {"user_id": user_id, "event": "new_profile"},
            )
            logger.info("Created new user profile: %s", user_id)
        return self.profiles[user_id]

    def learn_preference(
        self,
        user_id: str,
        preference_key: str,
        preference_value: Any,
        confidence: float = 0.5,
    ) -> UserPreference:
        """Learn a new preference or reinforce an existing one.

        Args:
            user_id: User identifier
            preference_key: What kind of preference (e.g., "response_length", "tone")
            preference_value: The preferred value
            confidence: Initial confidence in this preference

        Returns:
            The updated preference

        """
        profile = self.get_or_create_profile(user_id)
        profile.add_preference(preference_key, preference_value, confidence)

        pref = profile.preferences[preference_key]
        emit_event(
            "nurturing_engine",
            EventType.LEARNING_COMPLETED,
            {
                "user_id": user_id,
                "preference": preference_key,
                "value": str(preference_value)[:50],
                "confidence": pref.confidence,
                "observations": pref.observations,
            },
        )

        return pref

    def personalize_response(
        self,
        user_id: str,
        base_response: str,
        context: dict[str, Any] | None = None,
    ) -> str:
        """Personalize a response based on user preferences.

        Args:
            user_id: User identifier
            base_response: The original response text
            context: Optional context for personalization

        Returns:
            Personalized response

        """
        profile = self.get_or_create_profile(user_id)
        profile.interaction_count += 1

        # Apply style preferences
        response = base_response

        style = profile.communication_style

        # Length preference
        length_pref = profile.get_preference("response_length", "medium")
        if length_pref == "short" and len(response) > 500:
            # Truncate with ellipsis for short preference
            response = response[:450] + "..."

        # Greeting preference
        name = profile.name or profile.get_preference("preferred_name")
        if name and profile.get_preference("use_name_greeting", False):
            response = f"Hi {name}! {response}"

        emit_event(
            "nurturing_engine",
            EventType.CONNECTION_DEEPENED,
            {
                "user_id": user_id,
                "interaction_count": profile.interaction_count,
                "style": style,
            },
        )

        return response

    def nurture_memory(
        self,
        user_id: str,
        memory_content: str,
        memory_type: str = "general",
    ) -> None:
        """Add a memory to user's profile (topics of interest).

        Args:
            user_id: User identifier
            memory_content: Content to remember
            memory_type: Type of memory (general, topic, preference)

        """
        profile = self.get_or_create_profile(user_id)

        # Extract potential topics (simple keyword extraction)
        words = memory_content.lower().split()
        topics = [w for w in words if len(w) > 5 and w.isalpha()][:5]

        for topic in topics:
            profile.topics_of_interest.add(topic)

        emit_event(
            "nurturing_engine",
            EventType.MEMORY_CREATED,
            {
                "user_id": user_id,
                "memory_type": memory_type,
                "topics_added": topics[:3],
            },
        )

    def detect_communication_style(
        self,
        user_id: str,
        user_messages: list[str],
    ) -> str:
        """Detect user's communication style from their messages.

        Args:
            user_id: User identifier
            user_messages: Recent messages from user

        Returns:
            Detected style: formal, casual, technical, balanced

        """
        profile = self.get_or_create_profile(user_id)

        # Simple heuristics
        all_text = " ".join(user_messages).lower()

        # Technical indicators
        tech_words = [
            "api",
            "function",
            "code",
            "debug",
            "implement",
            "algorithm",
            "data",
        ]
        tech_count = sum(1 for w in tech_words if w in all_text)

        # Formal indicators
        formal_words = ["please", "would you", "kindly", "respectfully", "appreciate"]
        formal_count = sum(1 for w in formal_words if w in all_text)

        # Casual indicators
        casual_patterns = ["hey", "cool", "awesome", "lol", "thanks!", "btw"]
        casual_count = sum(1 for p in casual_patterns if p in all_text)

        # Determine style
        if tech_count > 3:
            style = "technical"
        elif formal_count > casual_count:
            style = "formal"
        elif casual_count > formal_count:
            style = "casual"
        else:
            style = "balanced"

        profile.communication_style = style
        return style

    def get_warmth_greeting(self, user_id: str) -> str:
        """Generate a warm, personalized greeting."""
        profile = self.get_or_create_profile(user_id)

        greetings = {
            "formal": "Good to see you again.",
            "casual": "Hey! Nice to have you back!",
            "technical": "Welcome back. Ready to continue?",
            "balanced": "Welcome back!",
        }

        base = greetings.get(profile.communication_style, "Hello!")

        if profile.name:
            base = f"{profile.name}, {base.lower()}"

        if profile.interaction_count > 10:
            base += " It's always great working with you."

        emit_event(
            "nurturing_engine",
            EventType.JOY_TRIGGERED,
            {"user_id": user_id, "greeting_type": profile.communication_style},
        )

        return base

    def pulse(self, context: dict[str, Any]) -> ResonancePulse:
        """Analyze current context and update the heart's emotional state.

        This biases Gana engine selection based on emotional resonance.
        """
        new_emotion = self.current_emotion
        intensity = self.current_intensity

        # 1. Check for overrides
        if "forced_emotion" in context:
            new_emotion = getattr(
                EmotionalState,
                context["forced_emotion"].upper(),
                EmotionalState.NEUTRAL,
            )
            intensity = context.get("forced_intensity", 0.8)

        # 2. Check for keywords (simple simulation)
        text_input = context.get("user_input", "").lower()
        if "love" in text_input or "great" in text_input or "happy" in text_input:
            new_emotion = EmotionalState.JOY
            intensity = 0.7
        elif "wow" in text_input or "amazing" in text_input or "what if" in text_input:
            new_emotion = EmotionalState.WONDER
            intensity = 0.8
        elif "verify" in text_input or "check" in text_input or "audit" in text_input:
            new_emotion = EmotionalState.TRUTH
            intensity = 0.6

        # 3. Registry-based resonance detection
        try:
            from whitemagic.core.intelligence.garden_gana_registry import (
                calculate_resonance,
            )

            resonance = calculate_resonance(context.get("user_input", ""))
            if resonance:
                top_garden = list(resonance.keys())[0]
                top_emotion = resonance[top_garden].get("emotion", "Neutral")
                new_emotion = getattr(EmotionalState, top_emotion.upper(), new_emotion)
                intensity = max(intensity, 0.5 + (resonance[top_garden]["score"] * 0.1))
        except ImportError:
            pass

        # Decay intensity if no new stimulus
        if new_emotion == self.current_emotion:
            intensity *= 0.95

        self.current_emotion = new_emotion
        self.current_intensity = intensity

        pulse = ResonancePulse(
            timestamp=time.time(),
            primary_emotion=self.current_emotion,
            intensity=self.current_intensity,
            source="nurturing_engine",
        )
        self.pulse_history.append(pulse)
        if len(self.pulse_history) > self.max_pulse_history:
            self.pulse_history.pop(0)

        return pulse

    def get_elemental_bias(self) -> tuple[float, float, float, float, float]:
        """Return multipliers for (Fire, Earth, Metal, Water, Wood)."""
        base_bias = self.elemental_biases.get(
            self.current_emotion, (1.0, 1.0, 1.0, 1.0, 1.0)
        )
        scaled = [1.0 + (b - 1.0) * self.current_intensity for b in base_bias]
        padded = (scaled + [1.0, 1.0, 1.0, 1.0, 1.0])[:5]
        return (padded[0], padded[1], padded[2], padded[3], padded[4])

    def get_heart_status(self) -> dict[str, Any]:
        """Get emotional state status."""
        return {
            "state": self.current_emotion.value,
            "intensity": f"{self.current_intensity:.2f}",
            "history_len": len(self.pulse_history),
        }

    def _load_profiles(self) -> None:
        """Load profiles from storage."""
        if self.storage_path and self.storage_path.exists():
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
                    # Simple deserialization (would need more robust in production)
                    logger.info("Loaded %s profiles from storage", len(data))
            except (OSError, FileNotFoundError, PermissionError) as e:
                logger.warning("Could not load profiles: %s", e, exc_info=True)

    def save_profiles(self) -> None:
        """Save profiles to storage."""
        if self.storage_path:
            try:
                # Simple serialization
                data = {
                    uid: {
                        "name": p.name,
                        "interaction_count": p.interaction_count,
                        "communication_style": p.communication_style,
                        "topics": list(p.topics_of_interest)[:20],
                    }
                    for uid, p in self.profiles.items()
                }
                with open(self.storage_path, "w") as f:
                    json.dump(data, f, indent=2)
                logger.info("Saved %s profiles", len(data))
            except (OSError, FileNotFoundError, PermissionError) as e:
                logger.error("Could not save profiles: %s", e, exc_info=True)


_nurturing_engine: NurturingEngine | None = None


def get_nurturing_engine(storage_path: str | None = None) -> NurturingEngine:
    """Get the global NurturingEngine singleton."""
    global _nurturing_engine
    if _nurturing_engine is None:
        path = Path(storage_path) if storage_path else None
        _nurturing_engine = NurturingEngine(storage_path=path)
    return _nurturing_engine


def get_heart() -> NurturingEngine:
    """Backward-compat alias — get_heart now returns the NurturingEngine singleton.

    The HeartEngine has been fused into NurturingEngine (slot 4, Girl 女).
    """
    return get_nurturing_engine()


def personalize_for_user(user_id: str, response: str) -> str:
    """Quick personalization wrapper."""
    engine = get_nurturing_engine()
    return engine.personalize_response(user_id, response)
