# V9 Retirement — Pilot & Per-Store Cutover Runbook

Status: **PILOT COMPLETE (neon)** · 2026-10-07 · tool `wm10 10.2.0-alpha.6`
Scope: retire the `wm-serve@*` v9/Gen2 LMDB instances by migrating each project
store into a per-project Gen3 store. Evidence: `receipts/V9_PILOT_MIGRATION_2026-10-07.md`.

## 1. Outcome

- `neon` migrated from a hash-guarded copy into a pilot Gen3 store:
  47 episodic records + 1,845 galaxy rows ingested (the galaxy rows include
  the 151 session rows; the 151 session turns are a parallel lane in
  `session_log.jsonl`, not part of the Gen3 record count).
  0 decode skips, 0 quarantine, 2 by-design exact-content duplicates.
- Gen3 pilot holds 1,898 records = 1,845 galaxy + 47 episodic + 6 seeded
  starter-guide.
- Per-galaxy counts reconcile exactly with the migration receipt.
- Parity (hybrid v9 vs lexical Gen3): 3/10 top-1 exact, avg 2.8/10 content
  overlap; 5/5 sampled records byte-identical by exact `memory.read` vs
  Gen3 recall.
- Idempotent rerun: 0 migrated; 1,847 galaxy and 47 episodic substrate
  duplicates, plus 151 session-turn duplicates in the session lane; record
  count unchanged at 1,898.

## 2. Invariants

1. **Migrate from a copy, never a live store.** Live stores drift (neon's
   `data.mdb` changed during this pilot); the copy is the migration input.
2. **One writer per checkout.** `sangha claims` before touching shared trees.
3. **No code edits during a migration run.** Tool gaps are reported, not patched
   mid-flight (see §6).
4. **Dry-run first** on the copy; capture both receipts.
5. **The v9 store never moves or mutates.** Cutover only changes which binary
   and store the serving unit points at; rollback is re-enabling the unit.
6. Do not delete v9 stores until the rollback window (≥2 nightly backups) closes.

## 3. Per-store runbook

Let `<name>` be the instance, `<store>` its v9 root (`--store` path in
`~/.config/wm/instances/<name>.env`; LMDB lives in `<store>/lmdb`), `<port>` its
`WM_PORT`, `<target>` the Gen3 store (e.g. `/srv/wm-gen3/<name>` or any durable
path).

### 3.0 Preflight

- `systemctl --user status wm-serve@<name>` — confirm the unit and store path.
- `ss -tnp | grep <port>` — must show **no ESTABLISHED clients** before copying.
- `df -h /` — keep ≥20 GB free (copy ≈ `data.mdb` + target growth).
- Record `sha256sum <store>/lmdb/data.mdb` as the source-of-record hash.

### 3.1 Quiesce

- For the copy window: absence of connected clients plus a stable source hash
  is enough; the service may keep running (the pilot did exactly this).
- For the **final flip** perform a maintenance window: notify consumers, stop
  or drain writers, confirm no established connections, and take the copy while
  quiesced so "copy" == "final v9 state".

### 3.2 Copy (hash-guarded)

```bash
S=/home/lucas/wm-data/WMdata/projects/<name>   # or the env's true store path
C=/tmp/wm-v9-pilot/<name>-copy
H1=$(sha256sum "$S/lmdb/data.mdb" | cut -d' ' -f1)
cp -a "$S" "$C"
H2=$(sha256sum "$S/lmdb/data.mdb" | cut -d' ' -f1)
H3=$(sha256sum "$C/lmdb/data.mdb" | cut -d' ' -f1)
[ "$H1" = "$H2" ] && [ "$H1" = "$H3" ] || echo "UNSTABLE — retry"
```

### 3.3 Initialize target

```bash
wm10 init --store <target>          # seeds starter guide: 6 records
```

The starter-guide 6 records are expected and count toward Gen3 totals.

### 3.4 Dry-run census (target must already exist)

```bash
wm10 migrate --dry-run --source "$C/lmdb" --store <target> \
  --receipt-file /tmp/wm-v9-pilot/<name>-dryrun-receipt.json
```

- Refusal proof: a missing target exits 1 with
  `target missing: <dir> does not contain data.mdb`.
