"""dispatch_memory.py — Memory, search, export/import, and galaxy tools.

Domain slice imported by dispatch_table.py.
"""

from collections.abc import Callable
from typing import Any

from whitemagic.tools.dispatch_core import LazyHandler

DISPATCH_MEMORY: dict[str, Callable[..., dict[str, Any]]] = {
    "search_query": LazyHandler("memory", "handle_search_memories"),
    "create_memory": LazyHandler("memory", "handle_create_memory"),
    "fast_read_memory": LazyHandler("memory", "handle_fast_read_memory"),
    "batch_read_memories": LazyHandler("memory", "handle_batch_read_memories"),
    "search_memories": LazyHandler("memory", "handle_search_memories"),
    "memory_search": LazyHandler("memory", "handle_search_memories"),
    "memory_read": LazyHandler("misc", "handle_read_memory"),
    "memory_update": LazyHandler("misc", "handle_update_memory"),
    "memory_delete": LazyHandler("misc", "handle_delete_memory"),
    "read_memory": LazyHandler("misc", "handle_read_memory"),
    "list_memories": LazyHandler("misc", "handle_list_memories"),
    "update_memory": LazyHandler("misc", "handle_update_memory"),
    "delete_memory": LazyHandler("misc", "handle_delete_memory"),
    "export_memories": LazyHandler("export_import", "handle_export_memories"),
    "import_memories": LazyHandler("export_import", "handle_import_memories"),
    "galaxy.create": LazyHandler("galaxy", "handle_galaxy_create"),
    "galaxy.switch": LazyHandler("galaxy", "handle_galaxy_switch"),
    "galaxy.list": LazyHandler("galaxy", "handle_galaxy_list"),
    "galaxy.status": LazyHandler("galaxy", "handle_galaxy_status"),
    "galaxy.ingest": LazyHandler("galaxy", "handle_galaxy_ingest"),
    "galaxy.delete": LazyHandler("galaxy", "handle_galaxy_delete"),
    "galaxy.backup": LazyHandler("backup", "handle_galaxy_backup"),
    "galaxy.restore": LazyHandler("backup", "handle_galaxy_restore"),
    "galaxy.transfer": LazyHandler("galaxy", "handle_galaxy_transfer"),
    "galaxy.merge": LazyHandler("galaxy", "handle_galaxy_merge"),
    "galaxy.sync": LazyHandler("galaxy", "handle_galaxy_sync"),
    "galaxy.lineage": LazyHandler("galaxy", "handle_galaxy_lineage"),
    "galaxy.taxonomy": LazyHandler("galaxy", "handle_galaxy_taxonomy"),
    "galaxy.lineage_stats": LazyHandler("galaxy", "handle_galaxy_lineage_stats"),
    "galaxy.route": LazyHandler("galaxy", "handle_galaxy_route"),
    "galaxy.stats": LazyHandler("galaxy", "handle_galaxy_stats"),
    "galaxy.migrate": LazyHandler("galaxy", "handle_galaxy_migrate"),
    "galaxy.list_types": LazyHandler("galaxy", "handle_galaxy_list_types"),
    "galaxy.export": LazyHandler("galaxy", "handle_galaxy_export"),
    "galaxy.import": LazyHandler("galaxy", "handle_galaxy_import"),
    "galaxy.canonical_taxonomy": LazyHandler(
        "galaxy", "handle_galaxy_canonical_taxonomy"
    ),
    "galaxy.export_tutorial": LazyHandler("galaxy", "handle_galaxy_export_tutorial"),
    "galaxy.search_multi": LazyHandler("galaxy", "handle_galaxy_search_multi"),
    "galaxy.share": LazyHandler("galaxy", "handle_galaxy_share"),
    "galaxy.list_shared": LazyHandler("galaxy", "handle_galaxy_list_shared"),
    "hybrid_recall": LazyHandler("living_graph", "handle_hybrid_recall"),
    "graph_topology": LazyHandler("living_graph", "handle_graph_topology"),
    "graph_walk": LazyHandler("living_graph", "handle_graph_walk"),
    "surprise_stats": LazyHandler("living_graph", "handle_surprise_stats"),
    "entity_resolve": LazyHandler("living_graph", "handle_entity_resolve"),
    "community.propagate": LazyHandler("living_graph", "handle_community_propagate"),
    "community.status": LazyHandler("living_graph", "handle_community_status"),
    "community.health": LazyHandler("living_graph", "handle_community_health"),
    "galactic.dashboard": LazyHandler(
        "galactic_dashboard", "handle_galactic_dashboard"
    ),
    "memory.lifecycle": LazyHandler("governance", "handle_memory_lifecycle"),
    "memory.lifecycle_sweep": LazyHandler("governance", "handle_lifecycle_sweep"),
    "memory.lifecycle_stats": LazyHandler("governance", "handle_lifecycle_stats"),
    "memory.consolidate": LazyHandler("governance", "handle_consolidate_memories"),
    "memory.consolidation_stats": LazyHandler(
        "governance", "handle_consolidation_stats"
    ),
    "oms.export": LazyHandler("oms", "handle_oms_export"),
    "oms.import": LazyHandler("oms", "handle_oms_import"),
    "oms.inspect": LazyHandler("oms", "handle_oms_inspect"),
    "oms.verify": LazyHandler("oms", "handle_oms_verify"),
    "oms.price": LazyHandler("oms", "handle_oms_price"),
    "oms.list": LazyHandler("oms", "handle_oms_list"),
    "oms.status": LazyHandler("oms", "handle_oms_status"),
    "memory.rent": LazyHandler("economy", "handle_rent_galaxy"),
    "view_hologram": LazyHandler("misc", "handle_view_hologram"),
    "salience.spotlight": LazyHandler("cyberbrain", "handle_salience_spotlight"),
    "memory.retention_sweep": LazyHandler("cyberbrain", "handle_retention_sweep"),
    "remember": LazyHandler("aliases", "handle_remember"),
    "recall": LazyHandler("aliases", "handle_recall"),
    "polyglot.memory_query": LazyHandler("polyglot", "handle_polyglot_memory_query"),
    "polyglot.status": LazyHandler("polyglot", "handle_polyglot_status"),
    "polyglot.search": LazyHandler("polyglot", "handle_polyglot_search"),
    "polyglot.evolution": LazyHandler("polyglot", "handle_polyglot_evolution"),
    "polyglot.yield": LazyHandler("polyglot", "handle_polyglot_yield"),
    "polyglot.actor": LazyHandler("polyglot", "handle_polyglot_actor"),
    "wm_read": LazyHandler("wm_read", "handle_wm_read"),
    "wm_read.status": LazyHandler("wm_read", "handle_wm_read_status"),
    "wm_write": LazyHandler("wm_write", "handle_wm_write"),
    "wm_write.status": LazyHandler("wm_write", "handle_wm_write_status"),
    # ── Neuro-Cognitive Systems ──
    "activation.spread": LazyHandler(
        "neuro_cognitive", "handle_activation_spread"
    ),
    "activation.stats": LazyHandler(
        "neuro_cognitive", "handle_activation_stats"
    ),
    "gating.set_context": LazyHandler(
        "neuro_cognitive", "handle_gating_set_context"
    ),
    "gating.detect": LazyHandler(
        "neuro_cognitive", "handle_gating_detect"
    ),
    "gating.mask": LazyHandler(
        "neuro_cognitive", "handle_gating_mask"
    ),
    "gating.list": LazyHandler(
        "neuro_cognitive", "handle_gating_list"
    ),
    "gating.stats": LazyHandler(
        "neuro_cognitive", "handle_gating_stats"
    ),
    "consolidation.run": LazyHandler(
        "neuro_cognitive", "handle_consolidation_run"
    ),
    "consolidation.stats": LazyHandler(
        "neuro_cognitive", "handle_consolidation_stats"
    ),
    # ── Ripple Tagging ──
    "ripple.tag": LazyHandler("neuro_cognitive", "handle_ripple_tag"),
    "ripple.tags": LazyHandler("neuro_cognitive", "handle_ripple_tags"),
    "ripple.decay": LazyHandler("neuro_cognitive", "handle_ripple_decay"),
    "ripple.stats": LazyHandler("neuro_cognitive", "handle_ripple_stats"),
    # ── Replay Simulation ──
    "replay.run": LazyHandler("neuro_cognitive", "handle_replay_run"),
    "replay.batch": LazyHandler("neuro_cognitive", "handle_replay_batch"),
    "replay.stats": LazyHandler("neuro_cognitive", "handle_replay_stats"),
    # ── Neuromodulation ──
    "neuro.compute": LazyHandler("neuro_cognitive", "handle_neuro_compute"),
    "neuro.modulate": LazyHandler("neuro_cognitive", "handle_neuro_modulate"),
    "neuro.reset": LazyHandler("neuro_cognitive", "handle_neuro_reset"),
    "neuro.stats": LazyHandler("neuro_cognitive", "handle_neuro_stats"),
    # ── Metaplasticity ──
    "metaplasticity.apply": LazyHandler("neuro_cognitive", "handle_metaplasticity_apply"),
    "metaplasticity.batch": LazyHandler("neuro_cognitive", "handle_metaplasticity_batch"),
    "metaplasticity.plasticity": LazyHandler("neuro_cognitive", "handle_metaplasticity_plasticity"),
    "metaplasticity.decay": LazyHandler("neuro_cognitive", "handle_metaplasticity_decay"),
    "metaplasticity.stats": LazyHandler("neuro_cognitive", "handle_metaplasticity_stats"),
    # ── Global Workspace ──
    "workspace.propose": LazyHandler("neuro_cognitive", "handle_workspace_propose"),
    "workspace.state": LazyHandler("neuro_cognitive", "handle_workspace_state"),
    "workspace.history": LazyHandler("neuro_cognitive", "handle_workspace_history"),
    "workspace.stats": LazyHandler("neuro_cognitive", "handle_workspace_stats"),
    "workspace.ignite": LazyHandler("neuro_cognitive", "handle_workspace_ignite"),
    "workspace.pending": LazyHandler("neuro_cognitive", "handle_workspace_pending"),
    "workspace.ignitions": LazyHandler("neuro_cognitive", "handle_workspace_ignitions"),
    # ── Neuro Sensorium ──
    "sensorium.state": LazyHandler("neuro_cognitive", "handle_sensorium_state"),
    "sensorium.citta": LazyHandler("neuro_cognitive", "handle_sensorium_citta"),
    "sensorium.stats": LazyHandler("neuro_cognitive", "handle_sensorium_stats"),
    # ── Citta Introspection ──
    "citta.vector": LazyHandler("neuro_cognitive", "handle_citta_vector"),
    "citta.trajectory": LazyHandler("neuro_cognitive", "handle_citta_trajectory"),
    "citta.coherence": LazyHandler("neuro_cognitive", "handle_citta_coherence"),
    "consciousness.loop.status": LazyHandler("neuro_cognitive", "handle_consciousness_loop_status"),
    "guna.balance.status": LazyHandler("neuro_cognitive", "handle_guna_balance_status"),
    "meta.galaxy.overview": LazyHandler("neuro_cognitive", "handle_meta_galaxy_overview"),
    "possibility.explore": LazyHandler("neuro_cognitive", "handle_possibility_explore"),
    "knowledge_gap.run": LazyHandler("neuro_cognitive", "handle_knowledge_gap_run"),
    # ── MC Simulation Tools (Tier 2-4) ──
    "mc.surrogate": LazyHandler("simulation", "handle_mc_surrogate"),
    "mc.optimize": LazyHandler("simulation", "handle_mc_optimize"),
    "mc.rare_event": LazyHandler("simulation", "handle_mc_rare_event"),
    "mc.sde": LazyHandler("simulation", "handle_mc_sde"),
    "mc.superforecaster": LazyHandler("simulation", "handle_mc_superforecaster"),
    "simulation.introspect": LazyHandler("simulation", "handle_simulation_introspect"),
    "simulation.forecast": LazyHandler("simulation", "handle_simulation_forecast"),
    # ── Codebase Self-Model ──
    "codebase.scan": LazyHandler("codebase", "handle_codebase_scan"),
    "codebase.recall": LazyHandler("codebase", "handle_codebase_recall"),
    "codebase.structure": LazyHandler("codebase", "handle_codebase_structure"),
    "codebase.status": LazyHandler("codebase", "handle_codebase_status"),
    "codebase.find": LazyHandler("codebase", "handle_codebase_find"),
}
