# Tantivy Recall Quality Fix — Work Spec

**Status**: Ready for a parallel session
**Owner**: WMv5 (Rust) — `crates/wm-memory/src/search.rs`, `crates/wm-tools/src/expansion/memory_ops.rs`
**Affected**: `memory.hybrid_recall`, `memory.search`, and every consumer (Antigravity proxy, opencode MCP)
**Baseline**: WMv5 source at `~/Desktop/WMv5` (currently v5.7.4, `target/debug/wm`); live store at `~/Desktop/WMdata/live` (58,660 memories, 11 galaxies)

---

## 1. Problem Statement

Full-text recall returns **irrelevant results at misleading scores** and occasionally
**binary garbage content**. Observed on the live store:

1. **The incident (2026-08-11)**: `memory.hybrid_recall` with query `"smoke test from wmClient"`,
   `limit: 20` returned 20 unrelated memories (e.g. "NES Evolution and Impact", "Insights on
   The Gateless Gate", "What the tweet is really saying") with **BM25 scores 0.5–1.0** and
   **zero query-token overlap** in their content previews. A cleanup script trusted these
   results and deleted all 20 memories (3/20 later recovered via raw LMDB forensics — see
   `~/Desktop/WM_RESTORE_AND_INTEGRATION.md`).
2. **Garbage content**: several FTS hits contain raw serialized bytes (migration artifacts
   from the v26→v5 import) instead of readable text. These currently require client-side
   sanitization (`sanitizeMemoryText` in the Antigravity patch).
3. **Project-query degradation**: query `"antigravity antigravity-project-test"` returned
   nothing relevant (compound/hyphenated tokenization), forcing a client-side plain-query
   fallback.
4. **Score thresholding is impossible**: BM25 scores are unbounded and unscaled, so clients
   cannot set a meaningful `minScore`.

> NOTE: the incident ran against the OLD release binary (`target/release/wm` v5.2.1, built
> Aug 2026). The current source (5.7.4) sets `set_conjunction_by_default()`, which may
> already change the garbage behavior. **Reproduce on BOTH the old binary and the current
> one before concluding.** If the old binary used OR semantics without a threshold, that
> fully explains the incident (common terms "test"/"from" matching most of the corpus).
> Even with conjunction, the other problems (2–4) stand.

---

## 2. Code Map

### `crates/wm-memory/src/search.rs` (tantivy 0.26)
- Schema: `memory_id` (STRING|STORED), `galaxy` (STRING|STORED), `content` (TEXT|STORED),
  `tags` (TEXT), `timestamp` (i64|STORED).
- `content` uses tantivy's **default tokenizer** (`SimpleTokenizer` — lowercase, splits on
  whitespace/punctuation; **no** camelCase split, **no** stopword removal).
- `search_in_galaxy(query, galaxy, limit)`:
  1. `sanitize_tantivy_query(query)` — wraps EVERY whitespace-separated term in double
     quotes → every term becomes a **phrase query**.
  2. `QueryParser::for_index(index, [field_content, field_tags])` + `set_conjunction_by_default()`.
  3. `TopDocs::with_limit(limit).order_by_score()` — **no score threshold**.
  4. Post-filters `galaxy` only by comparing the stored string; `content` is returned from
     the index **without verifying the memory still exists in LMDB** (stale entries survive).
- `add_document` indexes raw `content` as-is (binary garbage included).
- `delete_document` deletes by `Term::from_field_text(field_id, memory_id)`.

### `crates/wm-tools/src/expansion/memory_ops.rs`
- `memory.hybrid_recall` (`MemoryHybridRecallTool`):
  - Phase 1: `search.search(query, limit * 2)` → for each hit, `store.get(galaxy, id)`
    (stale entries filtered here) + `importance >= min_importance` → push `{id, content,
    importance, score, source: "fts"}`.
  - Phase 2 (fallback, only if phase 1 empty): `store.scan(galaxy, 100)` +
    `content.contains(query)` — **scans only the first 100 memories** (by id order, i.e. the
    oldest) — nearly useless at 58K scale, and `source: "scan"`.