- Review `galaxy_decode_skipped`, `galaxy_quarantined`, `non_memory_lane`
  skips and the full `by_record_type` table before proceeding.
- **Known tool gaps (do not treat dry-run as file-system-pure):**
  - the dry run still writes `<target>/session_migration_receipt.json`
    (store `data.mdb` is untouched);
  - the dry run does not simulate intra-run exact-duplicate collapse, so it
    over-predicts `migrated` (neon: predicted 1,847 galaxy rows; actual
    1,845 + 2 duplicates).

### 3.5 Live migration

```bash
wm10 migrate --source "$C/lmdb" --store <target>
```

Writes `<target>/migration_receipt.json`, `session_migration_receipt.json`,
`session_log.jsonl`, `uuid_index.jsonl`, `journal.jsonl`. No writes to the
source.

### 3.6 Verify (cutover gate)

1. `wm10 status --store <target>` — epoch == record count.
2. `wm10 galaxy list --store <target>` — reconcile each galaxy against the
   receipt. Mapping used by migration:
   `codex→codex, journals→journals, dreams→dreams, research→research,
   sessions→sessions, universal→universal, tutorial→guide,
   substrate|aria|citta→codex`, unmapped (e.g. `telemetry`) → `codex`.
   Episodic records also land in `codex`. Expect +6 guide.
3. Recall parity spot check, 10 queries:
   - v9 side (read-only): MCP `memory.search` against
     `http://127.0.0.1:<port>/mcp` (JSON-RPC POST) — or
     `wm10 serve --legacy-store "$C/lmdb"` for a legacy mount.
   - Gen3 side: `wm10 recall --store <target> "<query>" --limit 10`.
   - Compare **content presence**, not ranking (engines differ).
4. 5 sampled records: v9 `memory.read` exact content vs Gen3 recall by a
   distinctive token; require byte equality. Note: v9 UUIDs are *not*
   preserved by migration (§6.2), so find the Gen3 twin by content.
5. Idempotency: rerun `wm10 migrate` with `--receipt-file` outside the store;
   require `migrated == 0` and an unchanged record count.

### 3.7 Flip clients

- Preferred: repoint the `wm-serve@<name>` unit `ExecStart` to the wm10 Gen3
  server for `<target>` (same port, so client configs survive), e.g.
  `wm10 serve --store <target> --transport sse --bind 127.0.0.1:<port> --profile curated`.
  Verify the `wm10 serve` flag set for the pinned version; wm9's `--profile`
  values and route surface differ.
- Flip one consumer at a time; keep the v9 unit running until the Gen3
  endpoint passes a client smoke test.

### 3.8 Stop unit

```bash
systemctl --user stop wm-serve@<name>
# disable only after the rollback window closes
```

### 3.9 Rollback

- Stop the Gen3 server and `systemctl --user start wm-serve@<name>` — the v9
  store is untouched, so this is instant.
- If the Gen3 store took partial writes, discard it and re-run from a fresh
  copy (migration is additive + idempotent). Never write back into v9.

## 4. Neon pilot results

Source: `/home/lucas/wm-data/WMdata/projects/neon/lmdb` (`data.mdb` 16 MB,
sha256 `dbcbdece…` at copy time). Target: `/tmp/wm-v9-pilot/neon-gen3`.

| Metric | Dry-run | Live | Rerun |
|---|---|---|---|
| Episodic scanned / migrated | 47 / 47 | 47 / 47 | 47 / 0 (47 dup) |
| Galaxy scanned | 5,989 | 5,989 | 5,989 |
| Galaxy migrated / duplicates | 1,847 / 0 | 1,845 / 2 | 0 / 1,847 |
| Decode-skipped / quarantined | 0 / 0 | 0 / 0 | 0 / 0 |
| Session turns migrated (sessions) | 151 (19) | 151 (19) | 0 (151 dup) |
| Receipt digest | `c49ed828…` | `1440c27c…` | `d4ecf9a1…` |

Gen3 galaxy reconciliation (`wm10 galaxy list`): codex 143 (= 74 migrated +
47 episodic + 22 telemetry folded), dreams 173 (175 − 2 exact dupes),
research 1,425, sessions 151, guide 6 → **1,898 records**, epoch 1,898.
The 151 `sessions` galaxy rows count once, inside the 1,845 galaxy rows; the
151 turns in `session_log.jsonl` are the session lane's projection of the same
sessions DBI and are not added to 1,898.

