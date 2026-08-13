# WhiteMagic v5 Operations Guide

This document covers export, backup, index health, and recovery workflows
for production deployments.

## Export

### Per-galaxy export (JSON)

```
wm(route='galaxy.export', args={"galaxy": "codex", "path": "/tmp/codex.json"})
```

Exports all memories in a galaxy to a JSON file. Non-destructive — the
store is unchanged.

### Per-galaxy backup (binary snapshot)

```
wm(route='galaxy.backup', args={"galaxy": "codex", "path": "/tmp/codex.wmbak"})
```

Creates a binary backup file containing serialized memory records. Faster
than JSON export for large galaxies. Restore with `galaxy.restore`.

### Snapshot (point-in-time)

```
wm(route='galaxy.snapshot', args={"galaxy": "codex"})
```

Creates an in-memory snapshot of a galaxy's current state. Used by
transactions for rollback support. Snapshots are ephemeral — use
`galaxy.backup` for persistent backups.

### Training data export

```
wm export-training-data --output training.jsonl --format jsonl
```

Exports collected self-play training samples as JSONL for LoRA
fine-tuning. Use `--include-negative` to also export failed verification
samples.

## Backup Strategy

### Recommended backup routine

1. **Daily**: `galaxy.backup` for each galaxy with data, or copy the LMDB
   directory while the server is stopped.
2. **Weekly**: Full `galaxy.export` to JSON for cross-version portability.
3. **Before upgrades**: Stop the server, copy the entire store directory
   (`~/.local/share/whitemagic/lmdb`), then upgrade.

### Cold backup (simplest)

```bash
# Stop the server, then:
cp -a ~/.local/share/whitemagic/lmdb /backup/lmdb-$(date +%Y%m%d)
# Restart the server
```

LMDB is a single mmap'd file — a file copy while the server is stopped is
a consistent snapshot.

### Hot backup (server running)

Use `galaxy.backup` per galaxy. This reads memories through the normal
store API and serializes them. The Tantivy index is not included —
rebuild it with `wm reindex` after restoring.

## Index Health

### Checking index health

```
wm doctor
```

The doctor checks:
- Tantivy index directory exists
- **Index consistency**: compares LMDB memory counts to Tantivy document
  counts per galaxy. Reports `[WARN]` for any galaxy with drift.
- **Index health**: reports failure count and last error from indexing
  operations since startup.

### Programmatic health check

```
wm(route='system.health')
```

Returns JSON with:
- `index_health`: `{successes, failures, degraded, last_error}`
- `index_consistency`: `{has_drift, total_lmdb, total_tantivy, drifted_galaxies[]}`
- `healthy`: `false` when index is degraded, drifted, or unavailable

When no search engine is configured (e.g. read-only proxy), reports
`index_health.status = "unavailable"` with `degraded: true`.

### Consistency model

Tantivy indexing is **best-effort**: an indexing failure does not roll
back the LMDB write. This means:

- LMDB is the source of truth.
- Tantivy can drift (stale entries, missing entries).
- Content that fails sanitization (binary garbage, null bytes) is
  intentionally skipped — this is not a failure.
- `IndexHealth.failures` tracks actual indexing errors (Tantivy writer
  failures, disk errors). Sanitization skips do not count as failures.

### Rebuilding the index

```bash
# Full rebuild (all galaxies)
wm reindex

# Filtered rebuild (specific galaxies only)
wm reindex --galaxy codex --galaxy research

# Dry run (report what would be indexed)
wm reindex --dry-run

# Skip the automatic backup of the current index
wm reindex --no-backup
```

The rebuild:
1. Backs up the existing index directory (unless `--no-backup`)
2. Deletes all documents (or only the selected galaxies' documents)
3. Re-indexes every memory from LMDB through the sanitization gate
4. Reports `scanned`, `indexed`, and `skipped` counts

## Recovery

### Corrupted LMDB entries

```bash
wm doctor --check-integrity
wm doctor --repair
```

The integrity check scans all galaxies for corrupted entries (invalid
msgpack, missing fields). Repair quarantines corrupted entries to a JSON
file and rebuilds secondary indexes.

### Map full (LMDB)

If the LMDB map is full, writes fail with `LMDB map full`. Grow the map:

```bash
wm doctor  # confirms the issue
```

The store auto-grows on open if needed, but manual recovery may be
required if the map size is exhausted during operation. Stop the server,
then use the recovery module to grow the map size and reopen.

### Tantivy index corruption

If the Tantivy index is corrupted (cannot open, search errors):

1. Stop the server
2. Delete or rename the tantivy directory:
   `rm -rf ~/.local/share/whitemagic/lmdb/tantivy`
3. Restart the server (`wm serve`) — a fresh index is created
4. Run `wm reindex` to populate it from LMDB

Or simply run `wm reindex` which backs up and rebuilds in one step.

### Restore from backup

```bash
# Stop the server
# Replace the store directory with the backup
cp -a /backup/lmdb-20260813 ~/.local/share/whitemagic/lmdb
# Restart and rebuild the index
wm serve &
wm reindex
```

### Galaxy restore from backup file

```
wm(route='galaxy.restore', args={"galaxy": "codex", "path": "/tmp/codex.wmbak", "confirm": true})
```

Restores a galaxy from a `.wmbak` file. This is a **destructive**
operation — it replaces all memories in the galaxy. Requires
`confirm: true`.

## Quick Reference

| Task | Command |
|------|---------|
| Health check | `wm doctor` |
| Integrity check | `wm doctor --check-integrity` |
| Repair corruption | `wm doctor --repair` |
| Rebuild search index | `wm reindex` |
| Rebuild specific galaxy | `wm reindex --galaxy codex` |
| Export training data | `wm export-training-data --output out.jsonl` |
| System health (MCP) | `wm(route='system.health')` |
| Galaxy health (MCP) | `wm(route='galaxy.health')` |
| Export galaxy (MCP) | `wm(route='galaxy.export', args={...})` |
| Backup galaxy (MCP) | `wm(route='galaxy.backup', args={...})` |
| Restore galaxy (MCP) | `wm(route='galaxy.restore', args={..., "confirm": true})` |
