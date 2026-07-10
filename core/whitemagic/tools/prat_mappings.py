"""PRAT Tool Mappings.

Extracted from prat_router.py for better separation of concerns.
Contains the TOOL_TO_GANA mapping dictionary and related lookup functions.
"""
# ruff: noqa: BLE001

import logging
from typing import Any, cast

logger = logging.getLogger(__name__)

TOOL_TO_GANA: dict[str, str] = {
    # ═══ HORN — Session Initialization & Setup ═══
    "session_bootstrap": "gana_horn",
    "create_session": "gana_horn",
    "resume_session": "gana_horn",
    "checkpoint_session": "gana_horn",
    # ═══ NECK — Core Memory Creation & Stability ═══
    "create_memory": "gana_neck",
    "update_memory": "gana_neck",
    "memory_update": "gana_neck",
    "import_memories": "gana_neck",
    "delete_memory": "gana_neck",
    "memory_delete": "gana_neck",
    # ═══ ROOT — System Health & Foundations ═══
    "health_report": "gana_root",
    "rust_status": "gana_root",
    "rust_similarity": "gana_root",
    "ship.check": "gana_root",
    "state.paths": "gana_root",
    "state.summary": "gana_root",
    # ═══ ROOM — Resource Locks & Privacy ═══
    "sangha_lock": "gana_room",
    "sandbox.set_limits": "gana_room",
    "sandbox.status": "gana_room",
    "sandbox.violations": "gana_room",
    # ═══ HEART — Session Context & Pulse ═══
    "scratchpad": "gana_heart",
    "session.handoff": "gana_heart",
    "session_handoff": "gana_heart",
    "session_handoff_summary": "gana_heart",
    "context.pack": "gana_heart",
    "context.status": "gana_heart",
    "working_memory.attend": "gana_heart",
    "working_memory.context": "gana_heart",
    "working_memory.status": "gana_heart",
    "get_session_context": "gana_heart",
    # ── Session Memory — Chronological conversation recording & recall ──
    "session.record": "gana_heart",
    "session.recall": "gana_heart",
    "session.replay": "gana_heart",
    "session.search": "gana_heart",
    "session.memory_stats": "gana_heart",
    "session.backfill": "gana_heart",
    "session.continuity": "gana_heart",
    "session.consolidate": "gana_heart",
    # ═══ TAIL — Performance & Acceleration ═══
    "simd.cosine": "gana_tail",
    "simd.batch": "gana_tail",
    "simd.status": "gana_tail",
    "hexagram.simd_execute": "gana_tail",
    "hexagram.dispatch": "gana_tail",
    "hexagram.boltzmann_select": "gana_tail",
    "execute_cascade": "gana_tail",
    "list_cascade_patterns": "gana_tail",
    # ═══ WINNOWING BASKET — Wisdom & Tag Filtering ═══
    "search_memories": "gana_winnowing_basket",
    "memory_search": "gana_winnowing_basket",
    "search_query": "gana_winnowing_basket",
    "vector.search": "gana_winnowing_basket",
    "vector.index": "gana_winnowing_basket",
    "vector.status": "gana_winnowing_basket",
    "fast_read_memory": "gana_winnowing_basket",
    "batch_read_memories": "gana_winnowing_basket",
    "read_memory": "gana_winnowing_basket",
    "memory_read": "gana_winnowing_basket",
    "list_memories": "gana_winnowing_basket",
    "hybrid_recall": "gana_winnowing_basket",
    "graph_walk": "gana_winnowing_basket",
    # ═══ GHOST — Introspection & Metric Tracking ═══
    "gnosis": "gana_ghost",
    "capabilities": "gana_ghost",
    "manifest": "gana_ghost",
    "get_telemetry_summary": "gana_ghost",
    "tool_usage_stats": "gana_ghost",
    "repo.summary": "gana_ghost",
    "explain_this": "gana_ghost",
    "drive.snapshot": "gana_ghost",
    "drive.event": "gana_ghost",
    "selfmodel.forecast": "gana_ghost",
    "selfmodel.alerts": "gana_ghost",
    "capability.matrix": "gana_ghost",
    "capability.status": "gana_ghost",
    "capability.suggest": "gana_ghost",
    "graph_topology": "gana_ghost",
    "surprise_stats": "gana_ghost",
    "watcher_add": "gana_ghost",
    "watcher_remove": "gana_ghost",
    "watcher_start": "gana_ghost",
    "watcher_stop": "gana_ghost",
    "watcher_status": "gana_ghost",
    "watcher_recent_events": "gana_ghost",
    "watcher_stats": "gana_ghost",
    "watcher_list": "gana_ghost",
    # First-call discovery: one-shot 28-Gana surface, vitality, and bundle
    "list_ganas": "gana_ghost",
    "vitality": "gana_ghost",
    "discover": "gana_ghost",
    # Consciousness (Citta Architecture) — self-model & introspection
    "consciousness.depth": "gana_ghost",
    "consciousness.coherence": "gana_ghost",
    "consciousness.awaken": "gana_ghost",
    "consciousness.reflect": "gana_ghost",
    "consciousness.token_report": "gana_ghost",
    "consciousness.narrative": "gana_ghost",
    "consciousness.unified_field": "gana_ghost",
    "consciousness.status": "gana_ghost",
    "consciousness.smarana": "gana_ghost",
    "consciousness.flow": "gana_ghost",
    "consciousness.time_dilation": "gana_ghost",
    "consciousness.calibration": "gana_ghost",
    "consciousness.token_economy": "gana_ghost",
    "consciousness.stillness": "gana_ghost",
    # Citta Stream — temporal continuity (Ghost = introspection)
    "citta.continuity": "gana_ghost",
    "citta.stream_summary": "gana_ghost",
    "citta.sensorium": "gana_ghost",
    "citta.cycle": "gana_ghost",
    # ═══ WILLOW — Resilience & Flexibility ═══
    "rate_limiter.stats": "gana_willow",
    "grimoire_suggest": "gana_willow",
    "grimoire_cast": "gana_willow",
    "grimoire_recommend": "gana_willow",
    "grimoire_auto_status": "gana_willow",
    "grimoire_walkthrough": "gana_willow",
    "navigate_grimoire": "gana_willow",
    # ═══ STAR — Governance & PRAT Invocation ═══
    "governor_validate": "gana_star",
    "governor_set_goal": "gana_star",
    "governor_check_drift": "gana_star",
    "dharma.reload": "gana_star",
    "set_dharma_profile": "gana_star",
    "prat_get_context": "gana_star",
    "prat_invoke": "gana_star",
    "prat_list_morphologies": "gana_star",
    "prat_status": "gana_star",
    # ═══ EXTENDED NET — Pattern Connectivity ═══
    "pattern_search": "gana_extended_net",
    "cluster_stats": "gana_extended_net",
    "tool.graph": "gana_extended_net",
    "learning.patterns": "gana_extended_net",
    "learning.suggest": "gana_extended_net",
    "learning.status": "gana_extended_net",
    # ═══ WINGS — Deployment & Export ═══
    "export_memories": "gana_wings",
    "audit.export": "gana_wings",
    "mesh.connect": "gana_wings",
    "mesh.broadcast": "gana_wings",
    "mesh.status": "gana_wings",
    # ═══ CHARIOT — Mobility & Archaeology ═══
    "archaeology": "gana_chariot",
    "kg.extract": "gana_chariot",
    "kg.query": "gana_chariot",
    "kg.top": "gana_chariot",
    "kg.status": "gana_chariot",
    "kg2.extract": "gana_chariot",
    "kg2.batch": "gana_chariot",
    "kg2.entity": "gana_chariot",
    "kg2.stats": "gana_chariot",
    "embedding.daemon_start": "gana_chariot",
    "embedding.daemon_stop": "gana_chariot",
    "embedding.daemon_status": "gana_chariot",
    "embedding.daemon_process": "gana_chariot",
    # ═══ ABUNDANCE — Regeneration & Dream Cycle ═══
    "dream": "gana_abundance",
    "memory.lifecycle": "gana_abundance",
    "memory.retention_sweep": "gana_abundance",
    "serendipity_surface": "gana_abundance",
    "serendipity_mark_accessed": "gana_abundance",
    "entity_resolve": "gana_abundance",
    "whitemagic.tip": "gana_abundance",
    "gratitude.stats": "gana_abundance",
    "gratitude.benefits": "gana_abundance",
    "pulse.status": "gana_abundance",
    "bounty.create": "gana_abundance",
    "bounty.list": "gana_abundance",
    "memory.rent": "gana_abundance",
    # ═══ STRADDLING LEGS — Balance & Equilibrium ═══
    "evaluate_ethics": "gana_straddling_legs",
    "check_boundaries": "gana_straddling_legs",
    "verify_consent": "gana_straddling_legs",
    "get_ethical_score": "gana_straddling_legs",
    "get_dharma_guidance": "gana_straddling_legs",
    "harmony_vector": "gana_straddling_legs",
    # ═══ MOUND — Accumulation & Caching ═══
    "view_hologram": "gana_mound",
    "track_metric": "gana_mound",
    "get_metrics_summary": "gana_mound",
    "record_yin_yang_activity": "gana_mound",
    "get_yin_yang_balance": "gana_mound",
    "cache.flush": "gana_mound",
    "cache.status": "gana_mound",
    # ═══ STOMACH — Digestion & Resource Management ═══
    "pipeline": "gana_stomach",
    "task.distribute": "gana_stomach",
    "task.status": "gana_stomach",
    "task.list": "gana_stomach",
    "task.complete": "gana_stomach",
    "task.route_smart": "gana_stomach",
    # ═══ HAIRY HEAD — Detail & Debug ═══
    "salience.spotlight": "gana_hairy_head",
    "anomaly": "gana_hairy_head",
    "otel": "gana_hairy_head",
    "karma_report": "gana_hairy_head",
    "karmic_trace": "gana_hairy_head",
    "dharma_rules": "gana_hairy_head",
    # ═══ NET — Capture & Filtering ═══
    "prompt.render": "gana_net",
    "prompt.list": "gana_net",
    "prompt.reload": "gana_net",
    "karma.verify_chain": "gana_net",
    "karma.anchor": "gana_hairy_head",
    "karma.verify_anchor": "gana_hairy_head",
    "karma.anchor_status": "gana_hairy_head",
    # Dharma 4-tier escalation → Straddling Legs (ethics & balance)
    "dharma.escalate": "gana_straddling_legs",
    "dharma.review_queue": "gana_straddling_legs",
    "dharma.resolve_review": "gana_straddling_legs",
    # ═══ TURTLE BEAK — Precision & Protection ═══
    "edge_infer": "gana_turtle_beak",
    "edge_batch_infer": "gana_turtle_beak",
    "edge_stats": "gana_turtle_beak",
    "bitnet_infer": "gana_turtle_beak",
    "bitnet_status": "gana_turtle_beak",
    # ═══ THREE STARS — Judgment & Synthesis ═══
    "reasoning.bicameral": "gana_three_stars",
    "ensemble": "gana_three_stars",
    "solve_optimization": "gana_three_stars",
    "kaizen_analyze": "gana_three_stars",
    "kaizen_apply_fixes": "gana_three_stars",
    "art_of_war.wisdom": "gana_three_stars",
    "art_of_war.terrain": "gana_three_stars",
    "art_of_war.campaign": "gana_three_stars",
    "art_of_war.chapter": "gana_three_stars",
    "art_of_war.assess": "gana_three_stars",
    "art_of_war.plan": "gana_three_stars",
    "consult_wisdom_council": "gana_three_stars",
    # ═══ DIPPER — Governance & Strategy ═══
    "homeostasis": "gana_dipper",
    "maturity.assess": "gana_dipper",
    "starter_packs": "gana_dipper",
    "astro_status": "gana_dipper",
    "astro_shift": "gana_dipper",
    "neurotransmitter.status": "gana_dipper",
    "neurotransmitter.report": "gana_dipper",
    # ═══ OX — Endurance & Watchdog ═══
    "swarm.decompose": "gana_ox",
    "swarm.route": "gana_ox",
    "swarm.complete": "gana_ox",
    "swarm.vote": "gana_ox",
    "swarm.resolve": "gana_ox",
    "swarm.plan": "gana_ox",
    "swarm.status": "gana_ox",
    "worker.status": "gana_ox",
    # ── SkillForge — crystallized execution patterns (Ox — Endurance) ──
    "skill.list": "gana_ox",
    "skill.invoke": "gana_ox",
    "skill.seed": "gana_ox",
    "skill.export_all": "gana_ox",
    "skill.import": "gana_ox",
    # ═══ GIRL — Nurture & User Profile ═══
    "agent.register": "gana_girl",
    "agent.heartbeat": "gana_girl",
    "agent.list": "gana_girl",
    "agent.capabilities": "gana_girl",
    "agent.deregister": "gana_girl",
    "agent.trust": "gana_girl",
    # ═══ VOID — Emptiness & Defrag ═══
    "galactic.dashboard": "gana_void",
    "galactic_dashboard": "gana_void",
    "garden_activate": "gana_void",
    "garden_status": "gana_void",
    "garden_health": "gana_void",
    "garden_synergy": "gana_void",
    # S025: Garden Directory Tools
    "garden_list_files": "gana_void",
    "garden_list_functions": "gana_void",
    "garden_search": "gana_void",
    "garden_resonance": "gana_void",
    "garden_map_system": "gana_void",
    "garden_stats": "gana_void",
    # S025 Phase 6: Virtual Filesystem
    "garden_browse": "gana_void",
    "garden_resolve": "gana_void",
    "galaxy.create": "gana_void",
    "galaxy.switch": "gana_void",
    "galaxy.list": "gana_void",
    "galaxy.status": "gana_void",
    "galaxy.ingest": "gana_void",
    "galaxy.delete": "gana_void",
    "galaxy.backup": "gana_void",
    "galaxy.restore": "gana_void",
    "galaxy.transfer": "gana_void",
    "galaxy.merge": "gana_void",
    "galaxy.sync": "gana_void",
    "galaxy.lineage": "gana_void",
    "galaxy.taxonomy": "gana_void",
    "galaxy.canonical_taxonomy": "gana_void",
    "galaxy.export_tutorial": "gana_void",
    "galaxy.search_multi": "gana_void",
    "galaxy.share": "gana_void",
    "galaxy.list_shared": "gana_void",
    "galaxy.lineage_stats": "gana_void",
    # ═══ SIMPLIFIED ALIASES ═══
    "remember": "gana_neck",
    "recall": "gana_winnowing_basket",
    "think": "gana_three_stars",
    "check": "gana_root",
    # ═══ ROOF — Shelter & Zodiac Cores ═══
    "llama.models": "gana_roof",
    "llama.generate": "gana_roof",
    "llama.chat": "gana_roof",
    "llama.agent": "gana_roof",
    "zodiac.status": "gana_roof",
    # ═══ ENCAMPMENT — Transition & Handoff ═══
    "sangha_chat_send": "gana_encampment",
    "sangha_chat_read": "gana_encampment",
    "broker.publish": "gana_encampment",
    "broker.history": "gana_encampment",
    "broker.status": "gana_encampment",
    # ═══ WALL — Boundaries & Notifications ═══
    "vote.create": "gana_wall",
    "vote.cast": "gana_wall",
    "vote.analyze": "gana_wall",
    "vote.list": "gana_wall",
    "vote.record_outcome": "gana_wall",
    "engagement.issue": "gana_wall",
    "engagement.validate": "gana_wall",
    "engagement.revoke": "gana_wall",
    "engagement.list": "gana_wall",
    "engagement.status": "gana_wall",
    # ═══ ROOM — Edgerunner Violet: MCP Integrity & Security Monitor ═══
    "mcp_integrity.snapshot": "gana_room",
    "mcp_integrity.verify": "gana_room",
    "mcp_integrity.status": "gana_room",
    "security.alerts": "gana_room",
    "security.monitor_status": "gana_room",
    # ═══ ROOF — Edgerunner Violet: Model Signing ═══
    "model.register": "gana_roof",
    "model.verify": "gana_roof",
    "model.list": "gana_roof",
    "model.hash": "gana_roof",
    "model.signing_status": "gana_roof",
    # ═══ THREE STARS — Gana Sabha (Council Protocol — 12.108.25) ═══
    "sabha.convene": "gana_three_stars",
    "sabha.status": "gana_three_stars",
    # ═══ STAR — Gana Forge (Declarative Extension — 12.108.17) ═══
    "forge.status": "gana_star",
    "forge.reload": "gana_star",
    "forge.validate": "gana_star",
    # ═══════════════════════════════════════════════════════════
    # ORPHAN RESOLUTION — 94 dispatch tools mapped to Ganas
    # Ensures full coherence between dispatch_table and PRAT.
    # ═══════════════════════════════════════════════════════════
    # ── HORN — Additional session tools ──
    "session_status": "gana_horn",
    "session.handoff_transfer": "gana_horn",
    "session.accept_handoff": "gana_horn",
    "session.list_handoffs": "gana_horn",
    "focus_session": "gana_horn",
    # ── NECK — Memory mutation ──
    "thought_clone": "gana_neck",
    # ── ROOT — Rust acceleration status ──
    "rust_audit": "gana_root",
    "rust_compress": "gana_root",
    # ── ROOM — Security & locking sub-tools ──
    "sangha_lock_acquire": "gana_room",
    "sangha_lock_release": "gana_room",
    "sangha_lock_list": "gana_room",
    "anti_loop_check": "gana_room",
    "immune_scan": "gana_room",
    "immune_heal": "gana_room",
    # ── HEART — Scratchpad sub-tools ──
    "scratchpad_create": "gana_heart",
    "scratchpad_update": "gana_heart",
    "scratchpad_finalize": "gana_heart",
    "analyze_scratchpad": "gana_heart",
    # ── TAIL — Acceleration sub-tools ──
    "token_report": "gana_tail",
    # ── GHOST — Introspection sub-tools + watchers ──
    "capability_harness": "gana_ghost",
    "get_agent_capabilities": "gana_ghost",
    # ── WILLOW — Grimoire sub-tools ──
    "grimoire_list": "gana_willow",
    "grimoire_read": "gana_willow",
    "cast_oracle": "gana_willow",
    # ── STAR — Governor sub-tools ──
    "governor_check_budget": "gana_star",
    "governor_check_dharma": "gana_star",
    "governor_stats": "gana_star",
    "governor_validate_path": "gana_star",
    # ── EXTENDED NET — Pattern & graph sub-tools ──
    "tool.graph_full": "gana_extended_net",
    "coherence_boost": "gana_extended_net",
    "resonance_trace": "gana_extended_net",
    # ── CHARIOT — Archaeology sub-tools + Windsurf ──
    "archaeology_scan_directory": "gana_chariot",
    "archaeology_search": "gana_chariot",
    "archaeology_stats": "gana_chariot",
    "archaeology_report": "gana_chariot",
    "archaeology_daily_digest": "gana_chariot",
    "archaeology_process_wisdom": "gana_chariot",
    "archaeology_mark_read": "gana_chariot",
    "archaeology_mark_written": "gana_chariot",
    "archaeology_have_read": "gana_chariot",
    "archaeology_find_unread": "gana_chariot",
    "archaeology_find_changed": "gana_chariot",
    "archaeology_recent_reads": "gana_chariot",
    "windsurf_list_conversations": "gana_chariot",
    "windsurf_read_conversation": "gana_chariot",
    "windsurf_search_conversations": "gana_chariot",
    "windsurf_export_conversation": "gana_chariot",
    "windsurf_stats": "gana_chariot",
    # ── ABUNDANCE — Dream cycle + lifecycle sub-tools ──
    "dream_start": "gana_abundance",
    "dream_stop": "gana_abundance",
    "dream_status": "gana_abundance",
    "dream_now": "gana_abundance",
    "dream.list": "gana_abundance",
    "dream.read": "gana_abundance",
    "dream.promote": "gana_abundance",
    "dream.expire": "gana_abundance",
    "memory.lifecycle_sweep": "gana_abundance",
    "memory.lifecycle_stats": "gana_abundance",
    "memory.consolidate": "gana_abundance",
    "memory.consolidation_stats": "gana_abundance",
    # ── STRADDLING LEGS — Wu Xing balance ──
    "wu_xing_balance": "gana_straddling_legs",
    # ── STOMACH — Pipeline sub-tools ──
    "pipeline.create": "gana_stomach",
    "pipeline.list": "gana_stomach",
    "pipeline.status": "gana_stomach",
    # ── HAIRY HEAD — Anomaly & OTel sub-tools ──
    "anomaly.check": "gana_hairy_head",
    "anomaly.history": "gana_hairy_head",
    "anomaly.status": "gana_hairy_head",
    "otel.metrics": "gana_hairy_head",
    "otel.spans": "gana_hairy_head",
    "otel.status": "gana_hairy_head",
    "voice_audit.scan": "gana_hairy_head",
    "voice_audit.status": "gana_hairy_head",
    "voice_audit.quarantine_list": "gana_hairy_head",
    # ── TURTLE BEAK — Edge inference sub-tools ──
    "edge_add_rule": "gana_turtle_beak",
    # ── THREE STARS — Ensemble sub-tools ──
    "ensemble.query": "gana_three_stars",
    "ensemble.history": "gana_three_stars",
    "ensemble.status": "gana_three_stars",
    "corpus_callosum.debate": "gana_three_stars",
    "corpus_callosum.status": "gana_three_stars",
    "foresight.analyze": "gana_three_stars",
    "foresight.constellations": "gana_three_stars",
    "foresight.decay": "gana_three_stars",
    "foresight.convergence": "gana_three_stars",
    # ── DIPPER — Homeostasis + starter packs sub-tools ──
    "homeostasis.check": "gana_dipper",
    "homeostasis.status": "gana_dipper",
    "starter_packs.get": "gana_dipper",
    "starter_packs.list": "gana_dipper",
    "starter_packs.suggest": "gana_dipper",
    # ── ENCAMPMENT — Gan Ying sub-tools ──
    "ganying_emit": "gana_encampment",
    "ganying_history": "gana_encampment",
    "ganying_listeners": "gana_encampment",
    # ── v14.2: JIT Memory Researcher (Winnowing Basket — Wisdom & Search) ──
    "jit_research": "gana_winnowing_basket",
    "jit_research.stats": "gana_winnowing_basket",
    # ── v14.2: Narrative Compression (Abundance — Dream Cycle) ──
    "narrative.compress": "gana_abundance",
    "narrative.stats": "gana_abundance",
    # ── v14.2: Hermit Crab Mode (Room — Resource Locks & Privacy) ──
    "hermit.status": "gana_room",
    "hermit.assess": "gana_room",
    "hermit.withdraw": "gana_room",
    "hermit.mediate": "gana_room",
    "hermit.resolve": "gana_room",
    "hermit.verify_ledger": "gana_room",
    "hermit.check_access": "gana_room",
    # ── v14.2: Green Score Telemetry (Mound — Metrics & Caching) ──
    "green.report": "gana_mound",
    "green.record": "gana_mound",
    # ── v14.2: Cognitive Modes (Dipper — Strategy) ──
    "cognitive.mode": "gana_dipper",
    "cognitive.set": "gana_dipper",
    "cognitive.hints": "gana_dipper",
    "cognitive.stats": "gana_dipper",
    # ── v14.6: Physical Truth Verification (Straddling Legs — Ethics & Balance) ──
    "verification.request": "gana_straddling_legs",
    "verification.attest": "gana_straddling_legs",
    "verification.status": "gana_straddling_legs",
    # ── v15.2: Sovereign Sandbox (Roof — Shelter & Protection) ──
    "shelter.create": "gana_roof",
    "shelter.execute": "gana_roof",
    "shelter.inspect": "gana_roof",
    "shelter.destroy": "gana_roof",
    "shelter.status": "gana_roof",
    "shelter.policy": "gana_roof",
    # ── v15.2: Optimized Memory States (Void — Export/Import) ──
    "oms.export": "gana_void",
    "oms.import": "gana_void",
    "oms.inspect": "gana_void",
    "oms.verify": "gana_void",
    "oms.price": "gana_void",
    "oms.list": "gana_void",
    "oms.status": "gana_void",
    # ── v15.2: ILP Streaming Payments (Abundance — Regeneration) ──
    "ilp.configure": "gana_abundance",
    "ilp.send": "gana_abundance",
    "ilp.receipt": "gana_abundance",
    "ilp.history": "gana_abundance",
    "ilp.balance": "gana_abundance",
    "ilp.status": "gana_abundance",
    # ── Rebalanced: Marketplace → Wall (boundaries/transactions) ──
    "marketplace.publish": "gana_wall",
    "marketplace.discover": "gana_wall",
    "marketplace.negotiate": "gana_wall",
    "marketplace.complete": "gana_wall",
    "marketplace.my_listings": "gana_wall",
    "marketplace.remove": "gana_wall",
    "marketplace.status": "gana_wall",
    # ── v15.6: Cognitive Extensions ──
    # Reranking → Winnowing Basket (search/recall)
    "rerank": "gana_winnowing_basket",
    "rerank.status": "gana_winnowing_basket",
    # Working Memory → Heart (session context)
    # Reconsolidation → Abundance (regeneration/lifecycle)
    "reconsolidation.mark": "gana_abundance",
    "reconsolidation.update": "gana_abundance",
    "reconsolidation.status": "gana_abundance",
    # Community Maintenance → Extended Net (pattern connectivity)
    "community.propagate": "gana_extended_net",
    "community.status": "gana_extended_net",
    "community.health": "gana_extended_net",
    # ── Rebalanced: Browser & Web Research → Chariot (exploration/mobility) ──
    "browser_navigate": "gana_chariot",
    "browser_screenshot": "gana_chariot",
    "browser_click": "gana_chariot",
    "browser_type": "gana_chariot",
    "browser_extract_dom": "gana_chariot",
    "browser_get_interactables": "gana_chariot",
    "web_fetch": "gana_chariot",
    "web_fetch_enhanced": "gana_chariot",
    "web_search": "gana_chariot",
    "web_search_and_read": "gana_chariot",
    "research_topic": "gana_chariot",
    "browser_session_status": "gana_chariot",
    "image_analyze": "gana_chariot",
    "web_search_category": "gana_chariot",
    "web_search_batch": "gana_chariot",
    "deep_fetch": "gana_chariot",
    "research_repo": "gana_chariot",
    "research_url": "gana_chariot",
    "rabbit_hole_research": "gana_chariot",
    "web_cache_list": "gana_chariot",
    "web_cache_clear": "gana_chariot",
    "parallel_reason": "gana_three_stars",
    # ── v15.9: War Room & Shadow Clone Army (Ox — Endurance & Swarm) ──
    "war_room.status": "gana_ox",
    "war_room.plan": "gana_ox",
    "war_room.execute": "gana_ox",
    "war_room.hierarchy": "gana_ox",
    "war_room.campaigns": "gana_ox",
    "war_room.phase": "gana_ox",
    # ── v15.9: Imperial Doctrine (Dipper — Strategy) ──
    "doctrine.summary": "gana_dipper",
    "doctrine.stratagems": "gana_dipper",
    "doctrine.force": "gana_dipper",
    # ── v15.9: Art of War Engine (Three Stars — Judgment & Synthesis) ──
    # ── v15.9: Fool's Guard / Ralph Wiggum (Willow — Resilience) ──
    "fool_guard.status": "gana_willow",
    "fool_guard.dare_to_die": "gana_willow",
    "fool_guard.ralph": "gana_willow",
    # ── v15.8: Pattern Analysis Engines (previously hidden) ──
    # Mining engines → Extended Net (pattern connectivity)
    "causal.mine": "gana_extended_net",
    "causal.stats": "gana_extended_net",
    "association.mine": "gana_extended_net",
    "association.mine_semantic": "gana_extended_net",
    "constellation.detect": "gana_extended_net",
    "constellation.stats": "gana_extended_net",
    "constellation.merge": "gana_extended_net",
    "novelty.detect": "gana_extended_net",
    "novelty.stats": "gana_extended_net",
    "pattern_consciousness.status": "gana_extended_net",
    # Emergence → Extended Net
    "emergence.scan": "gana_extended_net",
    "emergence.status": "gana_extended_net",
    # Synthesis → Three Stars (judgment & synthesis)
    "satkona.fuse": "gana_three_stars",
    "reasoning.multispectral": "gana_three_stars",
    "elemental.optimize": "gana_three_stars",
    # Bridge + Galactic → Abundance (regeneration)
    "bridge.synthesize": "gana_abundance",
    "galactic.sweep": "gana_abundance",
    "galactic.stats": "gana_abundance",
    # Guideline Evolution → Star (governance)
    "guideline.evolve": "gana_star",
    # ── v22: CodeGenome / God-Kit (Chariot — Code Archaeology & Generation) ──
    "codegenome.generate": "gana_chariot",
    "codegenome.list": "gana_chariot",
    "codegenome.fork": "gana_chariot",
    "codegenome.status": "gana_chariot",
    # ── v22: Karma Record (Hairy Head — Detail & Debug) ──
    "karma_record": "gana_hairy_head",
    # ── v23: Fragment (Rust) — Winnowing Basket (search) + Chariot (codebase nav) ──
    "fragment.search": "gana_winnowing_basket",
    "fragment.index": "gana_winnowing_basket",
    "fragment.status": "gana_winnowing_basket",
    "fragment.query": "gana_winnowing_basket",
    # ── v23: STRATA — Chariot (codebase analysis + archaeology) ──
    "strata.analyze": "gana_chariot",
    "strata.survey": "gana_chariot",
    "strata.archaeology": "gana_chariot",
    "strata.list_checks": "gana_chariot",
    # ── v23: Polyglot Memory — Tail (acceleration) + Winnowing Basket (search) ──
    "polyglot.memory_query": "gana_tail",
    "polyglot.search": "gana_winnowing_basket",
    "polyglot.status": "gana_tail",
    # ── v23.4: Internal Wiki + External Repo (Chariot — self-knowledge + external scan) ──
    "wiki.generate": "gana_chariot",
    "wiki.query": "gana_chariot",
    "wiki.update": "gana_chariot",
    "wiki.scan": "gana_chariot",
    "wiki.stats": "gana_chariot",
    "external.wiki_query": "gana_chariot",
    "external.repo_scan": "gana_chariot",
    "external.repo_compare": "gana_chariot",
    # ── v24: Codebase Self-Model (Chariot — codebase perception + navigation) ──
    "codebase.scan": "gana_chariot",
    "codebase.recall": "gana_chariot",
    "codebase.structure": "gana_chariot",
    "codebase.status": "gana_chariot",
    "codebase.find": "gana_chariot",
    # ── v23.1: Unified Read API — Winnowing Basket (unified search/recall) ──
    "wm_read": "gana_winnowing_basket",
    "wm_read.status": "gana_winnowing_basket",
    # ── v23.1: Unified Write API — Neck (core memory creation) + Stomach (file/neural) ──
    "wm_write": "gana_neck",
    "wm_write.status": "gana_neck",
    # ── Neuro-Cognitive Systems ──
    # Spreading activation → Winnowing Basket (search/recall/priming)
    "activation.spread": "gana_winnowing_basket",
    "activation.stats": "gana_winnowing_basket",
    # Galaxy gating → Dipper (strategy/cognitive context)
    "gating.set_context": "gana_dipper",
    "gating.detect": "gana_dipper",
    "gating.mask": "gana_dipper",
    "gating.list": "gana_dipper",
    "gating.stats": "gana_dipper",
    # Sleep consolidation → Abundance (regeneration/lifecycle)
    "consolidation.run": "gana_abundance",
    "consolidation.stats": "gana_abundance",
    # Ripple tagging → Abundance (memory selection for consolidation)
    "ripple.tag": "gana_abundance",
    "ripple.tags": "gana_abundance",
    "ripple.decay": "gana_abundance",
    "ripple.stats": "gana_abundance",
    # Replay simulation → Abundance (memory reactivation during consolidation)
    "replay.run": "gana_abundance",
    "replay.batch": "gana_abundance",
    "replay.stats": "gana_abundance",
    # Neuromodulation → Dipper (cognitive strategy / state regulation)
    "neuro.compute": "gana_dipper",
    "neuro.modulate": "gana_dipper",
    "neuro.reset": "gana_dipper",
    "neuro.stats": "gana_dipper",
    # Metaplasticity → Extended Net (pattern connectivity / plasticity)
    "metaplasticity.apply": "gana_extended_net",
    "metaplasticity.batch": "gana_extended_net",
    "metaplasticity.plasticity": "gana_extended_net",
    "metaplasticity.decay": "gana_extended_net",
    "metaplasticity.stats": "gana_extended_net",
    # Global workspace → Three Stars (judgment/synthesis/broadcast)
    "workspace.propose": "gana_three_stars",
    "workspace.state": "gana_three_stars",
    "workspace.history": "gana_three_stars",
    "workspace.stats": "gana_three_stars",
    "workspace.ignite": "gana_three_stars",
    "workspace.pending": "gana_three_stars",
    "workspace.ignitions": "gana_three_stars",
    # Neuro sensorium → Ghost (introspection/self-model/citta)
    "sensorium.state": "gana_ghost",
    "sensorium.citta": "gana_ghost",
    "sensorium.stats": "gana_ghost",
    # Citta introspection → Ghost (introspection/self-model/citta)
    "citta.vector": "gana_ghost",
    "citta.trajectory": "gana_ghost",
    "citta.coherence": "gana_ghost",
    "consciousness.loop.status": "gana_ghost",
    "guna.balance.status": "gana_ghost",
    "meta.galaxy.overview": "gana_ghost",
    "possibility.explore": "gana_dipper",
    "knowledge_gap.run": "gana_heart",
    # ── v24.1: Security Bounty Tools ──
    # Foundry + ABI → Chariot (codebase analysis & navigation)
    "foundry.build": "gana_chariot",
    "foundry.test": "gana_chariot",
    "foundry.test_json": "gana_chariot",
    "abi.parse": "gana_chariot",
    "abi.summarize": "gana_chariot",
    "abi.decode_calldata": "gana_chariot",
    # Vuln Knowledge → Extended Net (pattern connectivity)
    "vuln.search": "gana_extended_net",
    "vuln.status": "gana_extended_net",
    "vuln.ingest_report": "gana_extended_net",
    # Contest → Wall (boundaries & marketplace / submissions)
    "contest.add_finding": "gana_wall",
    "contest.format": "gana_wall",
    "contest.status": "gana_wall",
    # OSS Bounty → Chariot (external repo scanning)
    "oss.scan_repo": "gana_chariot",
    "oss.scan_org": "gana_chariot",
    # Aggregate status → Ghost (introspection)
    "security.status": "gana_ghost",
    # PoC Pipeline → Chariot (codebase analysis & generation)
    "poc.generate": "gana_chariot",
    "poc.verify": "gana_chariot",
    "contest.prepare": "gana_wall",
    # HTTP Probe → Chariot (external exploration)
    "http_probe.get": "gana_chariot",
    "http_probe.post": "gana_chariot",
    "http_probe.xss": "gana_chariot",
    "http_probe.sqli": "gana_chariot",
    "http_probe.idor": "gana_chariot",
    "http_probe.ssrf": "gana_chariot",
    "api.state_machine": "gana_chariot",
    # Echidna → Chariot (codebase analysis)
    "echidna.fuzz": "gana_chariot",
    "echidna.status": "gana_chariot",
    # Fix Generator → Chariot (code generation) + Wall (PR submission)
    "fix.generate": "gana_chariot",
    "fix.apply": "gana_chariot",
    "pr.create": "gana_wall",
    "bounty.track": "gana_abundance",
    # Report Scraper → Extended Net (pattern ingestion)
    "report.scrape": "gana_extended_net",
    "report.ingest": "gana_extended_net",
    # Phase 7: Advanced Tools
    # Vuln Graph → Extended Net (pattern connectivity / graph)
    "vuln_graph.status": "gana_extended_net",
    "vuln_graph.chains": "gana_extended_net",
    "vuln_graph.cross_chain": "gana_extended_net",
    # Formal Verification → Three Stars (judgment & synthesis)
    "formal.verify": "gana_three_stars",
    "formal.status": "gana_three_stars",
    # Multi-Agent Swarm → Ox (endurance / swarm decompose)
    "swarm.analyze": "gana_ox",
    # Predictive Scoring → Dipper (strategy / cognitive modes)
    "predictive.score": "gana_dipper",
    "predictive.batch": "gana_dipper",
    # Audit Report → Chariot (codebase navigation / output)
    "audit.report": "gana_chariot",
    # Monitor → Hairy Head (detail & debug / anomaly monitoring)
    "monitor.status": "gana_hairy_head",
    "monitor.alerts": "gana_hairy_head",
    "monitor.contract": "gana_hairy_head",
    # Slither → Three Stars (judgment & synthesis)
    "slither.scan": "gana_three_stars",
    "slither.status": "gana_three_stars",
    # ── Previously orphaned tools (in dispatch table but not PRAT-mapped) ──
    # Alchemical cycle → Abundance (regeneration / dream cycle)
    "alchemical_cycle": "gana_abundance",
    # Code genome / DNA → Chariot (codebase navigation)
    "codegenome_validate": "gana_chariot",
    "dna_principles": "gana_chariot",
    "dna_validate": "gana_chariot",
    # Fast write → Ox (endurance / worker skills)
    "fast_write.append": "gana_ox",
    "fast_write.batch": "gana_ox",
    "fast_write.validate": "gana_ox",
    "fast_write.write": "gana_ox",
    # Galaxy management → Void (galaxies)
    "galaxy.export": "gana_void",
    "galaxy.import": "gana_void",
    "galaxy.list_types": "gana_void",
    "galaxy.migrate": "gana_void",
    "galaxy.route": "gana_void",
    "galaxy.stats": "gana_void",
    # Polyglot → Tail (performance & acceleration)
    "polyglot.actor": "gana_tail",
    "polyglot.evolution": "gana_tail",
    "polyglot.yield": "gana_tail",
    # Zodiac progression → Dipper (strategy / cognitive modes)
    "zodiac.activate": "gana_dipper",
    "zodiac.council": "gana_dipper",
    "zodiac.stats": "gana_dipper",
}