Non-memory lanes skipped by design (accounted, not migrated): associations
1,785, embeddings 1,560, karma 797 (total 4,142).

## 5. Parity results (neon copy vs pilot, read-only)

| Query | v9 hits | v9 mode | G3 hits | G3 mode | top-1 exact | top-10 content overlap |
|---|---|---|---|---|---|---|
| neon | 10 | hybrid | 10 | lexical | no | 0 |
| startForce | 10 | hybrid | 10 | lexical | **yes** | 4 |
| SIM PLAYLISTS | 10 | hybrid | 10 | lexical | no | 3 |
| starvation | 10 | hybrid | 10 | lexical | **yes** | 5 |
| flow-field | 10 | hybrid | 10 | lexical | no | 2 |
| hero aura | 10 | hybrid | 9 | lexical | no | 3 |
| CO DRAFTING | 10 | hybrid | 10 | lexical | no | 5 |
| minimap | 10 | hybrid | 5 | lexical | **yes** | 3 |
| asymmetric economy | 10 | hybrid | 10 | lexical | no | 3 |
| conformal | 10 | hybrid | **0** | lexical | no | 0 |

Summary: top-1 exact 3/10; average top-10 exact-content overlap 2.8/10.

The `conformal` zero-hit is **not data loss**: every v9 hit had
`bm25_score = 0.0` (vector-only match, `vector_score ≈ 0.59`) and no v9 record
lexically contains the term. Gen3's lexical-only recall is behaving correctly;
the pilot has no embedder/vector half configured.

### Sampled record reads (exact bytes)

| # | v9 galaxy / id | Gen3 record | Gen3 lane source | exact bytes |
|---|---|---|---|---|
| 1 | codex `021b7cba…` | #54 | `corpus:codex:…v9db:codex` | yes |
| 2 | sessions `87af2fb4…` | #1803 | `corpus:sessions:…v9db:sessions` | yes |
| 3 | sessions `2e41c070…` | #1751 | `corpus:sessions:…v9db:sessions` | yes |
| 4 | dreams `af379688…` | #251 (+ twin #1485 research) | `corpus:dreams:…v9db:dreams` | yes |
| 5 | codex `b0a67f27…` | #1824 (sessions twin) | `corpus:sessions:…v9db:sessions` | yes |

sha256 of sample 4 content matched on both sides (`82cf9026…`), demonstrating
the exact-content duplicate collapse: the same content can exist under several
v9 DBIs, each migrated under its own `v9db:` provenance tag.

## 6. Remaining gaps (what we cannot yet prove)

1. **Vector/embedding parity.** The pilot Gen3 store has no vector index; v9
   served hybrid BM25+vector. Lexical-only parity is proven; semantic parity
   is not. Fix path: configure the Gen3 embedder/vector half before treating
   recall as equivalent (see `memory.reembed` backfill semantics).
2. **No v9-UUID continuity.** Migration assigns fresh Gen3 UUIDs; original v9
   UUIDs survive only inside session-turn content. Per-uuid reconciliation of
   non-session records is impossible today. Fix path: emit a
   `v9_uuid → gen3_record_id` index in the migration receipt, or embed the v9
   UUID in the record source/tags (alongside `v9db:`).
3. **Ranking is not comparable.** Different engines/tokenizers; parity must be
   defined as content presence/byte-equality, not rank or score.
4. **Dry-run purity (minor).** Dry runs write `session_migration_receipt.json`
   into the target (store data untouched). Fix in `run_migration`: skip the
   session-receipt write when `dry_run` or write it next to `--receipt-file`.
5. **Dry-run duplicate blind spot.** Dry run over-predicts `migrated` when the
   source contains exact duplicate rows (intra-run dedupe not simulated).
6. **Non-memory lanes are dropped by design.** `embeddings`, `karma`,
   `dharma`, `associations`, `valkyrie`, `receipts` are counted under
   `non_memory_lane` and not migrated. Any store where these lanes hold needed
   state (wmv9: 1.6M rows; vault: 96k) needs an explicit keep/drop decision and
   a separate exporter.
