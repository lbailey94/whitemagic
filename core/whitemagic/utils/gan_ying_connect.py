"""Shared Gan Ying Bus connection — replaces 10 duplicate _connect_to_gan_ying methods.

Usage:
    from whitemagic.utils.gan_ying_connect import connect_to_bus

    class MyGarden:
        def __init__(self):
            self.bus = connect_to_bus("MyGarden")
            if self.bus:
                self.bus.listen(EventType.PATTERN_DETECTED, self._handler)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def connect_to_bus(component_name: str = "component") -> Any:
    """Connect to the Gan Ying Bus, returning the bus or None on failure.

    Args:
        component_name: Name for logging (e.g. "Joy Resonance").

    Returns:
        The GanYingBus instance, or None if unavailable.
    """
    try:
        from whitemagic.core.resonance.gan_ying import get_bus

        bus = get_bus()
        logger.info("%s connected to Gan Ying Bus", component_name)
        return bus
    except ImportError:
        logger.debug("%s: Gan Ying not available — remaining localized", component_name)
        return None
    except Exception as e:
        logger.debug("%s: Gan Ying connection failed: %s", component_name, e)
        return None
