#!/usr/bin/env python3
"""Exercise every registered WhiteMagic tool and record results.

Calls each tool in the dispatch table with safe default arguments,
records success/failure/duration, and stores results in the
ToolUsageTracker SQLite database.

Usage:
    python scripts/exercise_all_tools.py [--dry-run] [--limit N] [--verbose]
"""

from __future__ import annotations

import argparse
import gc
import json
import sys
import time
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "core"))

from whitemagic.tools.dispatch_table import DISPATCH_TABLE  # noqa: E402
from whitemagic.core.monitoring.tool_usage_tracker import (  # noqa: E402
    get_tool_usage_tracker,
)


# Safe default arguments for known tools that require parameters.
# Tools not in this dict get called with empty args.
SAFE_DEFAULTS: dict[str, dict] = {
    "search_memories": {"query": "test", "limit": 1},
    "create_memory": {"content": "test memory from exercise script", "title": "Exercise Test"},
    "recall": {"query": "test", "limit": 1},
    "remember": {"content": "test memory from exercise script"},
    "hybrid_recall": {"query": "test", "limit": 1},
    "list_memories": {"limit": 1},
    "batch_read_memories": {"filenames": []},
    "graph_walk": {"memory_id": "test", "depth": 1},
    "read_memory": {"memory_id": "test"},
    "vector.search": {"query": "test", "limit": 1},
    "gnosis": {"compact": True},
    "capabilities": {"include_tools": False, "include_schemas": False},
    "manifest": {},
    "health_report": {},
    "ship.check": {},
    "state.paths": {},
    "state.summary": {},
    "repo.summary": {},
    "get_telemetry_summary": {},
    "tool_usage_stats": {"action": "summary"},
    "rust_status": {},
    "tool.graph": {},
    "tool.graph_full": {},
    "list_ganas": {},
    "vitality": {},
    "discover": {},
    "harmony_vector": {},
    "check_boundaries": {"action": "list"},
    "evaluate_ethics": {"action": "list"},
    "get_dharma_guidance": {},
    "get_ethical_score": {"action": "list"},
    "cache.status": {},
    "cache.flush": {},
    "anomaly": {},
    "anomaly.check": {},
    "anomaly.status": {},
    "anomaly.history": {},
    "anti_loop_check": {},
    "coherence_boost": {},
    "cluster_stats": {},
    "activation.spread": {"memory_id": "test"},
    "activation.stats": {},
    "agent.list": {},
    "agent.capabilities": {"agent_id": "test"},
    "agent.heartbeat": {"agent_id": "test"},
    "broker.status": {},
    "broker.history": {"limit": 1},
    "community.status": {},
    "community.health": {},
    "cognitive.mode": {},
    "cognitive.hints": {},
    "cognitive.stats": {},
    "consciousness.status": {},
    "consciousness.coherence": {},
    "consciousness.calibration": {},
    "consciousness.depth": {},
    "consciousness.flow": {},
    "consciousness.stillness": {},
    "consciousness.smarana": {},
    "consciousness.reflect": {},
    "consciousness.narrative": {},
    "consciousness.time_dilation": {},
    "consciousness.token_economy": {},
    "consciousness.token_report": {},
    "consciousness.awaken": {},
    "citta.continuity": {},
    "citta.cycle": {},
    "citta.sensorium": {},
    "citta.stream_summary": {},
    "session.record": {},
    "session.recall": {"limit": 1},
    "session.replay": {"limit": 1},
    "session.search": {"query": "test"},
    "session.memory_stats": {},
    "session.backfill": {},
    "session.continuity": {},
    "session.consolidate": {},
    "checkpoint_session": {},
    "focus_session": {},
    "analyze_scratchpad": {},
    "context.pack": {},
    "context.status": {},
    "get_session_context": {},
    "art_of_war.wisdom": {},
    "art_of_war.chapter": {"chapter": 1},
    "art_of_war.terrain": {},
    "art_of_war.assess": {},
    "art_of_war.plan": {},
    "art_of_war.campaign": {},
    "cast_oracle": {"question": "test"},
    "grimoire_list": {},
    "grimoire_cast": {"spell": "test"},
    "bounty.list": {},
    "bounty.create": {"title": "test", "description": "test"},
    "codegenome.list": {},
    "codegenome.status": {},
    "codegenome.fork": {"parent": "test/test", "name": "test"},
    "codegenome.generate": {"prompt": "test"},
    "codegenome_validate": {},
    "archaeology": {"query": "test"},
    "archaeology_search": {"query": "test"},
    "archaeology_stats": {},
    "archaeology_report": {},
    "archaeology_recent_reads": {"limit": 1},
    "archaeology_daily_digest": {},
    "archaeology_find_changed": {},
    "archaeology_find_unread": {},
    "archaeology_have_read": {},
    "archaeology_mark_read": {"path": "test"},
    "archaeology_mark_written": {"path": "test"},
    "archaeology_process_wisdom": {},
    "archaeology_scan_directory": {"directory": "."},
    "bitnet_status": {},
    "bitnet_infer": {"prompt": "test"},
    "edge_add_rule": {"id": "test", "pattern": "test", "response": "test"},
    "edge_batch_infer": {"queries": ["test"]},
    "edge_infer": {"query": "test"},
    "selfmodel.forecast": {},
    "selfmodel.alerts": {},
    "capability.matrix": {},
    "capability.status": {"subsystem_id": "memory_unified"},
    "capability.suggest": {},
    "graph_topology": {},
    "surprise_stats": {},
    "telemetry": {},
    "get_metrics_summary": {},
    "get_yin_yang_balance": {},
    "green_score": {},
    "check": {},
    "health_report": {},
    "community.propagate": {},
    "bridge.synthesize": {},
    "consolidation.run": {"dry_run": True},
    "serendipity_surface": {},
    "dream.now": {},
    "dream.status": {},
    "dream.start": {},
    "dream.stop": {},
    "lifecycle.status": {},
    "entity.resolve": {"entity": "test"},
    "narrative.compress": {"content": "test"},
    "gratitude.stats": {},
    "whitemagic.tip": {},
    "vote.list": {},
    "vote.create": {"question": "test", "options": ["a", "b"]},
    "vote.analyze": {"session_id": "test"},
    "engagement.list": {},
    "engagement.status": {},
    "engagement.issue": {"issuer": "test", "scope": "test"},
    "engagement.revoke": {"issuer": "test", "token_id": "test"},
    "marketplace.publish": {},
    "marketplace.discover": {},
    "marketplace.negotiate": {"listing_id": "test"},
    "marketplace.complete": {"transaction_id": "test"},
    "galaxy.canonical_taxonomy": {},
    "galaxy.export_tutorial": {},
    "galaxy.backup": {},
    "galaxy.restore": {},
    "galaxy_dashboard": {},
    "galactic.dashboard": {},
    "galactic_dashboard": {},
    "dharma.reload": {},
    "dharma.rules": {},
    "forge.status": {},
    "forge.validate": {},
    "forge.reload": {},
    "governor.validate": {},
    "governor.set_goal": {},
    "governor.drift": {},
    "governor.budget": {},
    "governor.dharma": {},
    "prompt.list": {},
    "prompt.render": {"name": "test"},
    "prompt.reload": {},
    "karma.verify_chain": {},
    "export_memories": {"limit": 1},
    "audit.export": {},
    "galaxy.canonical_taxonomy": {},
    "galaxy.export_tutorial": {},
    "agent.register": {"agent_id": "test", "name": "test"},
    "agent.deregister": {"agent_id": "test"},
    "agent.trust": {"agent_id": "test"},
    "broker.publish": {"topic": "test", "message": "test"},
    "ganying_emit": {"signal": "test"},
    "model.list": {},
    "model.hash": {"model_path": "test"},
    "model.signing_status": {},
    "model.register": {},
    "llama_cpp.models": {},
    "llama_cpp.generate": {"prompt": "test"},
    "llama_cpp.chat": {"prompt": "test"},
    "llama_cpp.agent": {"prompt": "test"},
    "shelter.create": {},
    "shelter.execute": {},
    "shelter.inspect": {},
    "shelter.destroy": {},
    "sangha.chat": {"message": "test"},
    "hermit.assess": {},
    "hermit.check_access": {},
    "hermit.mediate": {},
    "security.monitor_status": {},
    "mcp.integrity": {},
    "sandbox.status": {},
    "art_of_war.assess": {},
    "art_of_war.campaign": {},
    "art_of_war.chapter": {"chapter": 1},
    "art_of_war.plan": {},
    "art_of_war.terrain": {},
    "art_of_war.wisdom": {},
    "kaizen.analyze": {},
    "kaizen.apply": {},
    "sabha.convene": {"topic": "test", "task": "test"},
    "sabha.status": {},
    "optimization": {},
    "ensemble.query": {"prompt": "test"},
    "ensemble.history": {},
    "ensemble.status": {},
    "bicameral_reasoning": {"topic": "test"},
    "homeostasis.check": {},
    "homeostasis.status": {},
    "maturity.assess": {},
    "starter_packs.get": {"name": "test"},
    "starter_packs.list": {},
    "starter_packs.suggest": {"context": "test"},
    "astro_shift": {"phase": "test"},
    "astro_status": {},
    "cognitive.set": {"mode": "balanced"},
    "swarm.decompose": {"goal": "test"},
    "swarm.route": {"plan_id": "test", "goal": "test"},
    "swarm.complete": {"plan_id": "test", "task_id": "test"},
    "swarm.vote": {"topic_id": "test", "agent_id": "test"},
    "swarm.plan": {"plan_id": "test", "goal": "test"},
    "swarm.resolve": {"topic_id": "test"},
    "swarm.status": {},
    "skill.export_all": {},
    "skill.import": {"path": "test"},
    "skill.invoke": {"name": "test"},
    "skill.list": {},
    "fool_guard.status": {},
    "fool_guard.dare_to_die": {},
    "fool_guard.ralph": {},
    "rate_limiter": {},
    "grimoire.spells": {},
    "grimoire.suggest": {},
    "grimoire.cast": {"spell": "test"},
    "grimoire.walkthrough": {},
    "association.mine": {},
    "association.mine_semantic": {},
    "causal.mine": {},
    "causal.stats": {},
    "pattern_search": {"query": "test"},
    "learning.patterns": {},
    "learning.suggest": {},
    "resonance.trace": {},
    "fast_read_memory": {"memory_id": "test"},
    "wm_read": {},
    "wm_read.status": {},
    "rerank": {},
    "rerank.status": {},
    "fragment.search": {"query": "test"},
    "fragment.status": {},
    "polyglot.search": {"query": "test", "texts": ["test"]},
    "activation.stats": {},
    "activation.spread": {"memory_id": "test"},
    "batch_read_memories": {"filenames": []},
    "memory_search": {"query": "test"},
    "search_query": {"query": "test"},
    "recall": {"query": "test"},
    "remember": {"content": "test"},
    "memory_delete": {"memory_id": "test"},
    "memory_update": {"memory_id": "test", "content": "test"},
    "import_memories": {},
    "memory_read": {"memory_id": "test"},
    "create_memory": {"content": "test", "title": "test"},
    "delete_memory": {"memory_id": "test"},
    "clone_memory": {"memory_id": "test"},
    "list_memories": {"limit": 1},
    "track_metric": {"metric": "test", "value": 1.0},
    "get_metrics_summary": {},
    "explain_this": {"tool_name": "test"},
    "drive.snapshot": {},
    "drive.event": {"event_type": "curiosity"},
    "selfmodel.forecast": {},
    "selfmodel.alerts": {},
    "capability.matrix": {},
    "capability.status": {"subsystem_id": "memory_unified"},
    "capability.suggest": {},
    "graph_topology": {},
    "surprise_stats": {},
    "karma.report": {},
    "karma.trace": {},
    "karma.anchor": {},
    "karma.verify": {},
    "dharma.rules": {},
    "anomaly": {},
    "anomaly.check": {},
    "anomaly.history": {},
    "anomaly.status": {},
    "otel": {},
    "otel.spans": {},
    "otel.metrics": {},
    "otel.status": {},
    "bitnet_infer": {"prompt": "test"},
    "bitnet_status": {},
    "edge_add_rule": {"id": "test", "pattern": "test", "response": "test"},
    "edge_batch_infer": {"queries": ["test"]},
    "vector.index": {"memory_id": "test", "content": "test"},
    "vector.status": {},
    "vector.search": {"query": "test"},
    "prompt.list": {},
    "prompt.render": {"name": "test"},
    "prompt.reload": {},
    "karma.verify_chain": {},
    # ── ValueError fixes: tools requiring specific params ──
    "alchemical_cycle": {"task": "test"},
    "analyze_scratchpad": {"scratchpad_id": "test"},
    "codegenome_validate": {"prompt": "test"},
    "deep_fetch": {"url": "https://example.com"},
    "garden_activate": {"garden": "beauty"},
    "parallel_reason": {"question": "test"},
    "rabbit_hole_research": {"topic": "test"},
    "research_repo": {"repo": "test/test"},
    "research_topic": {"topic": "test"},
    "research_url": {"url": "https://example.com"},
    "resume_session": {"session_id": "test"},
    "web_fetch": {"url": "https://example.com"},
    "web_fetch_enhanced": {"url": "https://example.com"},
    "web_search": {"query": "test"},
    "web_search_and_read": {"query": "test"},
    "web_search_batch": {"queries": ["test"]},
    "web_search_category": {"query": "test"},
    # ── invalid_params fixes: tools needing correct param formats ──
    "astro_shift": {"phase": "test"},
    "browser_click": {"selector": "button"},
    "browser_navigate": {"url": "https://example.com"},
    "browser_type": {"selector": "input", "text": "test"},
    "consult_wisdom_council": {"query": "test"},
    "galaxy.restore": {"galaxy": "default", "backup_path": "test_backup.tar.gz"},
    "image_analyze": {"image_path": "test.png"},
    "navigate_grimoire": {"query": "test"},
    "llama_cpp.agent": {"task": "test"},
    "llama_agent": {"task": "test"},
    "session.record": {"content": "test"},
    "verification.attest": {"request_id": "test", "attestation": "test"},
    "verification.request": {"target": "test"},
    "watcher_add": {"path": "test"},
    # ── not_found fixes: tools needing valid default IDs ──
    "agent.capabilities": {"agent_id": "test"},
    "agent.deregister": {"agent_id": "test"},
    "agent.heartbeat": {"agent_id": "test"},
    "watcher_recent_events": {"watcher_id": "test"},
    "watcher_remove": {"watcher_id": "test"},
    "watcher_start": {"watcher_id": "test"},
    "watcher_stop": {"watcher_id": "test"},
    # ── missing_params fixes ──
    "codegenome.fork": {"parent": "test/test", "name": "test"},
    "external.repo_compare": {"repo": "test/test", "local_module": "test"},
    "external.repo_scan": {"repo": "test/test"},
    "external.wiki_query": {"repo": "test/test", "question": "test"},
    "wiki.update": {"title": "test", "content": "test"},
    # ── single issue fixes ──
    "skill.invoke": {"name": "test"},
    "skill.import": {"path": "test"},
    # ── dream tools needing dream_id ──
    "dream.read": {"dream_id": "test"},
    "dream.promote": {"dream_id": "test"},
    "dream.expire": {"dream_id": "test"},
    # ── other tools needing params ──
    "corpus_callosum.debate": {"topic": "test"},
    "sangha_chat_send": {"content": "test message"},
    "sangha_lock_acquire": {"resource": "test"},
    "serendipity_mark_accessed": {"memory_id": "test"},
    # ── second batch: remaining UNKNOWN tools needing params ──
    "activation.spread": {"seed_ids": ["test"]},
    "bounty.create": {"task": "test", "amount": 1.0},
    "broker.history": {"channel": "test"},
    "broker.publish": {"channel": "test", "message": "test"},
    "capability.status": {"subsystem_id": "memory_unified"},
    "drive.event": {"event_type": "curiosity"},
    "edge_add_rule": {"id": "test", "pattern": "test", "response": "test"},
    "engagement.issue": {"issuer": "test", "scope": "test"},
    "engagement.revoke": {"issuer": "test", "token_id": "test"},
    "engagement.validate": {"issuer": "test", "token_id": "test"},
    "ensemble": {"prompt": "test"},
    "ensemble.query": {"prompt": "test"},
    "explain_this": {"tool_name": "test"},
    "fast_write.append": {"path": "test.txt", "content": "test"},
    "fast_write.batch": {"files": {"test.txt": "test"}},
    "fast_write.validate": {"path": "test.txt"},
    "fast_write.write": {"path": "test.txt", "content": "test"},
    "fragment.index": {"path": "."},
    "fragment.query": {"path": ".", "query": "test"},
    "fragment.search": {"path": ".", "query": "test"},
    "fragment.status": {"path": "."},
    "galaxy.create": {"name": "test"},
    "galaxy.delete": {"name": "test"},
    "galaxy.ingest": {"galaxy": "default", "source_path": "."},
    "galaxy.lineage": {"galaxy": "default", "memory_id": "test"},
    "galaxy.merge": {"source": "default", "target": "default"},
    "galaxy.migrate": {"galaxy": "default", "memory_id": "test", "target_galaxy": "default"},
    "galaxy.route": {"galaxy": "default", "subsystem": "memory"},
    "galaxy.share": {"galaxy": "default", "name": "test", "target_user_id": "test"},
    "galaxy.switch": {"name": "default"},
    "galaxy.sync": {"galaxy_a": "default", "galaxy_b": "default"},
    "galaxy.taxonomy": {"memory_id": "test"},
    "galaxy.transfer": {"galaxy": "default", "source": "default", "target": "default"},
    "garden_list_files": {"garden": "beauty"},
    "garden_list_functions": {"garden": "beauty"},
    "garden_map_system": {"garden": "beauty", "system_id": "test"},
    "garden_resolve": {"virtual_path": "test"},
    "garden_resonance": {"source": "beauty", "target": "wisdom"},
    "garden_search": {"query": "test"},
    "gating.detect": {"query": "test"},
    "gating.set_context": {"context": "test"},
    "grimoire_cast": {"spell_name": "test"},
    "grimoire_recommend": {"task": "test"},
    "grimoire_suggest": {"task": "test"},
    "hexagram.dispatch": {"hexagram_num": 1},
    "hexagram.simd_execute": {"hexagram_num": 1},
    "ilp.receipt": {"payment_id": "test"},
    "ilp.send": {"amount": 1, "destination": "test"},
    "import_memories": {"data": "[]"},
    "karma.verify_anchor": {"anchor_hash": "test", "tx_hash": "test"},
    "kg.extract": {"text": "test"},
    "kg.query": {"name": "test"},
    "kg2.entity": {"name": "test"},
    "kg2.extract": {"text": "test"},
    "learning.suggest": {"current_tool": "test"},
    "marketplace.complete": {"negotiation_id": "test"},
    "marketplace.negotiate": {"listing_id": "test"},
    "marketplace.remove": {"listing_id": "test"},
    "memory.rent": {"memory_id": "test", "galaxy_name": "default", "tx_hash": "test"},
    "metaplasticity.apply": {"memory_id": "test"},
    "metaplasticity.batch": {"updates": [{"memory_id": "test", "delta": 0.1}]},
    "metaplasticity.plasticity": {"memory_id": "test"},
    "model.hash": {"path": "test"},
    "model.register": {"path": "test", "model_name": "test", "sha256": "test"},
    "model.verify": {"path": "test", "model_name": "test"},
    "narrative.compress": {"content": "test"},
    "neuro.modulate": {"memories": [{"memory_id": "test"}]},
    "llama_cpp.chat": {"model": "test", "messages": [{"role": "user", "content": "test"}]},
    "llama_cpp.generate": {"model": "test", "prompt": "test"},
    "oms.export": {"galaxy": "default"},
    "oms.import": {"path": "test.mem"},
    "oms.inspect": {"path": "test.mem"},
    "oms.price": {"path": "test.mem"},
    "oms.verify": {"path": "test.mem"},
    "pipeline.create": {"name": "test", "steps": [{"tool": "search_memories", "args": {"query": "test"}}]},
    "polyglot.actor": {"operation": "test"},
    "polyglot.evolution": {"operation": "test"},
    "polyglot.memory_query": {"operation": "encode", "text": "test"},
    "polyglot.yield": {"operation": "test"},
    "reconsolidation.mark": {"memory_id": "test"},
    "reconsolidation.update": {"memory_id": "test"},
    "replay.batch": {"batches": [[{"memory_id": "test"}]]},
    "replay.run": {"sequence": [{"memory_id": "test"}]},
    "rerank": {"query": "test", "items": [{"id": "test", "content": "test"}]},
    "ripple.tag": {"memory_id": "test", "tag": "test"},
    "ripple.tags": {"memory_id": "test"},
    "sabha.convene": {"topic": "test", "task": "test"},
    "sandbox.set_limits": {"tool_name": "test"},
    "sangha_lock_release": {"resource": "test"},
    "session.accept_handoff": {"handoff_id": "test"},
    "session.handoff_transfer": {"session_id": "test"},
    "shelter.execute": {"name": "default", "payload": "pass"},
    "shelter.inspect": {"name": "default"},
    "shelter.policy": {"name": "default"},
    "simd.batch": {"query": [1.0], "vectors": [[1.0]]},
    "simd.cosine": {"a": [1.0], "b": [1.0]},
    "starter_packs.get": {"name": "test"},
    "starter_packs.suggest": {"context": "test"},
    "strata.analyze": {"path": "."},
    "strata.archaeology": {"path": "."},
    "strata.survey": {"path": "."},
    "swarm.complete": {"plan_id": "test", "task_id": "test"},
    "swarm.decompose": {"goal": "test"},
    "swarm.plan": {"plan_id": "test", "goal": "test"},
    "swarm.resolve": {"topic_id": "test"},
    "swarm.route": {"plan_id": "test", "goal": "test"},
    "swarm.vote": {"topic_id": "test", "agent_id": "test"},
    "task.complete": {"task_id": "test"},
    "task.distribute": {"task": "test", "workers": [], "command": "test"},
    "vector.index": {"memory_id": "test", "content": "test"},
    "vote.analyze": {"session_id": "test"},
    "vote.cast": {"session_id": "test", "voter": "test"},
    "vote.create": {"problem": "test"},
    "vote.record_outcome": {"session_id": "test", "outcome": "test"},
    "war_room.execute": {"campaign": {"objective": "test"}},
    "windsurf_export_conversation": {"path": "test"},
    "windsurf_read_conversation": {"path": "test"},
    "windsurf_search_conversations": {"query": "test"},
    "wm": {"thought": "test"},
    "wm_write": {"content": "test"},
    "workspace.propose": {"source": "test", "content": "test"},
    "zodiac.activate": {"core": "aries"},
    "zodiac.council": {"topic": "test", "decision": "test"},
    "constellation.merge": {"source": "test", "target": "test"},
    "constellation.stats": {},
    "context.pack": {"query": "test"},
    "create_memory": {"content": "test", "title": "test"},
    "consult_wisdom_council": {"query": "test"},
    "bitnet_infer": {"prompt": "test"},
    "codegenome.fork": {"parent": "test/test", "name": "test"},
    "codegenome_validate": {"prompt": "test"},
    "external.repo_compare": {"repo": "test/test", "local_module": "test"},
    "external.repo_scan": {"repo": "test/test"},
    "external.wiki_query": {"repo": "test/test", "question": "test"},
    "wiki.update": {"title": "test", "content": "test"},
    # ── exception fixes ──
    "alchemical_cycle": {"task": "test", "cycles": 1},
    "gratitude.benefits": {},
}


