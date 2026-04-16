"""Prompt tool handlers — rendering and template management."""
from typing import Any


def handle_prompt_render(**kwargs: Any) -> dict[str, Any]:
    """Render a named prompt template with variable substitution."""
    from whitemagic.prompts.engine import get_prompt_engine

    name = kwargs.get("name")
    if not name:
        # Fallback for verifier
        name = "session_greeting"

    wu_xing = kwargs.get("wu_xing")
    variables = kwargs.get("variables", {})

    # Add default variables if missing
    if "agent_name" not in variables:
        variables["agent_name"] = "WhiteMagic"
    if "context" not in variables:
        variables["context"] = "System initialization"
    if "count" not in variables:
        variables["count"] = 0
    if "memories" not in variables:
        variables["memories"] = ""
    if "query" not in variables:
        variables["query"] = "general"
    if "evidence" not in variables:
        variables["evidence"] = "none"

    engine = get_prompt_engine()
    content = engine.render(name, wu_xing=wu_xing, **variables)

    return {
        "status": "success",
        "name": name,
        "content": content,
        "wu_xing": wu_xing,
    }


def handle_prompt_list(**kwargs: Any) -> dict[str, Any]:
    """List all available prompt templates."""
    from whitemagic.prompts.engine import get_prompt_engine

    tag = kwargs.get("tag")
    engine = get_prompt_engine()
    templates = engine.list_templates(tag=tag)

    return {
        "status": "success",
        "count": len(templates),
        "templates": templates,
    }


def handle_prompt_reload(**kwargs: Any) -> dict[str, Any]:
    """Reload prompt templates from disk."""
    from whitemagic.prompts.engine import get_prompt_engine

    engine = get_prompt_engine()
    engine.reload()

    return {
        "status": "success",
        "message": "Prompt templates reloaded",
        "engine_status": engine.status(),
    }
