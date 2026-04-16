# Cyberbrain Global Workspace
# Adapting from MandalaOS/Cyberbrain concepts
import time
from typing import Any


class GlobalWorkspace:
    """
    A high-bandwidth bus where all cores publish state events.
    Enforces arbitration based on salience score (urgency + novelty).
    """
    def __init__(self):
        self.events = []
        self.active_core = None

    def publish_event(self, core_id: str, event_type: str, payload: dict[str, Any], salience: float):
        event = {
            "timestamp": time.time(),
            "core": core_id,
            "type": event_type,
            "payload": payload,
            "salience": salience
        }
        self.events.append(event)
        self._arbitrate()

    def _arbitrate(self):
        if not self.events:
            return

        # Sort by salience descending
        self.events.sort(key=lambda x: x["salience"], reverse=True)
        top_event = self.events[0]

        if top_event["salience"] > 0.8:
            self.active_core = top_event["core"]
            # Dispatch to active core (simulated)

    def get_state(self):
        return {
            "active_core": self.active_core,
            "event_backlog": len(self.events)
        }
