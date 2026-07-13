"""dispatch_agents.py — Agent coordination, swarm, session, and mesh tools.

Domain slice imported by dispatch_table.py.
"""

from collections.abc import Callable
from typing import Any

from whitemagic.tools.dispatch_core import LazyHandler, LazyHandlerAbs

DISPATCH_AGENTS: dict[str, Callable[..., dict[str, Any]]] = {
    "get_agent_capabilities": LazyHandler("misc", "handle_get_agent_capabilities"),
    "session_bootstrap": LazyHandler("session", "handle_session_bootstrap"),
    "session_status": LazyHandler("session", "handle_session_status"),
    "session_handoff": LazyHandler("session", "handle_session_handoff"),
    "session_handoff_summary": LazyHandler("session", "handle_session_handoff_summary"),
    "create_session": LazyHandler("session", "handle_create_session"),
    "checkpoint_session": LazyHandler("session", "handle_checkpoint_session"),
    "resume_session": LazyHandler("session", "handle_resume_session"),
    "session.handoff": LazyHandler("session", "handle_session_handoff"),
    "session.handoff_transfer": LazyHandler(
        "session", "handle_session_handoff_transfer"
    ),
    "session.accept_handoff": LazyHandler("session", "handle_session_accept_handoff"),
    "session.list_handoffs": LazyHandler("session", "handle_session_list_handoffs"),
    # ── Session Memory — Chronological conversation recording & recall ──
    "session.record": LazyHandler("session", "handle_session_record"),
    "session.recall": LazyHandler("session", "handle_session_recall"),
    "session.replay": LazyHandler("session", "handle_session_replay"),
    "session.search": LazyHandler("session", "handle_session_search"),
    "session.memory_stats": LazyHandler("session", "handle_session_memory_stats"),
    "session.backfill": LazyHandler("session", "handle_session_backfill"),
    "session.continuity": LazyHandler("session", "handle_session_continuity"),
    "session.consolidate": LazyHandler("session", "handle_session_consolidate"),
    # ── Current State — Live work context for AI agents ──
    "state.current": LazyHandler("state_tools", "handle_state_current"),
    "state.update": LazyHandler("state_tools", "handle_state_update"),
    "state.context": LazyHandler("state_tools", "handle_state_context"),
    # ── Swarm ──
    "swarm.decompose": LazyHandler("swarm", "handle_swarm_decompose"),
    "swarm.route": LazyHandler("swarm", "handle_swarm_route"),
    "swarm.complete": LazyHandler("swarm", "handle_swarm_complete"),
    "swarm.vote": LazyHandler("swarm", "handle_swarm_vote"),
    "swarm.resolve": LazyHandler("swarm", "handle_swarm_resolve"),
    "swarm.plan": LazyHandler("swarm", "handle_swarm_plan"),
    "swarm.status": LazyHandler("swarm", "handle_swarm_status"),
    "agent.register": LazyHandler("agent_registry", "handle_agent_register"),
    "agent.heartbeat": LazyHandler("agent_registry", "handle_agent_heartbeat"),
    "agent.list": LazyHandler("agent_registry", "handle_agent_list"),
    "agent.capabilities": LazyHandler("agent_registry", "handle_agent_capabilities"),
    "agent.deregister": LazyHandler("agent_registry", "handle_agent_deregister"),
    "sangha_chat_send": LazyHandler("sangha", "handle_sangha_chat_send"),
    "sangha_chat_read": LazyHandler("sangha", "handle_sangha_chat_read"),
    "sangha_lock": LazyHandler("sangha", "handle_sangha_lock"),
    "sangha_lock_acquire": LazyHandler("sangha", "handle_sangha_lock_acquire"),
    "sangha_lock_release": LazyHandler("sangha", "handle_sangha_lock_release"),
    "sangha_lock_list": LazyHandler("sangha", "handle_sangha_lock_list"),
    "task.distribute": LazyHandler("task_dist", "handle_task_distribute"),
    "task.status": LazyHandler("task_dist", "handle_task_status"),
    "task.list": LazyHandler("task_dist", "handle_task_list"),
    "task.complete": LazyHandler("task_dist", "handle_task_complete"),
    "task.route_smart": LazyHandler("task_dist", "handle_task_route_smart"),
    "vote.create": LazyHandler("voting", "handle_vote_create"),
    "vote.cast": LazyHandler("voting", "handle_vote_cast"),
    "vote.analyze": LazyHandler("voting", "handle_vote_analyze"),
    "vote.list": LazyHandler("voting", "handle_vote_list"),
    "vote.record_outcome": LazyHandler("voting", "handle_vote_record_outcome"),
    "ensemble": LazyHandler("ensemble", "handle_ensemble"),
    "ensemble.query": LazyHandler("ensemble", "handle_ensemble_query"),
    "ensemble.status": LazyHandler("ensemble", "handle_ensemble_status"),
    "ensemble.history": LazyHandler("ensemble", "handle_ensemble_history"),
    "mesh.connect": LazyHandler("agent_ergonomics", "handle_mesh_connect"),
    "mesh.status": LazyHandler("agent_ergonomics", "handle_mesh_status"),
    "mesh.broadcast": LazyHandler("agent_ergonomics", "handle_mesh_broadcast"),
    "broker.publish": LazyHandler("broker", "handle_broker_publish"),
    "broker.history": LazyHandler("broker", "handle_broker_history"),
    "broker.status": LazyHandler("broker", "handle_broker_status"),
    "pipeline": LazyHandler("pipeline", "handle_pipeline"),
    "pipeline.create": LazyHandler("pipeline", "handle_pipeline_create"),
    "pipeline.status": LazyHandler("pipeline", "handle_pipeline_status"),
    "pipeline.list": LazyHandler("pipeline", "handle_pipeline_list"),
    "starter_packs": LazyHandler("agent_ergonomics", "handle_starter_packs"),
    "starter_packs.list": LazyHandler("agent_ergonomics", "handle_starter_packs_list"),
    "starter_packs.get": LazyHandler("agent_ergonomics", "handle_starter_packs_get"),
    "starter_packs.suggest": LazyHandler(
        "agent_ergonomics", "handle_starter_packs_suggest"
    ),
    "rate_limiter.stats": LazyHandler("agent_ergonomics", "handle_rate_limiter_stats"),
    "audit.export": LazyHandler("agent_ergonomics", "handle_audit_export"),
    "explain_this": LazyHandler("agent_ergonomics", "handle_explain_this"),
    "agent.trust": LazyHandler("agent_ergonomics", "handle_agent_trust"),
    "sabha.convene": LazyHandlerAbs(
        "whitemagic.tools.gana_sabha", "handle_sabha_convene"
    ),
    "sabha.status": LazyHandlerAbs(
        "whitemagic.tools.gana_sabha", "handle_sabha_status"
    ),
    "marketplace.publish": LazyHandler("marketplace", "handle_marketplace_publish"),
    "marketplace.discover": LazyHandler("marketplace", "handle_marketplace_discover"),
    "marketplace.negotiate": LazyHandler("marketplace", "handle_marketplace_negotiate"),
    "marketplace.complete": LazyHandler("marketplace", "handle_marketplace_complete"),
    "marketplace.my_listings": LazyHandler(
        "marketplace", "handle_marketplace_my_listings"
    ),
    "marketplace.remove": LazyHandler("marketplace", "handle_marketplace_remove"),
    "marketplace.status": LazyHandler("marketplace", "handle_marketplace_status"),
    "codegenome.generate": LazyHandler("codegenome", "handle_codegenome_generate"),
    "codegenome.list": LazyHandler("codegenome", "handle_codegenome_list"),
    "codegenome.fork": LazyHandler("codegenome", "handle_codegenome_fork"),
    "codegenome.status": LazyHandler("codegenome", "handle_codegenome_status"),
    # ── Research DAG ──
    "research.dag.submit": LazyHandler("research", "handle_research_dag_submit"),
    "research.dag.result": LazyHandler("research", "handle_research_dag_result"),
    "research.dag.critique": LazyHandler("research", "handle_research_dag_critique"),
    "research.dag.lineage": LazyHandler("research", "handle_research_dag_lineage"),
    "research.dag.breakthroughs": LazyHandler("research", "handle_research_dag_breakthroughs"),
    "research.dag.stats": LazyHandler("research", "handle_research_dag_stats"),
    "research.dag.leaderboard": LazyHandler("research", "handle_research_dag_leaderboard"),
    "research.dag.experiments": LazyHandler("research", "handle_research_dag_experiments"),
    # ── Autoswarm ──
    "autoswarm.campaign": LazyHandler("research", "handle_autoswarm_campaign"),
    "autoswarm.status": LazyHandler("research", "handle_autoswarm_status"),
    "autoswarm.start": LazyHandler("research", "handle_autoswarm_start"),
    "autoswarm.stop": LazyHandler("research", "handle_autoswarm_stop"),
    # ── Warps ──
    "warp.load": LazyHandler("research", "handle_warp_load"),
    "warp.list": LazyHandler("research", "handle_warp_list"),
    "warp.create": LazyHandler("research", "handle_warp_create"),
    "warp.delete": LazyHandler("research", "handle_warp_delete"),
    "warp.status": LazyHandler("research", "handle_warp_status"),
    # ── Mesh Experiment Sync ──
    "mesh.experiment.share": LazyHandler("research", "handle_mesh_experiment_share"),
    "mesh.experiment.receive": LazyHandler("research", "handle_mesh_experiment_receive"),
    "mesh.experiment.status": LazyHandler("research", "handle_mesh_experiment_status"),
    "mesh.experiment.peers": LazyHandler("research", "handle_mesh_experiment_peers"),
    "mesh.experiment.discover": LazyHandler("research", "handle_mesh_experiment_discover"),
    # ── Research DAG Synthesis ──
    "research.dag.synthesize": LazyHandler("research", "handle_research_dag_synthesize"),
    # ── CRDT Leaderboard ──
    "leaderboard.submit": LazyHandler("research", "handle_leaderboard_submit"),
    "leaderboard.top": LazyHandler("research", "handle_leaderboard_top"),
    "leaderboard.status": LazyHandler("research", "handle_leaderboard_status"),
    "leaderboard.merge": LazyHandler("research", "handle_leaderboard_merge"),
    # ── Pulse Verification ──
    "pulse.verify": LazyHandler("research", "handle_pulse_verify"),
    "pulse.verify.status": LazyHandler("research", "handle_pulse_status"),
    # ── Critique Protocol ──
    "critique.submit": LazyHandler("research", "handle_critique_submit"),
    "critique.auto": LazyHandler("research", "handle_critique_auto"),
    "critique.status": LazyHandler("research", "handle_critique_status"),
    # ── Durable Archive ──
    "archive.run": LazyHandler("research", "handle_archive_run"),
    "archive.status": LazyHandler("research", "handle_archive_status"),
    # ── DiLoCo Distributed Training ──
    "dilo_co.init": LazyHandler("research", "handle_dilo_co_init"),
    "dilo_co.register_worker": LazyHandler("research", "handle_dilo_co_register_worker"),
    "dilo_co.submit_gradient": LazyHandler("research", "handle_dilo_co_submit_gradient"),
    "dilo_co.sync": LazyHandler("research", "handle_dilo_co_sync"),
    "dilo_co.status": LazyHandler("research", "handle_dilo_co_status"),
    # ── Warp Marketplace ──
    "warp.market.publish": LazyHandler("research", "handle_warp_market_publish"),
    "warp.market.discover": LazyHandler("research", "handle_warp_market_discover"),
    "warp.market.download": LazyHandler("research", "handle_warp_market_download"),
    "warp.market.status": LazyHandler("research", "handle_warp_market_status"),
    "warp.market.broadcast": LazyHandler("research", "handle_warp_market_broadcast"),
    # ── Mesh Inference Router ──
    "mesh.route": LazyHandler("research", "handle_mesh_route"),
    "mesh.route.register": LazyHandler("research", "handle_mesh_route_register"),
    "mesh.route.nodes": LazyHandler("research", "handle_mesh_route_nodes"),
    "mesh.route.status": LazyHandler("research", "handle_mesh_route_status"),
    "mesh.route.strategy": LazyHandler("research", "handle_mesh_route_strategy"),
}
