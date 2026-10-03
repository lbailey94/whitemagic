# Read-path discipline audit (fold-in register #2; 9.1.8 snapshot-read class)

**Status: audit landed 2026-09-17 · driver `receipts/ops_foldin_2026-09-17/driver_readpath_audit.py`
· no verdict/claim movement.**

**Scope:** Gen3 `recall` and `inspect` read paths against the 9.1.8 snapshot-read discipline
(no lock/temp/prune; reads do not mutate what they read) and A2 §3 case 8.

## Findings

1. **No durable record/relation mutation in either path (source level; corrected 2026-09-19).**
   `inspect` is `&self` — it **cannot** mutate or journal by construction (the type system enforces
   the contract). `recall`'s mutable touches are declared and bounded: the journal append (the
   disclosure surface — `selection.decision`, `provenance.chain`), the in-process `usage` counter
   (promotion bookkeeping; explicitly *not* durable evidence, B1 §1.4), and — **projection-on
   only** — the content-hash embedding cache. `recall` embeds its query through
   `Substrate::embed_cached` (`ops.rs:828` → `:490-520`), which writes cache misses to the
   `embed_cache` store DB (`Store::put_embedding_cache`). As first written, this finding
   overstated purity: it is accurate for the default configuration (projection off); with
   `WM_GEN3_PROJECTION=1`, a first-seen query mutates `embed_cache` (never `records`/`relations`).
   Erratum L #54.
2. **No store locks on the read path.** Recall/inspect use read transactions only. For a live or
   wedged writer, the snapshot-readonly open (`MDB_RDONLY | MDB_NOLOCK`) serves reads without
   touching the lock file — demonstrated in `IMPL_A2_DISCIPLINE_2026-09-17` (idle writer: recall OK,
   writes refused; SIGKILL-wedged writer: recall still OK) and reused in `W2_07` (inspect).
3. **No temp files, no prune.** Nothing on the read path creates temporaries or expires state it
   merely observes; the journal is append-only.
4. **Runtime byte-identity (default configuration).** `data.mdb` sha256 is unchanged after a
   recall-only process and after an inspect-only process — demonstrated with projection off (the
   default); projection-on recalls populate `embed_cache` by design (finding #1) and add the
   declared `projection.load` event when the slot is enabled. The default-configuration
   recall-only journal carries exactly `{selection.decision, provenance.chain, run.end}` and the
   inspect-only journal carries `{run.end}` only (no hidden events).
5. **Journal hash-outs** remain the per-run linkage (N4): a run is invalid if its journal hash does
   not match — never silently unmeasured.

## Evidence

- `receipts/ops_foldin_2026-09-17/` — drivers + journals/responses/results (this audit).
- `IMPL_A2_DISCIPLINE_2026-09-17` — readonly open + wedged-writer recall + write refusals.
- `IMPL_W2_03_07_2026-09-17` — inspect read-only across a separate process.

## Residual (declared)

- `recall` appends journal events by design — this is disclosure, not store mutation; the audit
  asserts the event set rather than absence.
- The `usage` counter lives only in process memory; it is not durable evidence and no metric may
  cite it as such.
- Embedding-cache writes on the projection-on read path are bounded to `embed_cache`
  (content-hash keyed, one entry per distinct query text) and are not evidence records; they do
  not affect `records`/`relations` (erratum L #54).
