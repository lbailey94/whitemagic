"""dispatch_agents.py — Agent coordination, swarm, session, and mesh tools.

Domain slice imported by dispatch_table.py.
"""
from collections.abc import Callable
from typing import Any

from whitemagic.tools.dispatch_core import LazyHandler, LazyHandlerAbs

DISPATCH_AGENTS: dict[str, Callable[..., dict[str, Any]]] = {
    # --- Agent Capabilities ---
    "get_agent_capabilities": LazyHandler("misc", "handle_get_agent_capabilities"),

    # --- Session ---
    "session_bootstrap": LazyHandler("session", "handle_session_bootstrap"),
    "session_status": LazyHandler("session", "handle_session_status"),
    "session_handoff": LazyHandler("session", "handle_session_handoff"),
    "session_handoff_summary": LazyHandler("session", "handle_session_handoff_summary"),
    "create_session": LazyHandler("session", "handle_create_session"),
    "checkpoint_session": LazyHandler("session", "handle_checkpoint_session"),
    "resume_session": LazyHandler("session", "handle_resume_session"),

    # --- Cross-Device Session Handoff ---
    "session.handoff": LazyHandler("session", "handle_session_handoff"),
    "session.handoff_transfer": LazyHandler("session", "handle_session_handoff_transfer"),
    "session.accept_handoff": LazyHandler("session", "handle_session_accept_handoff"),
    "session.list_handoffs": LazyHandler("session", "handle_session_list_handoffs"),

    # --- Agent Swarm Protocols ---
    "swarm.decompose": LazyHandler("swarm", "handle_swarm_decompose"),
    "swarm.route": LazyHandler("swarm", "handle_swarm_route"),
    "swarm.complete": LazyHandler("swarm", "handle_swarm_complete"),
    "swarm.vote": LazyHandler("swarm", "handle_swarm_vote"),
    "swarm.resolve": LazyHandler("swarm", "handle_swarm_resolve"),
    "swarm.plan": LazyHandler("swarm", "handle_swarm_plan"),
    "swarm.status": LazyHandler("swarm", "handle_swarm_status"),

    # --- Agent Registry ---
    "agent.register": LazyHandler("agent_registry", "handle_agent_register"),
    "agent.heartbeat": LazyHandler("agent_registry", "handle_agent_heartbeat"),
    "agent.list": LazyHandler("agent_registry", "handle_agent_list"),
    "agent.capabilities": LazyHandler("agent_registry", "handle_agent_capabilities"),
    "agent.deregister": LazyHandler("agent_registry", "handle_agent_deregister"),

    # --- Sangha (Coordination) ---
    "sangha_chat_send": LazyHandler("sangha", "handle_sangha_chat_send"),
    "sangha_chat_read": LazyHandler("sangha", "handle_sangha_chat_read"),
    "sangha_lock": LazyHandler("sangha", "handle_sangha_lock"),
    "sangha_lock_acquire": LazyHandler("sangha", "handle_sangha_lock_acquire"),
    "sangha_lock_release": LazyHandler("sangha", "handle_sangha_lock_release"),
    "sangha_lock_list": LazyHandler("sangha", "handle_sangha_lock_list"),

    # --- Task Distribution ---
    "task.distribute": LazyHandler("task_dist", "handle_task_distribute"),
    "task.status": LazyHandler("task_dist", "handle_task_status"),
    "task.list": LazyHandler("task_dist", "handle_task_list"),
    "task.complete": LazyHandler("task_dist", "handle_task_complete"),
    "task.route_smart": LazyHandler("task_dist", "handle_task_route_smart"),

    # --- Voting / Ensemble ---
    "vote.create": LazyHandler("voting", "handle_vote_create"),
    "vote.cast": LazyHandler("voting", "handle_vote_cast"),
    "vote.analyze": LazyHandler("voting", "handle_vote_analyze"),
    "vote.list": LazyHandler("voting", "handle_vote_list"),
    "vote.record_outcome": LazyHandler("voting", "handle_vote_record_outcome"),
    "ensemble": LazyHandler("ensemble", "handle_ensemble"),
    "ensemble.query": LazyHandler("ensemble", "handle_ensemble_query"),
    "ensemble.status": LazyHandler("ensemble", "handle_ensemble_status"),
    "ensemble.history": LazyHandler("ensemble", "handle_ensemble_history"),

    # --- Mesh & Broker ---
    "mesh.connect": LazyHandler("agent_ergonomics", "handle_mesh_connect"),
    "mesh.status": LazyHandler("agent_ergonomics", "handle_mesh_status"),
    "mesh.broadcast": LazyHandler("agent_ergonomics", "handle_mesh_broadcast"),
    "broker.publish": LazyHandler("broker", "handle_broker_publish"),
    "broker.history": LazyHandler("broker", "handle_broker_history"),
    "broker.status": LazyHandler("broker", "handle_broker_status"),

    # --- Pipelines ---
    "pipeline": LazyHandler("pipeline", "handle_pipeline"),
    "pipeline.create": LazyHandler("pipeline", "handle_pipeline_create"),
    "pipeline.status": LazyHandler("pipeline", "handle_pipeline_status"),
    "pipeline.list": LazyHandler("pipeline", "handle_pipeline_list"),

    # --- Starter Packs & Agent Ergonomics ---
    "starter_packs": LazyHandler("agent_ergonomics", "handle_starter_packs"),
    "starter_packs.list": LazyHandler("agent_ergonomics", "handle_starter_packs_list"),
    "starter_packs.get": LazyHandler("agent_ergonomics", "handle_starter_packs_get"),
    "starter_packs.suggest": LazyHandler("agent_ergonomics", "handle_starter_packs_suggest"),
    "rate_limiter.stats": LazyHandler("agent_ergonomics", "handle_rate_limiter_stats"),
    "audit.export": LazyHandler("agent_ergonomics", "handle_audit_export"),
    "explain_this": LazyHandler("agent_ergonomics", "handle_explain_this"),
    "agent.trust": LazyHandler("agent_ergonomics", "handle_agent_trust"),

    # --- Gana Sabha (Council Protocol) ---
    "sabha.convene": LazyHandlerAbs("whitemagic.tools.gana_sabha", "handle_sabha_convene"),
    "sabha.status": LazyHandlerAbs("whitemagic.tools.gana_sabha", "handle_sabha_status"),

    # --- Marketplace ---
    "marketplace.publish": LazyHandler("marketplace", "handle_marketplace_publish"),
    "marketplace.discover": LazyHandler("marketplace", "handle_marketplace_discover"),
    "marketplace.negotiate": LazyHandler("marketplace", "handle_marketplace_negotiate"),
    "marketplace.complete": LazyHandler("marketplace", "handle_marketplace_complete"),
    "marketplace.my_listings": LazyHandler("marketplace", "handle_marketplace_my_listings"),
    "marketplace.remove": LazyHandler("marketplace", "handle_marketplace_remove"),
    "marketplace.status": LazyHandler("marketplace", "handle_marketplace_status"),

    # --- God-Kit / CodeGenome ---
    "codegenome.generate": LazyHandler("codegenome", "handle_codegenome_generate"),
    "codegenome.list": LazyHandler("codegenome", "handle_codegenome_list"),
    "codegenome.fork": LazyHandler("codegenome", "handle_codegenome_fork"),
    "codegenome.status": LazyHandler("codegenome", "handle_codegenome_status"),
}
