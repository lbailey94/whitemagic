---
name: wm-export
description: "Export memories, audit exports, and broadcast across the mesh"
version: 1.0.0
author: WhiteMagic Labs
license: MIT
platforms: [linux, macos, windows]
metadata:
  whitemagic:
    gana: gana_wings
    tools: [export_memories, audit_export, galaxy_backup, galaxy_restore, mesh_broadcast, mesh_status]
    tags: [export, backup, restore, mesh, broadcast, deployment]
---

# Export & Deployment

Export memories for transfer, audit exports for security, backup/restore galaxies, and broadcast across the mesh network.

## When to Use

- Exporting memories for backup or transfer
- Auditing an export for sensitive content
- Backing up a galaxy before major changes
- Restoring a galaxy from backup
- Broadcasting status across mesh nodes
- Checking mesh network status

## How to Invoke

```python
# Export memories
wm(route="gana_wings.export_memories", args={"galaxy": "...", "format": "arrow"})

# Audit an export
wm(route="gana_wings.audit_export", args={"export_id": "..."})

# Galaxy backup
wm(route="gana_wings.galaxy_backup", args={"galaxy": "..."})

# Galaxy restore
wm(route="gana_wings.galaxy_restore", args={"backup_file": "..."})

# Mesh broadcast
wm(route="gana_wings.mesh_broadcast", args={"message": "..."})

# Mesh status
wm(route="gana_wings.mesh_status", args={})
```

## Export Formats

- **Arrow** — Apache Arrow format (32x faster than JSON, default)
- **JSON** — Human-readable, universal compatibility
- **SQLite** — Direct database export
