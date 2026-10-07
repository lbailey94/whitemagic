# Receipt — V9 Retirement Pilot (neon) + Census

Date: 2026-10-07 · Operator: opencode (migration wave) · Status: **PASS**
Worktree: `/home/lucas/Desktop/front burner/WHITEMAGIC/worktrees/wt-v9pilot`
(branch `feat/v9-pilot-migration`, HEAD `ef623fbd5e80d64a47c3335e99a34ea3b9bf7511`,
version `10.2.0-alpha.6`).
Runbook: `docs/V9_RETIREMENT_PILOT.md`. Raw logs/receipts: `/tmp/wm-v9-pilot/`.

## Instrument

- Binary: `/home/lucas/.local/bin/wm10` — `wm 10.2.0-alpha.6`, sha256
  `fcd7f5a0f0353a482c85ba04b0fe7cd0d7e3db599947f9182ccdce58575819aa`.
- The worktree ships source only (no `target/`), so the installed alpha.6
  build of the same workspace version was used as `target/release/wm10` would
  have been. No code was edited.
- v9 side: live `wm9 9.3.4` `wm-serve@neon.service` MCP endpoint,
  `http://127.0.0.1:18791/mcp`, read-only calls (`initialize`,
  `memory.search`, `memory.read`). The unit was never stopped.

## Safety

- `ss -tnp | grep 18791` → no established connections before the copy.
- Source `data.mdb` sha256 before/after copy:
  `dbcbdece5c38baeddc8f6b74dce319fdd843b7087696477f30386b06d4e34a09`
  identical for live-before, live-after and the copy → consistent snapshot.
- Live neon `data.mdb` later changed (`46a6da4d…`) while the copy stayed
  frozen → copy-based migration was the right call.
- All dry-runs/migrations on other stores opened the live LMDB read-only
  (`Gen2Reader`: `READ_ONLY | NO_LOCK`); no writes to any v9 store.
- Pilot target `data.mdb` hash before/after dry run identical
  (`d3721acf…`) → store state untouched by dry-run.

## Exact flags used

```
wm10 init --store /tmp/wm-v9-pilot/neon-gen3
wm10 migrate --dry-run --source /tmp/wm-v9-pilot/neon-copy/lmdb \
  --store /tmp/wm-v9-pilot/neon-gen3 \
  --receipt-file /tmp/wm-v9-pilot/neon-gen3-dryrun-receipt.json
wm10 migrate --source /tmp/wm-v9-pilot/neon-copy/lmdb \
  --store /tmp/wm-v9-pilot/neon-gen3
wm10 recall --store /tmp/wm-v9-pilot/neon-gen3 "<query>" --limit 10
wm10 status  --store /tmp/wm-v9-pilot/neon-gen3
wm10 galaxy list --store /tmp/wm-v9-pilot/neon-gen3
wm10 census <store>/lmdb            # heritage, vault (read-only)
```

Missing-target refusal (dry run, exit 1, nothing written):

```
Migration dry-run refused: compat error: target missing: <dir> does not
contain data.mdb; dry-run never creates the target store
```

## Migration receipts (neon)

Source `/tmp/wm-v9-pilot/neon-copy/lmdb`; target `/tmp/wm-v9-pilot/neon-gen3`.

| Field | Dry-run | Live | Idempotency rerun |
|---|---|---|---|
| `total_scanned` (episodic) | 47 | 47 | 47 |
| `migrated_count` | 47 | 47 | 0 |
| `duplicate_skipped` | 0 | 0 | 47 |
| `quarantined_count` | 0 | 0 | 0 |
| `galaxy_total_scanned` | 5,989 | 5,989 | 5,989 |
| `galaxy_migrated` | 1,847 | 1,845 | 0 |
| `galaxy_duplicates` | 0 | 2 | 1,847 |
| `galaxy_decode_skipped` | 0 | 0 | 0 |
| `galaxy_quarantined` | 0 | 0 | 0 |
| `target_epoch` | 6 | 1,898 | 1,898 |
| `receipt_digest` | `c49ed828a2e319ad3f4c01ef986bcd208808615909e05d4adba3f233baada9bd` | `1440c27cb4ebcd04d17edfe3137f79907b748bb848342f268658a4acf4dcf868` | `d4ecf9a197bd5772…` |
| `dry_run` | true | false | false |

Session lane (parallel, not part of the 1,898 records): 151 turns / 19
sessions migrated; rerun 0 migrated, 151 duplicates. Post-rerun
`wm10 status`: `Epoch 1898 · Records Count 1898`.

