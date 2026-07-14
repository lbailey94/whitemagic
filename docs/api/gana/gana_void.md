# Gana: gana_void

**50 tools** routed through this Gana.

| Tool | Category | Safety | Description |
|------|----------|--------|-------------|
| [galactic.dashboard](../tools/galactic.dashboard.md) | introspection | read | Rich Galactic Map dashboard — zone counts, crown jewels, type distribution, rete |
| [galactic_dashboard](../tools/galactic_dashboard.md) | system | read | Dispatch-routable WhiteMagic tool 'galactic_dashboard'. |
| [galaxy.backup](../tools/galaxy.backup.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.backup'. |
| [galaxy.canonical_taxonomy](../tools/galaxy.canonical_taxonomy.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.canonical_taxonomy'. |
| [galaxy.create](../tools/galaxy.create.md) | system | write | Create a new galaxy (project-scoped memory database). Each galaxy gets its own S |
| [galaxy.delete](../tools/galaxy.delete.md) | system | write | Remove a galaxy from the registry. The database file is preserved on disk. |
| [galaxy.export](../tools/galaxy.export.md) | system | read | Export memories from a galaxy as Arrow IPC bytes for cross-instance sharing. Use |
| [galaxy.export_tutorial](../tools/galaxy.export_tutorial.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.export_tutorial'. |
| [galaxy.import](../tools/galaxy.import.md) | system | write | Import memories from Arrow IPC bytes into the local memory system. Memories are  |
| [galaxy.ingest](../tools/galaxy.ingest.md) | system | write | Ingest files from a directory into a galaxy's memory store. Reads text files mat |
| [galaxy.lineage](../tools/galaxy.lineage.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.lineage'. |
| [galaxy.lineage_stats](../tools/galaxy.lineage_stats.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.lineage_stats'. |
| [galaxy.list](../tools/galaxy.list.md) | system | read | List all known galaxies with metadata, memory counts, and active status. |
| [galaxy.list_shared](../tools/galaxy.list_shared.md) | system | read | List all galaxies shared with a user. Shared galaxies have a 'shared' tag and po |
| [galaxy.list_types](../tools/galaxy.list_types.md) | system | read | List all registered cognitive galaxy types with descriptions, colors, and decay  |
| [galaxy.merge](../tools/galaxy.merge.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.merge'. |
| [galaxy.migrate](../tools/galaxy.migrate.md) | system | write | Migrate a memory from one cognitive galaxy to another. Useful when a memory's co |
| [galaxy.package](../tools/galaxy.package.md) | system | read | Create a portable cross-AI galaxy package from a snapshot. Wraps the snapshot wi |
| [galaxy.receive](../tools/galaxy.receive.md) | system | read | Receive and import a cross-AI galaxy package. Verifies package integrity (conten |
| [galaxy.restore](../tools/galaxy.restore.md) | system | read | Restore a galaxy from a snapshot created by galaxy.snapshot. Can restore into th |
| [galaxy.route](../tools/galaxy.route.md) | system | read | Determine which cognitive galaxy a memory belongs to based on the source subsyst |
| [galaxy.search_multi](../tools/galaxy.search_multi.md) | memory | read | Search across multiple galaxies in parallel. Executes FTS5 queries against each  |
| [galaxy.share](../tools/galaxy.share.md) | system | write | Share a galaxy with another user by creating a registry entry that points to the |
| [galaxy.snapshot](../tools/galaxy.snapshot.md) | system | read | Create a full snapshot of a galaxy — memories, 6D coordinates, associations, and |
| [galaxy.stats](../tools/galaxy.stats.md) | system | read | Get statistics for a specific cognitive galaxy — memory count, average importanc |
| [galaxy.status](../tools/galaxy.status.md) | system | read | Get overall galaxy manager status — active galaxy, total count, registry path. |
| [galaxy.switch](../tools/galaxy.switch.md) | system | write | Switch the active galaxy. All subsequent memory operations (search, create, reca |
| [galaxy.sync](../tools/galaxy.sync.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.sync'. |
| [galaxy.taxonomy](../tools/galaxy.taxonomy.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.taxonomy'. |
| [galaxy.transfer](../tools/galaxy.transfer.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.transfer'. |
| [galaxy.use](../tools/galaxy.use.md) | system | read | Dispatch-routable WhiteMagic tool 'galaxy.use'. |
| [garden_activate](../tools/garden_activate.md) | garden | write | Activate a consciousness garden |
| [garden_browse](../tools/garden_browse.md) | system | read | Dispatch-routable WhiteMagic tool 'garden_browse'. |
| [garden_health](../tools/garden_health.md) | garden | read | Check garden health metrics |
| [garden_list_files](../tools/garden_list_files.md) | system | write | Dispatch-routable WhiteMagic tool 'garden_list_files'. |
| [garden_list_functions](../tools/garden_list_functions.md) | system | write | Dispatch-routable WhiteMagic tool 'garden_list_functions'. |
| [garden_map_system](../tools/garden_map_system.md) | system | read | Dispatch-routable WhiteMagic tool 'garden_map_system'. |
| [garden_resolve](../tools/garden_resolve.md) | system | read | Dispatch-routable WhiteMagic tool 'garden_resolve'. |
| [garden_resonance](../tools/garden_resonance.md) | system | read | Dispatch-routable WhiteMagic tool 'garden_resonance'. |
| [garden_search](../tools/garden_search.md) | system | read | Dispatch-routable WhiteMagic tool 'garden_search'. |
| [garden_stats](../tools/garden_stats.md) | system | read | Dispatch-routable WhiteMagic tool 'garden_stats'. |
| [garden_status](../tools/garden_status.md) | garden | read | Get garden activation status |
| [garden_synergy](../tools/garden_synergy.md) | system | read | Dispatch-routable WhiteMagic tool 'garden_synergy'. |
| [oms.export](../tools/oms.export.md) | system | read | Dispatch-routable WhiteMagic tool 'oms.export'. |
| [oms.import](../tools/oms.import.md) | system | read | Dispatch-routable WhiteMagic tool 'oms.import'. |
| [oms.inspect](../tools/oms.inspect.md) | system | read | Dispatch-routable WhiteMagic tool 'oms.inspect'. |
| [oms.list](../tools/oms.list.md) | system | read | Dispatch-routable WhiteMagic tool 'oms.list'. |
| [oms.price](../tools/oms.price.md) | system | read | Dispatch-routable WhiteMagic tool 'oms.price'. |
| [oms.status](../tools/oms.status.md) | system | read | Dispatch-routable WhiteMagic tool 'oms.status'. |
| [oms.verify](../tools/oms.verify.md) | system | read | Dispatch-routable WhiteMagic tool 'oms.verify'. |
