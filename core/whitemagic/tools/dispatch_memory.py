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
}