# Reverse: Gana → list of nested tools
GANA_TO_TOOLS: dict[str, list[str]] = {}
for _tool, _gana in TOOL_TO_GANA.items():
    GANA_TO_TOOLS.setdefault(_gana, []).append(_tool)


def get_gana_for_tool(tool_name: str) -> str | None:
    """Look up which Gana a tool belongs to."""
    return TOOL_TO_GANA.get(tool_name)


def get_tools_for_gana(gana_name: str) -> list[str]:
    """Get all tools nested under a Gana."""
    return GANA_TO_TOOLS.get(gana_name, [])


# ── Koka Hot Path Handler Mapping (S023 VC #8) ──
# Maps Gana → (koka_module, supported_operations)
_KOKA_GANA_HANDLERS: dict[str, tuple[str, set[str]]] = {
    "gana_ghost": ("gnosis", {"gnosis", "capabilities", "manifest", "telemetry"}),
    "gana_winnowing_basket": ("prat", {"search", "read", "list", "vector"}),
    "gana_willow": ("circuit", {"check", "reset", "status", "grimoire"}),
}


def try_koka_handler(
    gana_name: str, tool: str | None, args: dict | None
) -> dict | None:
    """Attempt to route a Gana call through Koka native handler.

    Returns None if Koka unavailable or operation not supported.
    Used for hot-path acceleration of 3+ Ganas (S023 VC #8).
    """
    handler_info = _KOKA_GANA_HANDLERS.get(gana_name)
    if not handler_info:
        return None  # This Gana doesn't have Koka handler

    koka_module, supported_ops = handler_info

    op = tool or "native"
    if op not in supported_ops and tool is not None:
        op_match = any(s in op for s in supported_ops)
        if not op_match:
            return None  # Operation not supported in Koka

    try:
        from whitemagic.core.acceleration.koka_native_bridge import koka_dispatch

        result = koka_dispatch(
            koka_module, f"handle_{op.replace('.', '_')}", args or {}, timeout=2.0
        )
        if result:
            # we should fall back to Python
            if result.get("status") == "error" or "error" in result:
                return None
            return cast(dict[str, Any], result)
    except Exception as e:
        logger.debug("Koka handler fallback for %s: %s", gana_name, e, exc_info=True)

    return None  # Fallback to Python
