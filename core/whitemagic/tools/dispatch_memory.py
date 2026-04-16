"""dispatch_memory.py — Memory, search, export/import, and galaxy tools.

Domain slice imported by dispatch_table.py.
"""
from collections.abc import Callable
from typing import Any

from whitemagic.tools.dispatch_core import LazyHandler

DISPATCH_MEMORY: dict[str, Callable[..., dict[str, Any]]] = {
    # --- Search Aliases ---
    "search_query": LazyHandler("memory", "handle_search_memories"),

    # --- Memory CRUD ---
    "create_memory": LazyHandler("memory", "handle_create_memory"),
    "fast_read_memory": LazyHandler("memory", "handle_fast_read_memory"),
    "batch_read_memories": LazyHandler("memory", "handle_batch_read_memories"),
    "search_memories": LazyHandler("memory", "handle_search_memories"),
    "memory_search": LazyHandler("memory", "handle_search_memories"),
    "memory_read": LazyHandler("misc", "handle_read_memory"),
    "memory_update": LazyHandler("misc", "handle_update_memory"),
    "memory_delete": LazyHandler("misc", "handle_delete_memory"),

    # --- Memory Aliases ---
    "read_memory": LazyHandler("misc", "handle_read_memory"),
    "list_memories": LazyHandler("misc", "handle_list_memories"),
    "update_memory": LazyHandler("misc", "handle_update_memory"),
    "delete_memory": LazyHandler("misc", "handle_delete_memory"),

    # --- Export/Import ---
    "export_memories": LazyHandler("export_import", "handle_export_memories"),
    "import_memories": LazyHandler("export_import", "handle_import_memories"),

    # --- Galaxy Management ---
    "galaxy.create": LazyHandler("galaxy", "handle_galaxy_create"),
    "galaxy.switch": LazyHandler("galaxy", "handle_galaxy_switch"),
    "galaxy.list": LazyHandler("galaxy", "handle_galaxy_list"),
    "galaxy.status": LazyHandler("galaxy", "handle_galaxy_status"),
    "galaxy.ingest": LazyHandler("galaxy", "handle_galaxy_ingest"),
    "galaxy.delete": LazyHandler("galaxy", "handle_galaxy_delete"),
    "galaxy.backup": LazyHandler("backup", "handle_galaxy_backup"),
    "galaxy.restore": LazyHandler("backup", "handle_galaxy_restore"),

    # --- v15.3 Galactic Telepathy ---
    "galaxy.transfer": LazyHandler("galaxy", "handle_galaxy_transfer"),
    "galaxy.merge": LazyHandler("galaxy", "handle_galaxy_merge"),
    "galaxy.sync": LazyHandler("galaxy", "handle_galaxy_sync"),

    # --- v15.4 Phylogenetic Lineage ---
    "galaxy.lineage": LazyHandler("galaxy", "handle_galaxy_lineage"),
    "galaxy.taxonomy": LazyHandler("galaxy", "handle_galaxy_taxonomy"),
    "galaxy.lineage_stats": LazyHandler("galaxy", "handle_galaxy_lineage_stats"),

    # --- v14.0 Living Graph ---
    "hybrid_recall": LazyHandler("living_graph", "handle_hybrid_recall"),
    "graph_topology": LazyHandler("living_graph", "handle_graph_topology"),
    "graph_walk": LazyHandler("living_graph", "handle_graph_walk"),
    "surprise_stats": LazyHandler("living_graph", "handle_surprise_stats"),
    "entity_resolve": LazyHandler("living_graph", "handle_entity_resolve"),
    "community.propagate": LazyHandler("living_graph", "handle_community_propagate"),
    "community.status": LazyHandler("living_graph", "handle_community_status"),
    "community.health": LazyHandler("living_graph", "handle_community_health"),

    # --- Galactic Dashboard ---
    "galactic.dashboard": LazyHandler("galactic_dashboard", "handle_galactic_dashboard"),

    # --- Memory Governance ---
    "memory.lifecycle": LazyHandler("governance", "handle_memory_lifecycle"),
    "memory.lifecycle_sweep": LazyHandler("governance", "handle_lifecycle_sweep"),
    "memory.lifecycle_stats": LazyHandler("governance", "handle_lifecycle_stats"),
    "memory.consolidate": LazyHandler("governance", "handle_consolidate_memories"),
    "memory.consolidation_stats": LazyHandler("governance", "handle_consolidation_stats"),

    # --- OMS (Optimized Memory States) ---
    "oms.export": LazyHandler("oms", "handle_oms_export"),
    "oms.import": LazyHandler("oms", "handle_oms_import"),
    "oms.inspect": LazyHandler("oms", "handle_oms_inspect"),
    "oms.verify": LazyHandler("oms", "handle_oms_verify"),
    "oms.price": LazyHandler("oms", "handle_oms_price"),
    "oms.list": LazyHandler("oms", "handle_oms_list"),
    "oms.status": LazyHandler("oms", "handle_oms_status"),

    # --- Memory Rent ---
    "memory.rent": LazyHandler("economy", "handle_rent_galaxy"),

    # --- Hologram ---
    "view_hologram": LazyHandler("misc", "handle_view_hologram"),

    # --- CyberBrain: Salience, Retention ---
    "salience.spotlight": LazyHandler("cyberbrain", "handle_salience_spotlight"),
    "memory.retention_sweep": LazyHandler("cyberbrain", "handle_retention_sweep"),

    # --- Simple Aliases ---
    "remember": LazyHandler("aliases", "handle_remember"),
    "recall": LazyHandler("aliases", "handle_recall"),
}