- `memory.search` (`MemorySearchTool`, in `lib.rs`): returns `content_preview` straight from
  the index — **no LMDB verification** → deleted memories can still appear.

### Consumers
- Antigravity patch (`~/Desktop/Antigravity/antigravity-add-model/src/wmClient.ts` +
  `src/proxy/wmMemory.ts`): client-side guards already in place — `sanitizeMemoryText`
  (rejects >10% control chars, strips non-printables, 1KB cap), `sharesMeaningfulToken`
  (≥1 non-stopword token overlap with the prompt), optional `minScore` config, plain-query
  fallback for project mode. **Do not regress these**; the WM-side fix should make them
  unnecessary, not conflict with them.

---

## 3. Root-Cause Hypotheses (ranked)

1. **No score threshold + permissive matching** — low-BM25 hits are returned regardless of
   relevance. With the old binary's presumed OR semantics this is catastrophic; with
   conjunction it still returns weak matches (documents that merely contain the terms
   scattered, or match only in `tags`).
2. **Binary/garbage content indexed** — migration artifacts are in the index; they pollute
   top-K results and, for `memory.search`, leak raw bytes to clients.
3. **Stale index entries** — LMDB/tantivy drift (deleted memories still searchable via
   `memory.search`; `hybrid_recall` filters them via `store.get` but wastes the top-K slots).
4. **Tokenization mismatch** — `SimpleTokenizer` + phrase-quoting: `wmClient` → `wmclient`
   (single token); `antigravity-project-test` → one token `antigravity-project-test`
   (hyphens not split by default SimpleTokenizer — **verify**); no stopword handling, so
   `"from"`, `"the"`, etc. inflate scores.
5. **Phase-2 scan fallback scans 100 of 58K** — effectively a lottery; also produces the
   `source: "scan"` noise.

---

## 4. Fix Plan

### Short-term (index + query hygiene, highest ROI)
1. **Score threshold in search**: add a `min_score` param to `search` / `search_in_galaxy`
   (absolute BM25 threshold) AND/OR a relative floor (`top_score * ratio`, e.g. 0.05–0.1).
   Apply a sane default in `hybrid_recall` (e.g. `min_score` arg passthrough, default
   relative-to-top). Validate thresholds empirically on the live store.
2. **Index-time sanitization**: in `add_document`, skip or scrub content that is not clean
   text (reuse the client-side heuristic: null bytes → skip; printable-char ratio < 0.9 →
   skip; cap length ~8KB). Also sanitize on `hybrid_recall`/`search` output (belt & braces).
3. **Stopword handling**: strip common stopwords from queries (or switch `content` to an
   English tokenizer with stopwords at index time — requires a **full re-index**).
4. **Full index rebuild tool**: add a `wm` subcommand (or `wm_forensic`-style bin) that
   rebuilds the tantivy index from LMDB: iterate all memories via `store.scan`/cursor,
   apply sanitization, skip stale/deleted, re-add. Run it once against the live store.
   (Backup `WMdata/live/tantivy` first — the Antigravity backup module snapshots it.)

### Medium-term (query semantics)
5. **Fix `sanitize_tantivy_query`**: don't phrase-quote every term — only escape when the
   term contains reserved chars (`+ - && || ! ( ) { } [ ] ^ " ~ * ? : \ /`); keep
   conjunction but consider `minimum_should_match` for multi-word queries.
6. **Fix Phase-2 fallback**: replace `scan(galaxy, 100)` with a proper iteration (scan in
   batches / full cursor) or drop it in favor of a relaxed FTS query (OR + threshold) so
   `source: "scan"` noise disappears.
7. **`memory.search` store verification**: check `store.get` before returning
   `content_preview` (or return the `memory_id` and let clients verify — but the tool
   contract currently returns previews, so verify server-side).
8. **Score normalization**: expose a scaled score (e.g. `score / max_score_of_top_k`) so
   clients can use stable thresholds.

### Long-term (retrieval quality)
9. **Embedding-hybrid recall**: the store has an `embeddings` galaxy — combine BM25 + vector
   similarity (`hybrid_recall` is already named for this). Explore `wm-memory/src/vector.rs`
   / `lance_vector.rs` / `semantic.rs` and the embedder.
