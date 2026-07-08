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
    )


def handle_shelter_execute(**kwargs: Any) -> dict[str, Any]:
    """Execute a payload inside a shelter."""
    from whitemagic.shelter import get_shelter_manager

    mgr = get_shelter_manager()
    name = kwargs.get("name", "default")
    # Auto-create shelter if it doesn't exist
    try:
        return mgr.execute(name=name, payload=kwargs.get("payload"))
    except Exception as e:
        if "not found" in str(e).lower():
            mgr.create(name=name, tier="auto", ephemeral=True)
            return mgr.execute(name=name, payload=kwargs.get("payload"))
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