def exercise_tool(tool_name: str, dry_run: bool = False, timeout: float = 15.0) -> dict:
    """Exercise a single tool and return the result.

    Args:
        tool_name: Name of the tool to exercise.
        dry_run: If True, don't actually call the tool.
        timeout: Maximum seconds to wait for the tool to respond.
    """
    import signal

    handler_entry = DISPATCH_TABLE.get(tool_name)
    if handler_entry is None:
        return {"tool": tool_name, "status": "error", "error": "not in dispatch table"}

    args = dict(SAFE_DEFAULTS.get(tool_name, {}))
    # Merge dynamic context values (from _setup_context)
    dyn = DYNAMIC_DEFAULTS.get(tool_name)
    if dyn:
        for param_name, ctx_key in dyn.items():
            ctx_val = _ctx.get(ctx_key, "")
            if ctx_val:
                args[param_name] = ctx_val
    if dry_run:
        return {"tool": tool_name, "status": "dry_run", "args": args}

    def _timeout_handler(signum, frame):
        raise TimeoutError(f"Tool {tool_name} exceeded {timeout}s timeout")

    start = time.monotonic()
    try:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.setitimer(signal.ITIMER_REAL, timeout)

        result = handler_entry(**args)
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old_handler)
        duration_ms = (time.monotonic() - start) * 1000

        success = True
        error_code = None
        if isinstance(result, dict):
            status = result.get("status", "")
            if status == "error":
                success = False
                error_code = result.get("error_code")
                if not error_code:
                    err_msg = result.get("error", result.get("message", ""))
                    if isinstance(err_msg, str):
                        if "not found" in err_msg.lower():
                            error_code = "not_found"
                        elif "required" in err_msg.lower():
                            error_code = "invalid_params"
                        elif "unavailable" in err_msg.lower() or "not available" in err_msg.lower():
                            error_code = "unavailable"
                        elif "failed" in err_msg.lower():
                            error_code = "internal_error"
                        else:
                            error_code = "internal_error"
                    else:
                        error_code = "internal_error"

        tracker = get_tool_usage_tracker()
        tracker.record(
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=success,
            error_code=error_code,
            input_tokens=len(json.dumps(args, default=str)) // 4,
            output_tokens=len(json.dumps(result, default=str)) // 4 if result else 0,
        )

        return {
            "tool": tool_name,
            "status": "success" if success else "error",
            "duration_ms": round(duration_ms, 2),
            "error_code": error_code,
        }
    except Exception as e:
        try:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
        except Exception:
            pass
        duration_ms = (time.monotonic() - start) * 1000
        error_msg = str(e)[:200]

        tracker = get_tool_usage_tracker()
        tracker.record(
            tool_name=tool_name,
            duration_ms=duration_ms,
            success=False,
            error_code=type(e).__name__,
            error_message=error_msg,
        )

        return {
            "tool": tool_name,
            "status": "exception",
            "duration_ms": round(duration_ms, 2),
            "error": error_msg,
            "error_type": type(e).__name__,
        }