10. **Per-galaxy + tag-aware ranking**: weight `galaxy` matches and boost tag hits; add
    optional `tags` filter to `hybrid_recall`/`search` (currently absent — clients request
    it for project scoping).

---

## 5. Verification Plan

1. **Reproduce the incident query** against the live store with the current binary:
   `wm serve --store ~/Desktop/WMdata/live`, then
   `tools/call` → `wm`, `route: memory.hybrid_recall`, `args: {query: "smoke test from wmClient", limit: 20}`.
   Expected after fix: only memories genuinely containing those tokens (ideally the
   `[antigravity:...]` smoke memories) at sane scores; no unrelated hits.
2. **Garbage check**: run `memory.search` over several queries; assert zero binary content.
3. **Project query**: `"antigravity antigravity-project-test"` must return `[antigravity:]`
   memories (or at least the plain-token ones).
4. **Stale check**: delete a memory, then `memory.search` must not return it.
5. **Latency budget**: recall on 58K store should stay < ~500ms (currently ~120ms).
6. **Unit tests**: extend `search.rs` tests (threshold, sanitization, stopwords) and add
   `hybrid_recall` tests mirroring the incident query.
7. **Cross-check consumers**: Antigravity's 201 tests
   (`cd ~/Desktop/Antigravity/antigravity-add-model && npm test`) must stay green; the
   client-side guards can stay as defense-in-depth.

---

## 6. Repro/Dev Notes

- Build the current server: `cd ~/Desktop/WMv5 && cargo build --release --bin wm -p wm-mcp`
  (or debug). The integration auto-detects release→debug.
- Store layout: `--store <dir>` expects `lmdb/` + `tantivy/` inside; live = `~/Desktop/WMdata/live`.
- There is an old `target/release/wm` (v5.2.1) behavior to compare against — check git log
  of `search.rs` between v5.2.x and v5.7.x for `set_conjunction_by_default` / sanitizer
  changes to confirm hypothesis 1.
- The `wm_forensic` bin (`crates/wm-mcp/src/bin/wm_forensic.rs`) shows the pattern for
  temporary tooling; a `wm reindex` subcommand should land in `wm-mcp/src/bin/wm.rs` or as a
  library API in `wm-memory` with an MCP tool (`galaxy.reindex`).
- Back up before mutating the live index: `~/.gemini/antigravity/backups/wmstore/*` or copy
  `WMdata/live/tantivy` + `lmdb`.

---

## 7. Multi-Process Model (ALREADY SHIPPED — don't break it)

The tantivy index lock is **exclusive** (`IndexWriter` lock in `Lockfile`). Unlike LMDB
(multi-process RW via `lock.mdb`), only ONE process may hold a tantivy writer on a store at
a time. A second `wm serve` on the same store dies at startup with `LockBusy` — this broke
the opencode mirror whenever Antigravity's proxy had the store open.

**Shipped fix (2026-08-11)** — read-only mode:
- `SearchEngine::open_readonly(path)` in `wm-memory/src/search.rs` — no `IndexWriter` is
  created, so no exclusive lock; `writer()` errors; `add_document`/`delete_document`/
  `commit` reject writes.
- `McpServer::with_defaults_mode(store_path, readonly)` in `wm-mcp/src/server.rs`.
- `wm serve --readonly` flag in `wm-mcp/src/bin/wm.rs`.
- Memory mutation tools (`memory.create` / `memory.update` / `memory.delete`) reject with a
  clear error when the index is read-only (prevents silent LMDB-write-without-index).
- Consumers: Antigravity's proxy = full RW (`wm serve --store …`); the opencode mirror =
  read-only (`~/.local/bin/wm-mcp` → `wm serve --readonly --store …`). A stale-writer
  cleanup (`cleanupStaleWmServers` in the Antigravity patch) kills orphaned RW servers at
  app startup.

Any reindex/rebuild work must respect this: the reindex tool needs the writer (run when
Antigravity is closed, or acquire the lock with a clear error).
