"""MCP handlers for the CodeGenome / God-Kit system."""

from typing import Any


def handle_codegenome_generate(**kwargs: Any) -> dict[str, Any]:
    """Generate code from a natural language prompt using the God-Kit.

    Args:
        prompt: Natural language code request (e.g., "I need a FastAPI endpoint for items")
        num_clones: Optional override for clones per tier
        tier: Optional force a tier (xianfeng, wei_wuzu, huben)

    Returns:
        Dict with generated code, metadata, and tier progression
    """
    from whitemagic.codegenome.vault import get_geneseed_vault
    from whitemagic.edge.thought_clones_async import god_kit_generate

    prompt = kwargs.get("prompt", "")
    if not prompt:
        return {"status": "error", "error_code": "prompt_required", "message": "prompt is required"}

    # If tier is specified, use direct vault render; otherwise use full God-Kit pipeline
    forced_tier = kwargs.get("tier")
    if forced_tier:
        vault = get_geneseed_vault()
        result = vault.vibe_render(prompt)
        if result.get("status") == "success":
            # Re-render with forced tier
            from whitemagic.codegenome.engine import get_codegenome_engine
            engine = get_codegenome_engine()
            template = engine.get_template(result["template_name"])
            if template:
                code = template.render(tier=forced_tier, **result.get("variables", {}))
                return {
                    "status": "success",
                    "code": code,
                    "template_name": result["template_name"],
                    "tier": forced_tier,
                    "variables": result.get("variables", {}),
                    "mode": "direct_tier_override",
                }
        return {"status": "error", "error_code": "render_failed", "details": result}

    # Full three-tier God-Kit pipeline
    import asyncio
    try:
        result = asyncio.run(god_kit_generate(prompt, num_clones=kwargs.get("num_clones")))
        return result
    except Exception as e:
        return {"status": "error", "error_code": "generation_failed", "message": str(e)}


def handle_codegenome_list(**kwargs: Any) -> dict[str, Any]:
    """List available code templates, optionally filtered by tag.

    Args:
        tag: Optional tag filter (e.g., "fastapi", "testing", "model")

    Returns:
        List of template metadata dicts
    """
    from whitemagic.codegenome.vault import get_geneseed_vault

    vault = get_geneseed_vault()
    tag = kwargs.get("tag")
    templates = vault.list_templates(tag=tag)
    return {"status": "success", "templates": templates, "count": len(templates)}


def handle_codegenome_fork(**kwargs: Any) -> dict[str, Any]:
    """Fork an existing template into a new one.

    Args:
        parent: Name of the parent template
        name: Name for the new forked template
        body_delta: Optional body override for the child

    Returns:
        Dict with forked template metadata
    """
    from whitemagic.codegenome.vault import get_geneseed_vault

    parent = kwargs.get("parent", "")
    name = kwargs.get("name", "")
    if not parent or not name:
        return {"status": "error", "error_code": "missing_params", "message": "parent and name are required"}

    vault = get_geneseed_vault()
    result = vault.fork(parent, name, body_delta=kwargs.get("body_delta", ""))
    return result


def handle_codegenome_status(**kwargs: Any) -> dict[str, Any]:
    """Get CodeGenome / God-Kit system status."""
    from whitemagic.codegenome.vault import get_geneseed_vault

    vault = get_geneseed_vault()
    return {"status": "success", **vault.status()}