# Tools that hang indefinitely due to SQLite lock contention or blocking I/O.
# These are exercised separately or skipped to keep the script responsive.
SKIP_TOOLS: set[str] = {
    "constellation.detect",    # Hangs on full SQLite scan of 49K memories
    "citta.sensorium",        # Blocks on embedding model loading
    "checkpoint_session",     # Blocks on session I/O
    "consciousness.smarana",  # Blocks on embedding model loading
    "corpus_callosum.debate", # Multiple llama-server HTTP calls, 3+ min per call
    "embedding.daemon_process", # ONNX runtime blocks signal timeout
    "galaxy.ingest",          # ONNX embedding blocks signal timeout
}

# Dynamic context — populated by _setup_context() before the main run.
# Stores IDs from prerequisite operations (watcher_id, vote_session_id, etc.)
_ctx: dict[str, str] = {}


def _setup_context() -> None:
    """Create prerequisite resources so dependent tools have valid IDs."""
    print("Setting up test context...")
    _ctx["llama_model"] = "qwen3-4b"

    # 1. Create a watcher
    try:
        r = DISPATCH_TABLE["watcher_add"](path="/tmp")
        if isinstance(r, dict) and r.get("watcher_id"):
            _ctx["watcher_id"] = r["watcher_id"]
    except Exception:
        pass

    # 2. Create a vote session
    try:
        r = DISPATCH_TABLE["vote.create"](problem="test question")
        if isinstance(r, dict) and r.get("session_id"):
            _ctx["vote_session_id"] = r["session_id"]
    except Exception:
        pass

    # 3. Create a swarm plan
    try:
        r = DISPATCH_TABLE["swarm.decompose"](goal="test task")
        if isinstance(r, dict) and r.get("plan_id"):
            _ctx["swarm_plan_id"] = r["plan_id"]
            # Extract task_id from the plan
            tasks = r.get("subtasks", [])
            if tasks and isinstance(tasks, list):
                _ctx["swarm_task_id"] = tasks[0].get("id", "task_0")
    except Exception:
        pass

    # 4. Create a session
    try:
        r = DISPATCH_TABLE["create_session"](name="exercise_test")
        if isinstance(r, dict):
            sess = r.get("session", {})
            if isinstance(sess, dict):
                _ctx["session_id"] = sess.get("id", "")
    except Exception:
        pass

    # 5. Issue an engagement token
    try:
        r = DISPATCH_TABLE["engagement.issue"](issuer="exercise", scope=["test"], tools=[])
        if isinstance(r, dict):
            _ctx["engagement_token_id"] = r.get("token_id", r.get("id", ""))
    except Exception:
        pass

    # 6. Create a shelter
    try:
        DISPATCH_TABLE["shelter.create"](name="exercise_shelter", tier="auto", ephemeral=False)
        _ctx["shelter_name"] = "exercise_shelter"
    except Exception:
        pass

    # 7. Get a dream_id from dream.list (dream.start doesn't return one)
    try:
        r = DISPATCH_TABLE["dream.list"]()
        if isinstance(r, dict):
            dreams = r.get("details", {}).get("dreams", r.get("dreams", []))
            if isinstance(dreams, list) and dreams:
                first = dreams[0]
                if isinstance(first, dict):
                    _ctx["dream_id"] = first.get("id", first.get("dream_id", ""))
                elif isinstance(first, str):
                    _ctx["dream_id"] = first
    except Exception:
        pass

    # 8. Find a windsurf conversation path
    try:
        r = DISPATCH_TABLE["windsurf_list_conversations"]()
        if isinstance(r, dict) and r.get("conversations"):
            convs = r["conversations"]
            if isinstance(convs, list) and convs:
                first = convs[0]
                if isinstance(first, dict):
                    _ctx["windsurf_path"] = first.get("path", first.get("file", ""))
                elif isinstance(first, str):
                    _ctx["windsurf_path"] = first
    except Exception:
        pass

    # 9. Export a galaxy to get a .mem file for OMS tools
    try:
        r = DISPATCH_TABLE["oms.export"](galaxy="default")
        if isinstance(r, dict) and r.get("path"):
            _ctx["oms_mem_path"] = r["path"]
    except Exception:
        pass

    # 10. Get a valid memory_id from the memory system
    try:
        r = DISPATCH_TABLE["list_memories"](limit=1)
        if isinstance(r, dict):
            mems = r.get("results", r.get("memories", []))
            if isinstance(mems, list) and mems:
                first = mems[0]
                if isinstance(first, dict):
                    _ctx["memory_id"] = first.get("id", first.get("memory_id", ""))
    except Exception:
        pass

    # 11. Get starter pack name
    try:
        r = DISPATCH_TABLE["starter_packs.list"]()
        if isinstance(r, dict) and r.get("packs"):
            packs = r["packs"]
            if isinstance(packs, list) and packs:
                first = packs[0]
                if isinstance(first, dict):
                    _ctx["starter_pack_name"] = first.get("name", first.get("id", ""))
                elif isinstance(first, str):
                    _ctx["starter_pack_name"] = first
    except Exception:
        pass

    # 12. Create a marketplace listing for marketplace tools
    try:
        r = DISPATCH_TABLE["marketplace.publish"](
            title="test listing",
            description="test",
            price_xrp=0.0,
            service_type="general",
        )
        if isinstance(r, dict):
            _ctx["marketplace_listing_id"] = r.get("listing_id", r.get("id", ""))
    except Exception:
        pass

    # 13. Get valid grimoire spell name from grimoire_read
    try:
        r = DISPATCH_TABLE["grimoire_read"]()
        if isinstance(r, dict):
            spells = r.get("spells", [])
            if isinstance(spells, list) and spells:
                first = spells[0]
                if isinstance(first, dict):
                    _ctx["grimoire_spell"] = first.get("name", first.get("id", ""))
    except Exception:
        pass

    print(f"  Context: {', '.join(f'{k}={v[:20]}' for k, v in _ctx.items() if v)}")
    print()


