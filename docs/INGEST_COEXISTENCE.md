# Ingest Coexistence — the writer-handoff protocol

**Status:** S4 canon (V8 BUILD PLAN). One page, as planned.
**Verified as of:** 2026-08-31

Bulk operations (heritage ingest, dedupe sweeps, reindex) and a live
`wm serve` both want **exclusive writer locks** — LMDB's write lock and
Tantivy's `IndexWriter`. Neither lock is negotiable; the protocol below is
how bulk runs and live servers coexist.

## The rule

> One writer at a time. A bulk run holds the writer for its whole run; a
> live serve holds it for its whole lifetime. They take turns, never share.

## The dance (bulk run against a live store)

1. **Stop the store's unit:**
   `systemctl --user stop wm-serve@<scope>`
2. **Run the bulk operation to completion** (`wm ingest`, dedupe sweeps,
   `wm reindex`). The run takes the writer at open and releases it at exit
   (`ingest.rs` releases the Tantivy writer before saving the ledger).
3. **Start the unit again.** Serve startup runs `heal_index_drift`, which
   rebuilds any galaxy whose Tantivy count disagrees with LMDB — the
   freshness mechanism that makes turn-taking safe.

Lock contention is no longer a bare error: `wm ingest` detects it and
prints this protocol (`lock_coexistence_error` in `ingest.rs`).

## Reads during a bulk run — the sidecar

`wm serve --readonly` opens the search index with
`SearchEngine::open_readonly`: **no writer is taken**, so it runs happily
while the bulk run owns the writer. Trade-offs, disclosed loudly by the
sidecar itself:

- it never observes writes made after it opened (freshness = restart);
- writes through it fail with an actionable error.

Use the sidecar for queries, dashboards, and canary runs during a long
ingest. Do not use it as the writer.

## Import path is the exception

`session.import` does **not** follow this dance — it runs *inside* a
server's process and reuses that server's own `SearchEngine` (plumbed
through `register_session_ops`, S4). One Tantivy commit per import; every
imported record is searchable immediately with zero index drift (pinned by
`import_indexes_tantivy_no_drift_even_on_reimport`).

- Against a read-only engine, import still lands in LMDB and discloses
  that indexing is deferred to the next writable startup's
  `heal_index_drift`.

## Envelope tie-in

Streams that cross process or store boundaries carry an envelope v2 header
(`wm_memory::envelope`): `session.export` writes it, `session.import`
validates it (bare v1 payloads accepted), `wm backup` writes `envelope.json`
beside `SHA256SUMS` and `wm restore` validates it. One validator, three
uses; newer format versions are refused with an upgrade hint, never
partially imported.
