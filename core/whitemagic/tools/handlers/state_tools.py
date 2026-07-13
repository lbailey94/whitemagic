"""Current state tool handlers — gives AI agents live work context.

Provides MCP tools for querying and updating the current work state,
replacing reliance on static .md docs for short-term context.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_state_current(**kwargs: Any) -> dict[str, Any]:
    """Get the current work state snapshot.

    Returns the live state including current task, active tasks, next steps,
    recent file modifications, and context. This is the primary tool an AI
    agent should call on connecting to understand what to work on next.
    """
    from whitemagic.core.memory.current_state import get_state_tracker

    tracker = get_state_tracker()
    state = tracker.get_state()
    context_block = tracker.get_context_block()

    return {
        "status": "success",
        "state": state,
        "formatted": context_block,
    }


def handle_state_update(**kwargs: Any) -> dict[str, Any]:
    """Update the current work state.

    Accepts any combination of:
    - current_task: Set what's being worked on now
    - add_active_task: Add an active task
    - complete_task: Mark a task as completed
    - add_next_step: Add a next step
    - clear_next_steps: Clear all next steps
    - set_context: Set a context key (requires context_key + context_value)
    - record_file: Record a file modification (requires file_path)
    - record_decision: Record a decision (requires decision_text)
    - record_error: Record an error (requires error_text)
    """
    from whitemagic.core.memory.current_state import get_state_tracker

    tracker = get_state_tracker()
    updates: list[str] = []

    current_task = kwargs.get("current_task")
    if current_task:
        tracker.set_current_task(current_task)
        updates.append(f"current_task: {current_task}")

    add_active_task = kwargs.get("add_active_task")
    if add_active_task:
        tracker.add_active_task(add_active_task)
        updates.append(f"active_task added: {add_active_task}")

    complete_task = kwargs.get("complete_task")
    if complete_task:
        tracker.complete_task(complete_task)
        updates.append(f"task completed: {complete_task}")

    add_next_step = kwargs.get("add_next_step")
    if add_next_step:
        tracker.add_next_step(add_next_step)
        updates.append(f"next_step added: {add_next_step}")

    if kwargs.get("clear_next_steps"):
        tracker.clear_next_steps()
        updates.append("next_steps cleared")

    context_key = kwargs.get("context_key")
    context_value = kwargs.get("context_value")
    if context_key and context_value is not None:
        tracker.set_context(context_key, context_value)
        updates.append(f"context.{context_key} set")

    file_path = kwargs.get("record_file")
    if file_path:
        file_desc = kwargs.get("file_description", "")
        tracker.record_file_modification(file_path, file_desc)
        updates.append(f"file recorded: {file_path}")

    decision_text = kwargs.get("record_decision")
    if decision_text:
        rationale = kwargs.get("decision_rationale", "")
        tracker.record_decision(decision_text, rationale)
        updates.append(f"decision recorded: {decision_text}")

    error_text = kwargs.get("record_error")
    if error_text:
        error_context = kwargs.get("error_context", "")
        tracker.record_error(error_text, error_context)
        updates.append(f"error recorded: {error_text}")

    # Generic field updates
    for field_name in ("last_session_summary", "last_session_id"):
        val = kwargs.get(field_name)
        if val:
            tracker.update(**{field_name: val})
            updates.append(f"{field_name} set")

    return {
        "status": "success",
        "message": f"State updated: {', '.join(updates)}" if updates else "No updates provided",
        "updates": updates,
        "state": tracker.get_state(),
    }


def handle_state_context(**kwargs: Any) -> dict[str, Any]:
    """Get or set context values in the current state.

    Without arguments, returns all context.
    With key+value, sets a context entry.
    With just key, gets a specific context entry.
    """
    from whitemagic.core.memory.current_state import get_state_tracker

    tracker = get_state_tracker()
    key = kwargs.get("key")
    value = kwargs.get("value")

    if key and value is not None:
        tracker.set_context(key, value)
        return {"status": "success", "key": key, "value": value}
    elif key:
        val = tracker.get_context(key)
        return {"status": "success", "key": key, "value": val}
    else:
        state = tracker.get_state()
        return {"status": "success", "context": state.get("context", {})}
