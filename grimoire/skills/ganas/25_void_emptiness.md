---
name: wm-galaxy
description: "Galaxy lifecycle management — create, transfer, merge, sync, lineage, taxonomy"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_void
    tools: [galactic_dashboard, galactic_dashboard, galaxy_backup, galaxy_canonical_taxonomy, galaxy_create, galaxy_export_tutorial, galaxy_lineage, galaxy_merge, galaxy_sync, galaxy_taxomony, galaxy_transfer, oms_export, oms_import, oms_inspect]
    tags: [galaxy, void, create, transfer, merge, sync, lineage, taxonomy, dashboard, oms]
---

# Galaxies & Stillness

Manage the 10-galaxy memory taxonomy, create and merge galaxies, transfer memories between galaxies, sync across instances, and inspect the galactic dashboard.

## When to Use

- Viewing the galactic dashboard (all galaxies at a glance)
- Creating a new galaxy for a specialized domain
- Transferring memories between galaxies
- Merging galaxies with conflict resolution
- Syncing galaxies across instances
- Checking galaxy lineage and history
- Getting the canonical taxonomy
- Exporting tutorial galaxy content

## How to Invoke

```python
# Galactic dashboard
wm(thought="show me the galaxy dashboard")
wm(route="gana_void.galactic_dashboard", args={})

# Create a galaxy
wm(route="gana_void.galaxy_create", args={"name": "...", "type": "..."})

# Transfer memories
wm(route="gana_void.galaxy_transfer", args={"source": "...", "target": "...", "memory_ids": [...]})

# Merge galaxies
wm(route="gana_void.galaxy_merge", args={"source": "...", "target": "..."})

# Sync
wm(route="gana_void.galaxy_sync", args={"galaxy": "..."})

# Lineage
wm(route="gana_void.galaxy_lineage", args={"galaxy": "..."})

# Canonical taxonomy
wm(route="gana_void.galaxy_canonical_taxonomy", args={})
```

## 10-Galaxy Taxonomy

`aria` · `citta` · `codex` · `journals` · `dreams` · `research` · `sessions` · `substrate` · `tutorial` · `universal`
