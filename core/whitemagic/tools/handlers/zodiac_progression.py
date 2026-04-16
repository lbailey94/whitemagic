"""MCP handler for Unified Zodiacal Progression status (Bridge 1 — Telemetric Qi)."""
from typing import Any


def handle_zodiac_status(**kwargs: Any) -> dict[str, Any]:
    """Return the current phase of the UnifiedProgressionDaemon."""
    from whitemagic.core.governance.unified_progression import get_progression_daemon
    daemon = get_progression_daemon()
    return {
        "status": "success",
        "running": daemon.running,
        "zodiac_phase": daemon.state.current_phase.value,
        "wu_xing": daemon.state.wu_xing.value,
        "yin_yang": daemon.state.yin_yang.value,
        "cycle_count": daemon.state.cycle_count,
        "total_activations": daemon.state.total_activations,
        "tick_duration_seconds": daemon.tick_duration,
    }
