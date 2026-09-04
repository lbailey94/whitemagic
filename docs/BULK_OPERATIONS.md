# Bulk Operations — limits, maintenance profile, and battle notes

Every limit below was discovered operationally during the 2026-08-30/31
dedup-and-harvest marathon (session notes in the vault store). This doc is
the one place they're written down, so no future session rediscovers them
by failure.

## The three rate layers (all apply to every tool dispatch)

| Layer | Default | Env knob | Error signature |
|---|---|---|---|
| Meta-tool RPM (`wm` bucket) | 60/min | `WM_DISPATCH_TOOL_RPM` (0 = off) | `rate limited: wm: retry after Nms` |
| Global dispatch RPM | 300/min | `WM_DISPATCH_GLOBAL_RPM` (0 = off) | same channel |
| Yama resource rules | 60 writes/min, 10 spawns, 30 network | `WM_RESOURCE_MAX_WRITES_PER_MIN` | `Budget exceeded for writes: N/N per minute` |

**Health scaling (Yama only):** effective limit = config × health, where
health = ½(cpu-health) + ½(mem-health), clamped to [0.1, 1.0]. A loaded box
silently shrinks 60/min to ~18/min — this is the "18/18" effect. `wm doctor`
now surfaces config, health, and effective values (section 3b).

**Maintenance profile** for one-shot stdio runs:

```bash
export WM_DISPATCH_TOOL_RPM=0
export WM_DISPATCH_GLOBAL_RPM=0
export WM_RESOURCE_MAX_WRITES_PER_MIN=1000000
```

## The three size caps

| Cap | Value | Where |
|---|---|---|
| Whole request line | 1 MiB (`MAX_REQUEST_SIZE`) | oversize → connection dropped **silently** (no response!) |
| Tool params | 64 KiB (`MAX_PARAMS_SIZE`) | `-32602 params too large` |
| Connection request budget | ~10k requests | later requests rejected: `Request budget exhausted — connection limit reached` |

Practical: batch tools should chunk ids at ~1,500/call (64 KiB params) and
~8,000 calls/connection. Regenerate a fresh request file per connection.

## Batch tools

- `memory.batch_delete {ids: [...], confirm: true}` — one dispatch, one
  Tantivy commit, one karma/audit entry for the whole batch. Capped at
  200k ids. No query-form variant **by design** (the bulk-delete confirm
  gate — incident ledger, 2026-07-13: 54,192 memories deleted through an
  ungated path; never again).
- `memory.consolidate {galaxy, confirm: true}` — exact-hash dedup within a
  galaxy (scan_all since `c813e58`; keeps first-seen per content_hash).

Measured: 49,809 deletes via 34 × 1,500-id batches ≈ 15 min, vs an
estimated 5+ hours through the per-row pipe.

## The firebreak — delete-confirm audit and scope law (2026-09-03)

The Jan-11 forbidden-command guardrail is now promoted (`wm-governance`
`firebreak.rs`, enforced at the dispatch seam by `wm-dispatch` stage 4c):
forbidden patterns (`rm -rf /`-class, disk writes, pipe-to-shell,
credential paths) veto a confirmed dispatch; dangerous patterns require
`confirm: true`; the veto scans the irreversible seam only (destructive /
spawn / FS+Process+Network writes) — prose is never scanned, so incident
notes quoting commands still store fine. Kill switch: `WM_FIREBREAK=0`
(the doctor flags a disarmed firebreak as an issue).

The bulk-scope law (the Jul-13 lesson, enforced at the same seam): every
destructive dispatch must satisfy its registry scope before execution,
and the write-audit journal records the confirm per destructive entry
(`confirmed` field — the delete-confirm audit). Registry as shipped:

| Tool | Scope rule | Verdict |
|---|---|---|
| `memory.delete` | `id` required | compliant |
| `memory.batch_delete` | `ids` required (capped) | compliant (reference) |
| `galaxy.purge` | `galaxy` required | compliant |
| `galaxy.transfer` | `from_galaxy` required | compliant |
| `galaxy.restore` | `snapshot_id` required | compliant |
| `memory.consolidate` | `galaxy` required | compliant |
| `memory.deduplicate` | `galaxy` required at the seam | **default-Codex path retired at the seam** — pass `galaxy` explicitly |
| `system.flush` | `galaxy` **or** `store_wide: true` | **hardened** — tool-level `dry_run` (default true) + galaxy-honoring + value-checked scope (exactly one of non-empty `galaxy` / `store_wide: true`); per-galaxy counts + 50-id preview in the response |
| `transaction.rollback` | self-bounded (snapshot id from `transaction.begin`) | compliant |
| `karma.clear` | self-bounded (keeps most recent N) | compliant |

Unregistered destructive tools fail loud-but-open (warn per dispatch) —
add them to `SCOPE_REGISTRY`. `wm doctor` (section 11h) reports arm state
and registry coverage.

## Ops pitfalls (each cost real time; do not re-learn them)

1. **`pkill` self-match** — a pattern appearing anywhere in your own command
   line (including heredoc content) matches your own shell. Use bracket
   classes (`pkill -f 'patter[n]'`) only when the unbracketed string appears
   nowhere else in the command; prefer kill-by-PID; never combine a kill
   with a relaunch in one shell call.
2. **Long jobs must `setsid`** — a tool-call timeout kills the whole process
   group, including `nohup`'d children. `setsid nohup ... < /dev/null &`
   detaches properly. Watch for `ChildProcess.kill` as the symptom.
3. **Vault LMDB row format** — msgpack *positional* arrays:
   `[[fields(24)], content, None]` with `fields[2] = content_hash`,
   `fields[3] = tags`, `fields[6] = created_at`. Read with
   `msgpack.unpackb(v, raw=False)`; JSON parsing fails silently.
4. **Stale Tantivy reader** — a running server may not see CLI ingests;
   restart the server to refresh. Conversely, `wm reindex` drops
   sanitization-failed docs that the incremental index may still hold —
   reindex deliberately, not reflexively.
5. **Sanitization skips** — content with null bytes or <0.9 printable ratio
   is never indexed (count them: LMDB count vs Tantivy count). Recovery:
   clean the content (strip control chars) and re-ingest fresh copies.
6. **exFAT du lies** — 128K clusters inflate directory sizes up to ~2×;
   trust rsync deltas and byte counts, never du on flash media.
7. **`rsync -nc` without `-r` skips directories** — arrival checks must be
   `-nrc`. Itemized output escapes non-printable bytes (`\#ooo`); parse with
   that in mind or use a python walker.
8. **Observer effect budgeting** — bulk operations generate friction
   telemetry proportional to their errors. Sample or template-dedup
   friction at write time (V8 typology work), or budget a cleanup pass.

## The speed hierarchy for bulk store work

per-row stdio pipe (~0.5s/row) → batch tool, one commit per batch
(~15 min / 50k) → server-side consolidate (single call, ~1 min / 170k).
Design new bulk operations at the right end of this list.
