"""Governor safety tool handlers."""
from typing import Any


def handle_governor_validate(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.core.governor import get_governor
    command = kwargs.get("command", "ls")
    result = get_governor().validate_command(command)
    return {"status": "success", **result.to_dict()}


def handle_governor_validate_path(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.core.governor import get_governor
    result = get_governor().validate_path(
        kwargs.get("path", ""),
        kwargs.get("operation", "access"),
    )
    return {"status": "success", **result.to_dict()}


def handle_governor_set_goal(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.core.governor import get_governor
    goal = kwargs.get("goal", "System safety")
    get_governor().set_goal(goal)
    return {"status": "success", "goal_set": goal}


def handle_governor_check_drift(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.core.governor import get_governor
    action = kwargs.get("action", "read")
    goal = kwargs.get("goal", "System safety")
    result = get_governor().check_drift(
        action,
        goal,
    )
    return {"status": "success", **result.to_dict()}


def handle_governor_check_budget(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.core.governor import get_governor
    result = get_governor().check_budget()
    return {"status": "success", **result.to_dict()}


def handle_governor_check_dharma(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.core.governor import get_governor
    result = get_governor().check_dharma(
        kwargs.get("action", ""),
        kwargs.get("context", {}),
    )
    return {"status": "success", **result.to_dict()}


def handle_governor_stats(**kwargs: Any) -> dict[str, Any]:
    from whitemagic.core.governor import get_governor
    return {"status": "success", **get_governor().stats()}
