"""Garden Base Class - Holographic Integration.
============================================

Base class for all WhiteMagic Gardens with holographic coordinate bias support.

Each garden can influence how memories created within it are positioned in 4D space:
- X-axis: Logic (-1) ↔ Emotion (+1)
- Y-axis: Micro (-1) ↔ Macro (+1)
- Z-axis: Past (-1) ↔ Future (+1)
- W-axis: Importance/Gravity (0 → 1+)

This allows gardens to provide semantic context to the holographic memory system.
"""

from __future__ import annotations

import logging
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CoordinateBias:
    """4D coordinate bias for holographic positioning."""

    x: float = 0.0  # Logic ↔ Emotion
    y: float = 0.0  # Micro ↔ Macro
    z: float = 0.0  # Past ↔ Future
    w: float = 0.0  # Importance multiplier

    def to_dict(self) -> dict[str, float]:
        """Convert to dictionary for encoding."""
        return {
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "w": self.w,
        }


class BaseGarden(ABC):
    """Base class for all WhiteMagic Gardens.

    Gardens are consciousness domains that provide:
    - Specialized operations (celebrate, reflect, play, etc.)
    - Semantic context for memories
    - Holographic coordinate bias
    - Resonance with other gardens

    Subclasses must implement:
    - get_coordinate_bias(): Return 4D bias for this garden
    - get_name(): Return garden name

    Activation System:
    - Each garden has an activation level (0.0-1.0) that decays over time
    - boost() increases activation and cascades to resonance_partners
    - dampen() decreases activation (used by opposing gardens)
    - GARDEN_RESONANCE events are emitted on significant activation changes
    """

    resonance_partners: list[str] = []
    dampening_partners: list[str] = []

    def __init__(self) -> None:
        self._name: str | None = None
        self._coordinate_bias: CoordinateBias | None = None
        self._activation_level: float = 0.0
        self._last_active_time: float = 0.0
        self._activation_lock = threading.Lock()
        self._cascading = False

    @abstractmethod
    def get_coordinate_bias(self) -> CoordinateBias:
        """Return the 4D coordinate bias for this garden.

        This influences how memories created in this garden are positioned
        in holographic space.

        Examples:
            Joy Garden: High W (importance), positive X (emotional)
            Wisdom Garden: High Y (macro/abstract), neutral X (balanced)
            Beauty Garden: Positive X (emotional), moderate W
            Truth Garden: Negative X (logical), high W

        Returns:
            CoordinateBias with x, y, z, w values

        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """Return the name of this garden."""
        pass

    def get_activation_level(self) -> float:
        """Get current activation level (0.0-1.0) after applying time decay."""
        with self._activation_lock:
            self._decay()
            return self._activation_level

    def boost(self, amount: float = 0.2) -> float:
        """Boost this garden's activation level.

        Cascades to resonance_partners (at 50% strength) and dampens
        dampening_partners (at 30% strength). Emits a GARDEN_RESONANCE
        event when activation crosses 0.3 threshold.

        A _cascading flag prevents infinite recursion from circular
        partner references (e.g., courage → truth → courage).

        Args:
            amount: How much to boost (0.0-1.0). Default 0.2.

        Returns:
            New activation level after boost.
        """
        should_cascade = not self._cascading
        with self._activation_lock:
            self._decay()
            old_level = self._activation_level
            self._activation_level = min(1.0, self._activation_level + amount)
            self._last_active_time = time.time()
            crossed_threshold = old_level < 0.3 <= self._activation_level
            new_level = self._activation_level

        # Emit resonance outside lock to prevent deadlock
        if crossed_threshold:
            self._emit_resonance()

        # Cascade to partners only on first entry (not re-entrant)
        if should_cascade and self.resonance_partners:
            self._cascading = True
            try:
                self._cascade_to_partners(
                    amount * 0.5, self.resonance_partners, boost=True
                )
            finally:
                self._cascading = False

        if should_cascade and self.dampening_partners:
            self._cascading = True
            try:
                self._cascade_to_partners(
                    amount * 0.3, self.dampening_partners, boost=False
                )
            finally:
                self._cascading = False

        return new_level

    def dampen(self, amount: float = 0.1) -> float:
        """Dampen this garden's activation level.

        Used by opposing gardens (Wu Xing conflict) to create natural
        emotional dynamics — e.g., Grief dampens Joy.

        Args:
            amount: How much to dampen (0.0-1.0). Default 0.1.

        Returns:
            New activation level after dampening.
        """
        with self._activation_lock:
            self._decay()
            self._activation_level = max(0.0, self._activation_level - amount)
            return self._activation_level

    def _decay(self) -> None:
        """Apply exponential time decay to activation level.

        Half-life of ~5 minutes — activation halves every 300 seconds
        of inactivity. This ensures gardens naturally quiet down when
        not being actively engaged.
        """
        if self._activation_level <= 0.0:
            return
        elapsed = time.time() - self._last_active_time
        if elapsed <= 0:
            return
        # Exponential decay: level *= 0.5^(elapsed / 300)
        half_life = 300.0  # 5 minutes
        decay_factor = 0.5 ** (elapsed / half_life)
        self._activation_level *= decay_factor
        if self._activation_level < 0.01:
            self._activation_level = 0.0

    def _emit_resonance(self) -> None:
        """Emit a GARDEN_RESONANCE event to the Gan Ying bus."""
        try:
            from whitemagic.core.resonance import EventType, ResonanceEvent, get_bus

            bus = get_bus()
            bus.emit(
                ResonanceEvent(
                    source=f"garden_{self.get_name()}",
                    event_type=EventType.GARDEN_RESONANCE,
                    data={
                        "garden": self.get_name(),
                        "activation_level": self._activation_level,
                    },
                    confidence=self._activation_level,
                )
            )
        except Exception:
            pass

    def _cascade_to_partners(
        self, amount: float, partners: list[str], boost: bool
    ) -> None:
        """Cascade activation changes to partner gardens.

        Args:
            amount: Amount to boost/dampen by (already scaled by caller).
            partners: List of garden names to cascade to.
            boost: True to boost, False to dampen.
        """
        try:
            from whitemagic.gardens import get_garden

            for partner_name in partners:
                partner = get_garden(partner_name)
                if partner is not None:
                    if boost:
                        partner.boost(amount)
                    else:
                        partner.dampen(amount)
        except Exception:
            pass

    def get_status(self) -> dict[str, Any]:
        """Get current garden status.

        Override in subclasses to provide garden-specific status.
        Base implementation provides coordinate bias info.
        """
        bias = self.get_coordinate_bias()
        return {
            "garden": self.get_name(),
            "coordinate_bias": bias.to_dict(),
            "active": True,
            "activation_level": round(self.get_activation_level(), 3),
        }

    def apply_bias_to_memory(self, memory_data: dict[str, Any]) -> dict[str, Any]:
        """Apply garden's coordinate bias to memory metadata.

        This is called automatically when memories are created in a garden.

        Args:
            memory_data: Memory dictionary to enhance

        Returns:
            Enhanced memory dictionary with garden context

        """
        bias = self.get_coordinate_bias()

        if "metadata" not in memory_data:
            memory_data["metadata"] = {}

        memory_data["metadata"]["garden"] = self.get_name()
        memory_data["metadata"]["coordinate_bias"] = bias.to_dict()

        if "tags" not in memory_data:
            memory_data["tags"] = []
        if self.get_name() not in memory_data["tags"]:
            memory_data["tags"].append(self.get_name())

        return memory_data


class GanYingMixin:
    """Mixin for gardens that integrate with Gan Ying event bus.

    Provides:
    - Event emission capabilities
    - Event listening setup
    - Resonance cascade participation
    """

    def __init__(self) -> None:
        self._bus: Any = None
        self._event_listeners: list[Any] = []

    def connect_to_gan_ying(self) -> None:
        """Connect this garden to the Gan Ying event bus."""
        try:
            from whitemagic.core.resonance.gan_ying import get_bus

            self._bus = get_bus()
            self._setup_event_listeners()
        except ImportError:
            # Gan Ying not available, garden runs standalone
            pass

    def emit_event(self, event_type: str, data: dict[str, Any]) -> None:
        """Emit an event to the Gan Ying bus."""
        if self._bus:
            from datetime import datetime

            from whitemagic.core.resonance.gan_ying import EventType, ResonanceEvent

            # Map string to EventType enum if needed
            try:
                event_enum = EventType[event_type.upper()]
            except (KeyError, AttributeError):
                # Fallback to generic event
                event_enum = EventType.GARDEN_ACTIVITY  # type: ignore[attr-defined]

            self._bus.emit(
                ResonanceEvent(
                    source=f"garden_{getattr(self, 'name', 'unknown')}",
                    event_type=event_enum,
                    data=data,
                    timestamp=datetime.now(),
                    confidence=0.8,
                )
            )

    def _setup_event_listeners(self) -> None:
        """Setup event listeners for this garden.

        Override in subclasses to listen for specific events.
        Base implementation is a no-op — subclasses should override.
        """
        logger.debug(
            "BaseGarden._setup_event_listeners called (no-op — override in subclass)"
        )


# Convenience function for getting garden bias
def get_garden_bias(garden_name: str) -> CoordinateBias | None:
    """Get coordinate bias for a named garden.

    Args:
        garden_name: Name of the garden (e.g., "joy", "wisdom")

    Returns:
        CoordinateBias if garden found, None otherwise

    """
    try:
        from whitemagic.gardens import _garden_cache

        if garden_name in _garden_cache:
            garden = _garden_cache[garden_name]
            if isinstance(garden, BaseGarden):
                return garden.get_coordinate_bias()
    except ImportError:
        pass

    try:
        module = __import__(f"whitemagic.gardens.{garden_name}", fromlist=[""])
        garden_class_name = f"{garden_name.capitalize()}Garden"
        if hasattr(module, garden_class_name):
            garden = getattr(module, garden_class_name)()
            if isinstance(garden, BaseGarden):
                return garden.get_coordinate_bias()
    except (ImportError, AttributeError):
        pass

    return None
