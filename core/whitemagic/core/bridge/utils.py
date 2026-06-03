
import logging
from typing import Any

from whitemagic.utils.fast_json import dumps_str as _json_dumps

logger = logging.getLogger(__name__)

def ensure_string(value: Any, **kwargs: Any) -> str | None:
    """Ensure value is a string. If it's a dict/list (JSON), dump it to string.
    This fixes issues with models like GLM 4.7 passing JSON objects for string fields.
    """
    if value is None:
        return None
    if isinstance(value, (dict, list)):
        try:
            return _json_dumps(value)
        except (TypeError, ValueError):
            return str(value)
    return str(value)

def get_system_time(**kwargs: Any) -> dict[str, Any]:
    """Get system time and temporal context."""
    try:
        from whitemagic.core.temporal import get_system_time as _get_time
        return _get_time()
    except Exception:
        from datetime import datetime
        return {"iso": datetime.now().isoformat(), "source": "python_fallback"}

def _emit_resonance_event(event_type: str, data: dict[str, Any], source: str = "mcp_api_bridge", **kwargs: Any) -> None:
    try:
        from whitemagic.core.resonance.gan_ying import ResonanceEvent, get_bus
        from whitemagic.core.resonance.gan_ying_enhanced import EventType
        bus = get_bus()
        if event_type in EventType.__members__:
            event = ResonanceEvent(source=source, event_type=EventType[event_type], data=data)
            bus.emit(event)
        else:
            event = ResonanceEvent(source=source, event_type=EventType.SYSTEM_STATE_CHANGE, data={"event_type": event_type, **data})
            bus.emit(event)
    except Exception:
        pass