# Tools that need dynamic IDs from _ctx merged into their SAFE_DEFAULTS
DYNAMIC_DEFAULTS: dict[str, dict[str, str]] = {
    "watcher_recent_events": {"watcher_id": "watcher_id"},
    "watcher_remove": {"watcher_id": "watcher_id"},
    "watcher_start": {"watcher_id": "watcher_id"},
    "watcher_stop": {"watcher_id": "watcher_id"},
    "vote.analyze": {"session_id": "vote_session_id"},
    "vote.cast": {"session_id": "vote_session_id", "voter": ""},
    "vote.record_outcome": {"session_id": "vote_session_id", "outcome": "test"},
    "swarm.complete": {"plan_id": "swarm_plan_id", "task_id": "swarm_task_id"},
    "swarm.plan": {"plan_id": "swarm_plan_id"},
    "swarm.route": {"plan_id": "swarm_plan_id"},
    "swarm.resolve": {"topic_id": "swarm_plan_id"},
    "resume_session": {"session_id": "session_id"},
    "session.handoff_transfer": {"session_id": "session_id"},
    "session.accept_handoff": {"handoff_id": "session_id"},
    "engagement.revoke": {"token_id": "engagement_token_id"},
    "shelter.execute": {"name": "shelter_name"},
    "shelter.inspect": {"name": "shelter_name"},
    "shelter.policy": {"name": "shelter_name"},
    "dream.read": {"dream_id": "dream_id"},
    "dream.promote": {"dream_id": "dream_id"},
    "dream.expire": {"dream_id": "dream_id"},
    "llama_cpp.chat": {"model": "llama_model"},
    "llama_cpp.generate": {"model": "llama_model"},
    "windsurf_read_conversation": {"path": "windsurf_path"},
    "windsurf_export_conversation": {"path": "windsurf_path"},
    "oms.import": {"path": "oms_mem_path"},
    "oms.inspect": {"path": "oms_mem_path"},
    "oms.price": {"path": "oms_mem_path"},
    "oms.verify": {"path": "oms_mem_path"},
    "fast_read_memory": {"memory_id": "memory_id"},
    "galaxy.migrate": {"memory_id": "memory_id"},
    "galaxy.lineage": {"memory_id": "memory_id"},
    "starter_packs.get": {"name": "starter_pack_name"},
    "marketplace.negotiate": {"listing_id": "marketplace_listing_id"},
    "marketplace.complete": {"negotiation_id": "marketplace_listing_id"},
    "marketplace.remove": {"listing_id": "marketplace_listing_id"},
    "grimoire_cast": {"spell_name": "grimoire_spell"},
    "verification.attest": {"request_id": "session_id", "attestation": "test"},
}