Per-type (live receipt): episodic `system_event` 47/0 dup; galaxy
`codex` 74, `dreams` 173 + 2 dup, `research` 1,425, `sessions` 151,
`telemetry` 22 (sums to `galaxy_migrated` 1,845 — the 151 `sessions` rows are
already inside it); non-memory-lane skips `associations` 1,785,
`embeddings` 1,560, `karma` 797. `wm10 galaxy list`: codex 143
(74 + 47 episodic + 22 telemetry), dreams 173, research 1,425, sessions 151,
guide 6. The 151 `session_log.jsonl` turns are the session lane's projection
of the same sessions DBI and are not added to the record count.

## Verification

1. **Counts:** Gen3 total 1,898 = 1,845 galaxy + 47 episodic + 6 seeded guide;
   every migrated type reconciles per galaxy (§4 of the runbook).
2. **Recall parity (10 queries, top-10, content-presence):** top-1 exact 3/10
   (`startForce`, `starvation`, `minimap`); average exact-content overlap
   2.8/10. `conformal`: v9 10 hits all `bm25_score=0.0` (vector-only), Gen3
   0 — engine-mode difference, not data loss.
3. **Sampled reads (5/5 byte-identical):** v9 `memory.read` vs Gen3 recall —
   codex `021b7cba…` → #54; sessions `87af2fb4…` → #1803; sessions
   `2e41c070…` → #1751; dreams `af379688…` → #251 (twin #1485, sha256
   `82cf9026525c4138` both sides); codex `b0a67f27…` → #1824.
4. **Idempotency:** rerun migrated 0 / deduped all, record count unchanged.

## Census matrix (read-only dry-run migrations into /tmp targets)

| Store | data.mdb | Ep | Galaxy migr (scanned) | Non-mem skip | Decode/Quar | Turns (sessions) |
|---|---|---|---|---|---|---|
| neon | 16 MB | 47 | 1,847 (5,989) | 4,142 | 0 / 0 | 151 (19) |
| default | 560 KB | 0 | 38 (338) | 300 | 0 / 0 | 0 |
| whitemagic-site | 232 KB | 2 | 24 (215) | 191 | 0 / 0 | 4 (1) |
| planning | 1.1 MB | 16 | 60 (1,307) | 1,247 | 0 / 0 | 38 (5) |
| valkyrie | 28 MB | 431 | 471 (3,211) | 2,740 | 0 / 0 | 56 (26) |
| opencode | 242 MB | 240 | 58,814 (61,510) | 2,696 | 0 / 0 | 58,763 (18,037) |
| heritage | 1.9 GB | 1 | 56,456 (58,445) | 1,989 | 0 / 0 | 28,080 (28,023) |
| vault | 2.4 GB | 0 | 244,815 (341,303) | 96,488 | 0 / 0 | 97,176 (97,176) |
| wmv9 | 1.1 GB | 19,879 | 17,204 (1,622,988) | 1,605,784 | 0 / 0 | 1,188 (136) |

`wm10 census` (episodic lane) on heritage: 1 record, 100% integrity;
vault: 0 records — their bulk is galaxy DBIs. No hash mismatches anywhere.
Dry-run receipt digests: neon `c49ed828…`, default `49cf03d6…`,
heritage `9a48c2cd…`, planning `bf3a8175…`, site `3b2af058…`,
vault `9c326e92…`, valkyrie `93870926…`, wmv9 `5170cdb2…`,
opencode `bb47c2e1…`.

## Findings / gaps

1. Dry run writes `<target>/session_migration_receipt.json` (store `data.mdb`
   untouched) — not fully side-effect-free; needs a `dry_run` guard.
2. Dry run over-predicts `galaxy_migrated` when the source has exact
   duplicates (neon 1,847 vs 1,845 + 2) — intra-run dedupe is not simulated.
3. Gen3 stores have no vector half in this pilot; lexical-only parity proven,
   semantic parity not.
4. v9 UUIDs are not preserved by migration; reconciliation must be by content
   (recommend a v9-uuid index in the receipt).
5. Non-memory lanes (`karma`, `associations`, `embeddings`, …) are deliberately
   not migrated; wmv9 (1.6M rows) and vault (96k rows) need a keep/drop
   decision.
6. Fixed 17-DBI scan list: unknown DBIs are invisible; add DBI enumeration
   before final cutover.
7. `session_migration_receipt.json` is overwritten by a rerun; snapshot
   evidence receipts after the live run.

## Blockers

None for the pilot path. Items 1–2 are tool hygiene; 3, 5, 6 must be resolved
before declaring recall/coverage parity for the remaining stores.

## Artifacts

`/tmp/wm-v9-pilot/`: `neon-copy/` (frozen source copy, data.mdb
`dbcbdece…`), `neon-gen3/` (pilot store), `dryrun.log`, `migrate.log`,
`neon-gen3-dryrun-receipt.json`, `neon-gen3-rerun-receipt.json`,
`parity.py`, `parity-run.log`, `parity-results.json`, `samples.py`,
`samples-results.log`, `<store>-dryrun-receipt.json`, `<store>-dryrun.log`,
`heritage-census.log`, `vault-census.log`, `disposition/`.
