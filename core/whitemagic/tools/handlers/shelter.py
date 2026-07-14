"""Shelter (Sovereign Sandbox) tool handlers (v15.2)."""

from typing import Any


def handle_shelter_create(**kwargs: Any) -> dict[str, Any]:
    """Create a new isolated execution shelter."""
    from whitemagic.shelter import get_shelter_manager

    mgr = get_shelter_manager()
    return mgr.create(
        name=kwargs.get("name", "default"),
        tier=kwargs.get("tier", "auto"),
        capabilities=kwargs.get("capabilities"),
        limits=kwargs.get("limits"),
        ephemeral=kwargs.get("ephemeral", True),
        dharma_profile=kwargs.get("dharma_profile", "default"),
        template=kwargs.get("template", ""),
    )


def handle_shelter_execute(**kwargs: Any) -> dict[str, Any]:
    """Execute a payload inside a shelter."""
    from whitemagic.shelter import get_shelter_manager

    mgr = get_shelter_manager()
    name = kwargs.get("name", "default")
    payload = kwargs.get("payload")
    if payload is not None and not isinstance(payload, dict):
        payload = {"type": "python", "code": str(payload)}
    # Auto-create shelter if it doesn't exist
    try:
        result = mgr.execute(name=name, payload=payload)
        if isinstance(result, dict) and "not found" in str(result.get("reason") or result.get("error") or "").lower():
            mgr.create(name=name, tier="auto", ephemeral=True)
            result = mgr.execute(name=name, payload=payload)
        return result
    except Exception as e:
        if "not found" in str(e).lower():
            mgr.create(name=name, tier="auto", ephemeral=True)
            return mgr.execute(name=name, payload=payload)
        raise


def handle_shelter_inspect(**kwargs: Any) -> dict[str, Any]:
    """Inspect output or artifacts from a shelter."""
    from whitemagic.shelter import get_shelter_manager

    mgr = get_shelter_manager()
    name = kwargs.get("name", "default")
    # Auto-create shelter if it doesn't exist
    try:
        return mgr.inspect(name=name, artifact=kwargs.get("artifact", ""))
    except Exception as e:
        if "not found" in str(e).lower():
            mgr.create(name=name, tier="auto", ephemeral=True)
            return mgr.inspect(name=name, artifact=kwargs.get("artifact", ""))
        raise


def handle_shelter_destroy(**kwargs: Any) -> dict[str, Any]:
    """Destroy a shelter and clean up resources."""
    from whitemagic.shelter import get_shelter_manager

    mgr = get_shelter_manager()
    return mgr.destroy(name=kwargs.get("name", "default"))


def handle_shelter_status(**kwargs: Any) -> dict[str, Any]:
    """List active shelters and system capabilities."""
    from whitemagic.shelter import get_shelter_manager

    mgr = get_shelter_manager()
    return mgr.status()


def handle_shelter_policy(**kwargs: Any) -> dict[str, Any]:
    """Get or set capability policy for a shelter."""
    from whitemagic.shelter import get_shelter_manager

    mgr = get_shelter_manager()
    name = kwargs.get("name", "default")
    # Auto-create shelter if it doesn't exist
    try:
        return mgr.policy(name=name, capabilities=kwargs.get("capabilities"))
    except Exception as e:
        if "not found" in str(e).lower():
            mgr.create(name=name, tier="auto", ephemeral=True)
            return mgr.policy(name=name, capabilities=kwargs.get("capabilities"))
        raise


# ── MandalaOS Phase B: mandala.* MCP tools ──────────────────────────────


def handle_mandala_create(**kwargs: Any) -> dict[str, Any]:
    """Create a new mandala compartment from a template or explicit config.

    Args:
        name: Unique mandala name.
        template: Template name (research, sandbox, production, secure).
        tier: Override isolation tier (auto, thread, namespace, container, wasm).
        dharma_profile: Override Dharma profile from template.
        capabilities: Override capabilities from template.
        limits: Override resource limits from template.
        ephemeral: Auto-destroy on completion (default True).
    """
    from whitemagic.shelter import get_shelter_manager
    from whitemagic.shelter.manager import SHELTER_TEMPLATES

    mgr = get_shelter_manager()
    template_name = kwargs.get("template", "")
    name = kwargs.get("name", "default")

    if template_name and template_name in SHELTER_TEMPLATES:
        tmpl = SHELTER_TEMPLATES[template_name]
        return mgr.create(
            name=name,
            tier=kwargs.get("tier", "auto"),
            capabilities=kwargs.get("capabilities", tmpl["capabilities"]),
            limits=kwargs.get("limits", tmpl["limits"]),
            ephemeral=kwargs.get("ephemeral", True),
            dharma_profile=kwargs.get("dharma_profile", tmpl["dharma_profile"]),
            template=template_name,
        )

    return mgr.create(
        name=name,
        tier=kwargs.get("tier", "auto"),
        capabilities=kwargs.get("capabilities"),
        limits=kwargs.get("limits"),
        ephemeral=kwargs.get("ephemeral", True),
        dharma_profile=kwargs.get("dharma_profile", "default"),
        template=template_name,
    )


def handle_mandala_status(**kwargs: Any) -> dict[str, Any]:
    """List active mandala compartments and available templates."""
    from whitemagic.shelter import get_shelter_manager
    from whitemagic.shelter.manager import SHELTER_TEMPLATES

    mgr = get_shelter_manager()
    base = mgr.status()
    base["templates"] = {
        name: {"description": t["description"], "dharma_profile": t["dharma_profile"]}
        for name, t in SHELTER_TEMPLATES.items()
    }
    return base


def handle_mandala_destroy(**kwargs: Any) -> dict[str, Any]:
    """Destroy a mandala compartment and clean up resources."""
    from whitemagic.shelter import get_shelter_manager

    mgr = get_shelter_manager()
    return mgr.destroy(name=kwargs.get("name", "default"))


def handle_mandala_templates(**kwargs: Any) -> dict[str, Any]:
    """List available mandala templates with their capabilities and limits."""
    from whitemagic.shelter.manager import SHELTER_TEMPLATES

    return {
        "status": "success",
        "templates": {
            name: {
                "capabilities": t["capabilities"],
                "limits": t["limits"],
                "dharma_profile": t["dharma_profile"],
                "description": t["description"],
            }
            for name, t in SHELTER_TEMPLATES.items()
        },
    }
