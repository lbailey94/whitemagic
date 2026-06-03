"""MCP handlers for Agent Swarm Protocols."""

from typing import Any, cast


def handle_swarm_decompose(**kwargs: Any) -> dict[str, Any]:
    """Decompose a goal into subtasks with capability requirements."""
    from whitemagic.agents.swarm import get_swarm
    goal = kwargs.get("goal", "")
    if not goal:
        return {"status": "error", "error": "goal is required"}
    hints = kwargs.get("hints", None)
    swarm = get_swarm()
    plan = swarm.decompose(goal, hints=hints)
    return {"status": "success", **plan.to_dict()}


def handle_swarm_route(**kwargs: Any) -> dict[str, Any]:
    """Route subtasks to agents by capability matching."""
    from whitemagic.agents.swarm import get_swarm
    plan_id = kwargs.get("plan_id", "")
    if not plan_id:
        return {"status": "error", "error": "plan_id is required"}
    return cast("dict[str, Any]", get_swarm().route(plan_id))


def handle_swarm_complete(**kwargs: Any) -> dict[str, Any]:
    """Mark a subtask as completed or failed."""
    from whitemagic.agents.swarm import get_swarm
    plan_id = kwargs.get("plan_id", "")
    task_id = kwargs.get("task_id", "")
    if not plan_id or not task_id:
        return {"status": "error", "error": "plan_id and task_id required"}
    result = kwargs.get("result", None)
    success = kwargs.get("success", True)
    return cast("dict[str, Any]", get_swarm().complete_task(plan_id, task_id, result=result, success=success))


def handle_swarm_vote(**kwargs: Any) -> dict[str, Any]:
    """Record a vote from an agent on a consensus topic."""
    from whitemagic.agents.swarm import get_swarm
    topic = kwargs.get("topic_id", "")
    agent = kwargs.get("agent_id", "")
    value = kwargs.get("value", "")
    if not topic or not agent:
        return {"status": "error", "error": "topic_id and agent_id required"}
    confidence = float(kwargs.get("confidence", 1.0))
    return cast("dict[str, Any]", get_swarm().vote(topic, agent, value, confidence=confidence))


def handle_swarm_resolve(**kwargs: Any) -> dict[str, Any]:
    """Resolve a consensus vote."""
    from whitemagic.agents.swarm import ConsensusStrategy, get_swarm
    topic = kwargs.get("topic_id", "")
    if not topic:
        return {"status": "error", "error": "topic_id is required"}
    strategy = kwargs.get("strategy", "majority")
    try:
        strat = ConsensusStrategy(strategy)
    except ValueError:
        strat = ConsensusStrategy.MAJORITY
    return cast("dict[str, Any]", get_swarm().resolve(topic, strategy=strat))


def handle_swarm_assign_house(**kwargs: Any) -> dict[str, Any]:
    """Assign an agent to a tricameral house."""
    from whitemagic.agents.swarm import get_swarm
    agent_id = kwargs.get("agent_id", "")
    house = kwargs.get("house", "")
    if not agent_id or not house:
        return {"status": "error", "error": "agent_id and house are required"}
    return cast("dict[str, Any]", get_swarm().assign_house(agent_id, house))


def handle_swarm_prune(**kwargs: Any) -> dict[str, Any]:
    """Prune stale plans and votes (Proof-of-Utility)."""
    from whitemagic.agents.swarm import get_swarm
    max_age = kwargs.get("max_age_seconds")
    if max_age is not None:
        max_age = float(max_age)
    return cast("dict[str, Any]", get_swarm().prune_stale(max_age_seconds=max_age))


def handle_swarm_plan(**kwargs: Any) -> dict[str, Any]:
    """Get a specific swarm plan by ID."""
    from whitemagic.agents.swarm import get_swarm
    plan_id = kwargs.get("plan_id", "")
    if not plan_id:
        return {"status": "error", "error": "plan_id is required"}
    plan = get_swarm().get_plan(plan_id)
    if not plan:
        return {"status": "error", "error": "Plan not found"}
    return {"status": "success", **plan}


def handle_swarm_status(**kwargs: Any) -> dict[str, Any]:
    """Get swarm coordination status."""
    from whitemagic.agents.swarm import get_swarm
    return {"status": "success", **get_swarm().status()}