7. **No DBI discovery.** The migrator scans a fixed 17-DBI list
   (`GEN2_GALAXY_DBS`). Unknown DBIs in a store are invisible to census and
   migration. Add DBI enumeration before final cutover (validate on the
   largest stores).
8. **Duplicate semantics need sign-off.** Exact `(content, source)` duplicates
   collapse (neon: 2 dream rows). Record counts will not be 1:1; this is
   intentional idempotence but must be acknowledged per store.
9. **Session evidence is a two-step lane.** `sessions` galaxy rows migrate in
   the main pass, but `session_log.jsonl` turns are ingested into Gen3
   substrate evidence via `backfill-session-evidence` (not run in this pilot).
10. **Copy window vs final v9 state.** The pilot's copy froze at
    `dbcbdece…`; live neon drifted during the session. Final flips need a
    drained/quiesced copy so the migrated state equals the last v9 state.
11. **Artifact immutability (minor).** `session_migration_receipt.json` is
    overwritten by an idempotency rerun (no `--receipt-file` for it); snapshot
    receipts after the live run if they are evidence.

## 7. Per-instance disposition

Census on 2026-10-07 from live stores (read-only) into disposable `/tmp`
targets; sizes are `lmdb/data.mdb`. "migr" = memory-bearing galaxy rows the
dry run would ingest; "skip" = non-memory-lane rows counted but not migrated.

| Unit | Port | Store (v9) | mdb | Ep | Galaxy migr (of scanned) | Skip | Decode / quar. | Turns (sessions) | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| `wm-serve@neon` | 18791 | `WMdata/projects/neon` | 16 MB | 47 | 1,847 (of 5,989) | 4,142 | 0 / 0 | 151 (19) | **pilot PASS** — flip when ready |
| `wm-serve@default` | 18792 | `WMdata/projects/default` (ro) | 560 KB | 0 | 38 (of 338) | 300 | 0 / 0 | 0 | trivial |
| `wm-serve@site` | 18793 | `WMdata/projects/whitemagic-site` | 232 KB | 2 | 24 (of 215) | 191 | 0 / 0 | 4 (1) | trivial |
| `wm-serve@planning` | 18794 | `WMdata/projects/planning` | 1.1 MB | 16 | 60 (of 1,307) | 1,247 | 0 / 0 | 38 (5) | trivial |
| `wm-serve@valkyrie` | 18785 | `~/.local/share/whitemagic` | 28 MB | 431 | 471 (of 3,211) | 2,740 | 0 / 0 | 56 (26) | trivial (18 GB in dir is Gen3 state, not v9) |
| (none running) | — | `WMdata/projects/opencode` | 242 MB | 240 | 58,814 (of 61,510) | 2,696 | 0 / 0 | 58,763 (18,037) | medium; unit currently down |
| `wm-serve@heritage` | 18797 | `WMdata/projects/heritage` | 1.9 GB | 1 | 56,456 (of 58,445) | 1,989 | 0 / 0 | 28,080 (28,023) | clean; needs window |
| `wm-serve@vault` | 18789 | `WMdata/projects/vault` (ro) | 2.4 GB | 0 | 244,815 (of 341,303) | 96,488 | 0 / 0 | 97,176 | largest; window + lane policy |
| `wm-serve@wmv9` | 18790 | `WMdata/projects/wmv9` | 1.1 GB | 19,879 | 17,204 (of 1,622,988) | 1,605,784 | 0 / 0 | 1,188 (136) | lane-policy decision first |

Notes:
- `default` and `vault` units already run `--readonly`; `vault`/`wmv9` are the
  only stores where non-memory lanes dominate (vault 28%, wmv9 99%).
- `heritage`/`vault` plain `wm10 census` shows 1/0 episodic rows — their bulk
  is in galaxy DBIs, which is why the migration dry-run is the useful census.
- No decode failures or quarantine were recorded anywhere.

## 8. Recommended cutover order

1. `site` → `default` → `planning` → `valkyrie` (tiny; batch the flip window).
2. `neon` (pilot already proven; flip plus 48 h soak).
3. `opencode` (unit down — migrate + verify before it restarts).
4. `heritage`, then `vault` (large; drain, quiesced copy, sampled verification).
5. `wmv9` last, after the non-memory-lane keep/drop decision.

Rollback remains available for every store throughout (§3.9).
