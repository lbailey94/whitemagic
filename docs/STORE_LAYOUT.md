# Gen3 store layout

On-disk layout of a Gen3 `wm` store as observed on 2026-10-07 (10.2.0-alpha.5,
`main` `2a923b4`). Path resolution, disposable-store policy and migration rules
are in [`STORE_AND_DATA_HYGIENE.md`](STORE_AND_DATA_HYGIENE.md); this document
is the byte-level map: LMDB DBIs, sidecar files, observed sizes, backup
coverage and known gaps.

Default store: `~/.local/share/whitemagic/gen3` (resolution order:
`--store` → `$WM_STORE` → `.../gen3` → legacy `.../lmdb` →
`.../whitemagic` → `./gen3-store`, see `wm.rs::resolve_store_path`).

## 1. LMDB environment (`data.mdb`)

Opened with max 16 DBIs, file permissions `0600` (map size policy below).
Named DBIs created by `wm-gen3-core::store`:

| DBI | Contents |
|---|---|
| `records` | Evidence records (wire-encoded domain values) |
| `relations` | Relation edges (supersession/contradiction ancestry) |
| `postings` | Inverted-index postings |
| `embeddings` | Persisted projection vectors (Gate 9C) |
| `embed_cache` | Derived embedding cache (see `DERIVED_CACHE_POLICY.md`) |
| `nullifiers` | Burned capability nullifiers (mirrors the journal) |
| `receipts` | Commit/sweep receipts keyed by operation id |
| default (unnamed) | Meta keys: `__init__`, `__ver__`, `__rlm__`, `__epc__`, `__nrid_*`, `next_relation_id`, `sweep` |

`lock.mdb` is LMDB's lock file (also `0600`). The store format is versioned;
unknown/older formats refuse to open rather than migrating silently.

**Map size policy.** `store.rs::configured_map_size` reads `WM_MAP_SIZE_GB`;
the code default is **16 GiB** and the fleet service environment sets
**`WM_MAP_SIZE_GB=32`** (raised in the 10.2.0-alpha.5 ops wave; confirmed in
`~/.config/wm10-instances/opencode.env`). The 32 GiB setting is the operating
policy for managed stores; ad-hoc/local opens that do not set the variable get
16 GiB. The live main store's `data.mdb` was ~16 GiB on 2026-10-07 — i.e. at or
near the 16 GiB default ceiling — which is exactly why the managed services run
with 32 GiB.

## 2. Sidecars (flat files next to `data.mdb`)

| File | Written by | Contents / retention |
|---|---|---|
| `journal.jsonl` | kernel nullifier journal (`ops.rs`, `Journal`) | Append-only, write-ahead with fsync before mutation; alpha.5 recovers `seq` and repairs a truncated tail. No rotation/pruning today |
| `uuid_index.jsonl` | `ops.rs::bind_uuid` | JSONL `{uuid, record_id}` mapping for migrated Gen2 identities; append-only |
| `session_log.jsonl` | harness `bridge.rs` session lanes | Append-only session checkpoints/turns (`wm session checkpoint`); grows with use |
| `receipts/` | System 0.5/decision tools | Individual `decision-*.json`, `shortlist-*.json`, `deliberation-*.json`, `*.outcome.json`, plus `outcomes.jsonl`; never pruned |
| `quarantine.jsonl` | migration | Damaged Gen2 records with structured reasons (Gate 9D) |
| `migration_receipt.json`, `session_migration_receipt.json`, `evidence_backfill_receipt.json` | migration/backfill | One-shot receipts, overwritten per run |
| `dream.jsonl`, `dream_insights.jsonl` | `wm dream` | Dream cycle log / insights; no rotation |
| `galaxy_6d.json`, `galaxy.html` | `wm galaxy` | Visualization outputs, regenerated on demand |
| `vault.jsonl`, `geneseed_vault.jsonl` | `wm vault` / apotheosis | Geneseed vault state |
| `peers.json`, `mesh_node_key.bin`, `mandala_gate_key.bin` | mesh/mandala | Peer directory, Ed25519 mesh key, gate signing key (key material is `0600`) |
| `sentinel-circuit-breaker.json`, `sample_pass.json` | sentinel/mandala | Durable guard state and sample pass |
| `lock.mdb` | LMDB | Lock file |

The repository's `receipts/` directory (verdicts/benchmarks) is **not** the
store `receipts/` directory; do not conflate them.

## 3. Observed sizes (2026-10-07 snapshot, not a trend)

| Path | Size |
|---|---|
| `gen3/data.mdb` | ~16 GiB (main store) |
| `gen3/journal.jsonl` | ~47 MB |
| `gen3/uuid_index.jsonl` | ~820 KB |
| `gen3/session_log.jsonl` | ~8 KB |
| `gen3/receipts/` | ~328 KB across 76 files |
| `gen3-project/opencode/data.mdb` | ~172 MB |
| `gen3-projects/opencode/session_log.jsonl` | ~29 MB |
| `gen3-projects/opencode/journal.jsonl` | ~26 MB |
| `vault/` (`tacit_vault.db`, `vault_vectors.bin`, `sync_state.json`) | ~1.1 GB |

These are point-in-time measurements (`du -sh`) on one host; there is no
time-series or dashboard for store growth (see §6). Re-measure with:
`du -sh <store>/data.mdb <store>/*.jsonl <store>/receipts`.

## 4. Backup coverage (fleet ops, outside the binary)

The alpha.5 ops wave restored the trust/backup chain for the managed fleet
(CHANGELOG 10.2.0-alpha.5, "Fleet ops"): **Gen3 store + `gen3-projects/opencode`
+ vault** are archived (tar + sha256, integrity-tested) and kept on the SD card
with **keep-2** retention (only the two newest archives survive pruning). The
main store's LMDB map was raised to 32 GiB as part of the same wave. An
archive-and-verify run was observed in progress on 2026-10-07 under
`/media/lucas/SD_CARD1/whitemagic-archive/20261007` (`wmdata-live.tar.zst` +
`.sha256`, `zstd -t` check). These scripts are fleet assets, not part of this
repository — treat the CHANGELOG entry as the in-repo reference.

## 5. Retention today

- LMDB pages are reused by LMDB itself, but there is **no compaction, vacuum,
  or GC pass** for the store (no `mdb_copy` rewrite, no page reclaim job).
- Sidecar JSONLs are append-only; only the journal has a (repair, not prune)
  policy today.
- The only retention policy in force is the SD **keep-2** archive rotation.

## 6. Known gaps

1. **No compaction yet.** A long-lived store only grows; the map ceiling is the
   hard stop. The 16 GiB default has already been reached by the live main
   store, which is why managed services run at 32 GiB.
2. **Growth is unmeasured.** There is no per-store size metric, no growth rate,
   and no alert before `MDB_MAP_FULL`; sizes above are manual snapshots.
3. **Full hydration on open** was flagged as a load risk in ops notes; it is
   not quantified here.
4. Backup verification is manual/fleet-side; the binary has no `backup` /
   `restore` command in the 10.2 alpha line.