def _main():
    parser = argparse.ArgumentParser(description="Exercise every WhiteMagic tool")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually call tools")
    parser.add_argument("--limit", type=int, default=0, help="Limit to N tools (0 = all)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print each result")
    args = parser.parse_args()

    tools = sorted(DISPATCH_TABLE.keys())
    if args.limit > 0:
        tools = tools[: args.limit]

    if not args.dry_run:
        _setup_context()

    print(f"Exercising {len(tools)} tools{' (dry run)' if args.dry_run else ''}...")
    print()

    results = {"success": 0, "error": 0, "exception": 0, "dry_run": 0, "skipped": 0}
    errors = []
    exceptions = []

    for i, tool_name in enumerate(tools, 1):
        if tool_name in SKIP_TOOLS:
            results["skipped"] += 1
            if args.verbose:
                print(f"  [{i:3d}/{len(tools)}] ⌀ {tool_name:40s} skipped")
            continue

        result = exercise_tool(tool_name, dry_run=args.dry_run)
        status = result["status"]
        results[status] = results.get(status, 0) + 1

        if status == "error":
            errors.append(result)
        elif status == "exception":
            exceptions.append(result)

        if args.verbose or status == "exception":
            marker = "✓" if status == "success" else "✗" if status == "error" else "!"
            print(f"  [{i:3d}/{len(tools)}] {marker} {tool_name:40s} {result.get('duration_ms', 0):8.1f}ms  {status}")
        elif i % 50 == 0:
            print(f"  [{i:3d}/{len(tools)}] ... {results['success']} ok, {results.get('error', 0)} err, {results.get('exception', 0)} exc")
        
        sys.stdout.flush()
        if i % 50 == 0:
            gc.collect()

    print()
    print(f"Results: {results}")
    if results.get('skipped', 0) > 0:
        print(f"Skipped: {', '.join(sorted(SKIP_TOOLS))}"), 
    if errors:
        print(f"\nErrors ({len(errors)}):")
        for e in errors:
            print(f"  {e['tool']:40s} {e.get('error_code', '')}")
    if exceptions:
        print(f"\nExceptions ({len(exceptions)}):")
        for e in exceptions:
            print(f"  {e['tool']:40s} {e.get('error_type', '')}: {e.get('error', '')[:80]}")

    # Print tracker summary
    if not args.dry_run:
        tracker = get_tool_usage_tracker()
        summary = tracker.get_summary()
        print(f"\nTracker Summary: {summary}")


if __name__ == "__main__":
    _main()
