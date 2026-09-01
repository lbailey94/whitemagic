# Memory Typology v8 — Class Schema, Write Gates, and Recall Tiers

**Prepared:** 2026-08-30 (early AM, session `ddbebecf`)
**Status:** Design doc — synthesized from the B-wave mining survey (14 read-only
agents, 2026-08-30 01:00–02:00 UTC) and the C-wave research legs. Evidence
citations refer to that wave; numbers are from live stores, sampled methods
noted where approximate.
**Implementation split:** §2–§4, §8 are the v7.x slice (write-path, no schema
migration); §5–§7, §9–§10 are v8.

## 1. Problem statement — salience inversion, quantified

The RSI telemetry loop out-writes and out-ranks the content it observes:

| Evidence (B-wave) | Finding |
|---|---|
| wmv5 codex galaxy | 516 of 518 memories are auto-logged friction (99.6%); the entire non-telemetry corpus is two records, one a deletable canary |
| planning store | **Every** memory ≥0.7 importance is friction telemetry (20/20) |
| Importance | dup copies sit at 0.90 flat; genuine session decisions average 0.75 |
| Growth | ~1 telemetry record/min live during the census; codex 569→631 in ~50 min (partly observer effect — our own agents' failed probes) |
| Duplication | `rsi:dup:1` population ≥15% (offset-sampled, plausibly 40%); friction records are 85–90% boilerplate by bytes |
| Karma ledger | 524 entries, 74% from one storm day; debt threshold never crossed; `wm` wrapper fan-in double-counts ~2× |
| Graph layer | Entity space flooded: top "concepts" are Tool/Karma/Friction/Latency; zero association edges exist |
| Search quality | BM25 saturated by one template variant (50/50 top hits identical) |

Root cause: telemetry enters the same galaxies as authored knowledge, with
importance assigned by severity string (0.5/0.66/0.90) — noise outranks
signal, dedup markers (`rsi:dup:N`, `rsi:hash:*`) record duplication without
preventing it.

## 2. Typology classes (v7.x: enforce at write time)

Five classes. Class is stamped at creation, before importance is assigned;
importance is derived from class + content, never caller-chosen.

| Class | Examples | Importance policy | Searchable |
|---|---|---|---|
| `dialogue` | user/agent turns, session decisions | floor 0.75 | yes |
| `knowledge` | strategy docs, lessons, verified claims | floor 0.7 | yes |
| `telemetry` | friction records, karma events, RSI auto-logs | **ceiling 0.40** | only via explicit telemetry queries |
| `raw-archive` | heritage chunks, bulk transcripts | ≤0.30, sealed | explicit queries only |
| `pointer` | dedup stubs, rollups, references | n/a (points at content) | yes |

Detection: title/template regex (`^## Auto-logged Friction:`) + embedded-JSON
shape detect on the write path (in `wm-memory::Memory::new` claim logic and
the `friction.auto_log` / RSI recording path in `wm-tools`). Session turns
keep the existing role-derived stamping (ai→agent/0.7, user→user/1.0,
system→system/0.7 — shipped in `68547b9`).

## 3. Write gates (v8: before anything lands)

Ordered gates on the memory-create path (extends the existing destructive-
confirm/dharma/rate-limit chain in `wm-dispatch`):

1. **Junk filter** — template match against the telemetry recognizer.
2. **Dedup gate** — content-hash + template-id lookup; on hit, **do not
   insert**: increment `dup_count` + update `last_seen` on the existing row
   and *decay* its importance (`imp *= 1/(1+dup_count)`). The
   `rsi:hash:<16hex>` tag already computes this key per record — the system
   currently records duplication after the fact instead of preventing it.
3. **Plausibility gate** — class-based importance ceilings/floors (§2);
   a telemetry record can never outrank a session decision by construction.
4. **Budget gate** — per-class write budgets (extends the Phase-3
   `write_budget.json` telemetry): telemetry writes are ring-buffered per
   hash family (keep top-K/day by severity, drop the rest).

## 4. Template mining for telemetry (v7.x slice)

Store telemetry as `{template_id, tool, error_class, latency_ms, karma_debt,
counters, first_seen, last_seen}` — drop the constant prose lines and the
markdown wrapper (~85% byte reduction, B7). Drain3-style template extraction
over incoming records; one row per template family with counters, not one row
per event. Keep `friction.review`'s read path working over rollups.

Karma ledger (B8): keep the SHA-256 chain (verified intact), replace row-level
payload with **daily rollups** (`n, errors, mismatches, max_debt, top_tool`) —
524 rows → ~5 with zero decision-relevant loss. Graduate `debt_delta` by
severity so the ≥30 threshold means something; dedupe `wm` wrapper fan-in.

## 5. Galaxy layout (v8)

Per B13's store×theme survey: four warm shards by class + one cold archive +
one scratch — each with a purpose contract enforced at write time (a telemetry
event cannot land in the knowledge shard). Every memory carries
`domain:<eng|strategy|dialogue|telemetry>` + `origin-store` tags; search
fan-out routes by domain. Fix the **leaky global index** (empty `default`
store returns cross-store hits — B13): per-store scoping must be strict;
global search becomes an explicit mode, never a silent fallback. vault
(9,842 chunked transcripts, avg imp 0.23) is quarantined cold: excluded from
default fan-out, mined once into curated stores (§9), then sealed.

## 6. Tiered recall (hot/warm/cold, ILM-style)

- **Hot**: current session context + top-salience — served from the compiled
  briefing (§7), zero search.
- **Warm**: Tantivy-indexed, default recall surface.
- **Cold**: sealed archives (vault, heritage, pruned telemetry) — explicit
  queries only.
- **Promotion on read**: `access_count` already exists; recalled cold items
  get promoted (importance bump + warm re-index) — LRU-in, decay-out
  (`memory.decay` is the eviction policy). Outcome-salience signal (did
  acting on this memory succeed?) weights promotion over raw frequency —
  the direct antidote to frequency-rewarding noise (MEMTIER-style).

## 7. Cache-friendly briefing prefix (v7.x — immediate)

Provider KV-caches hit on byte-identical prefixes, *across sessions*. Adopt
the Claude Code discipline: static-first ordering (tools → system → stable
memory → session → messages); deliver memory updates as injected reminder
messages, never by editing the cached prefix; never add/remove tools
mid-session. Concretely: a standardized session-start briefing block
(galaxy dashboard snapshot → top salience → open flags → checkpoint state),
compiled at `session.checkpoint` time (pay on the write path, read cheap
forever — the checkpoint IS the cache write, continuity IS the cache read).
Measured baseline, 2026-08-30: fleet-wide 98.2–98.4% of input tokens are
cache reads; a 14-agent project-wide recall wave cost $0.045 fresh.

## 8. API gaps to close (v7.x, small)

From B14's dig: `memory.filter` silently ignores `exclude_tags`/`query`;
`memory.list`/`memory.filter` ignore `offset` (no paging); `memory.search`
with a `galaxy` arg returns empty on some builds; `memory.query` falls back
to id-ascending first-N when nothing matches. Also `memory.aggregate`
session_count/session_span return 0/null on the pinned fleet binary despite
session-tagged evidence. Each of these forced multi-call workarounds in the
wave that found them.

## 9. Heritage ingestion spec (the excavation)

Corpora located (B9): `data/staging/v26-heritage/` — **60,500 md files with
full provenance headers already in `<!-- wm-* -->` comments** (type,
timestamps, access/recall counts, importance, neuro/novelty/valence,
half_life, trust, title) — the ready-made typology schema; v26 per-galaxy
SQLite (3.6 GB, ~121k memories, sessions galaxy 21,351); legacy monolith
`whitemagic_backup.db` (404 MB, 50,084); pre-cutover `live/lmdb` (3.1 GB).

Pilot: ingest the staged md set with class assignment at write time
(`raw-archive` default; `<summary>`-prefixed session digests → `dialogue`;
curated docs → `knowledge`), source-doc IDs as tags (the vault's
`chunk:N/M`-only tagging — 9,531 of 9,546 tags are position markers — is the
failure mode to avoid), exact-dup suppression by content hash (vault shows
2–5× duplication on heritage exports), and 2–3 topical tags per doc.
Vault gem rate is ~3–5% (15 gems found in B3, e.g. `8ef1fc87` builder
strategy, `eeda7067` competitive intel, `f5a1c0ba` prescience scorecard) —
the pilot's success metric is gem recall@surface, not volume ingested.

## 10. Web research surface (v8, revive + upgrade)

The three-tier lineage survives in the current binary (`web.fetch`,
`web.deep_fetch`, `web.search`, `web.search_and_read`, `research.topic`,
`research.repo`, `research.rabbit_hole` — verified live on 18790) but is
regressed vs v2: Bing-HTML-only search (v2 had DuckDuckGo + Brave fallback +
`web_cache_list/clear`), and absent from the curated opencode-facing profile.

C3's $0 stack for burst-scale research (hundreds–thousands of pages: Brave's
free 2K/mo tier was retired Feb 2026 — cost wall confirmed):

1. **Self-hosted SearXNG on loopback** (limiter bypassed for loopback;
   engines = duckduckgo, brave, mojeek, bing — never Google/Startpage) —
   the only $0 backend sustaining 1,000+ queries/day with 2–3s pacing.
2. **Crawl4AI in-process** (pip, not Docker) for JS pages + httpx/trafilatura
   static fast-path — 5,000 fetches/day at $0.
3. **Keyless vertical APIs** wired directly: HN Algolia (10K/hr), arXiv,
   Crossref, OpenAlex, Wikipedia/Wikidata, Semantic Scholar.
4. **Hash-keyed fetch/search cache** with TTLs by volatility + URL dedup
   before fetch — the single biggest cost/latency lever (v2's cache, lost,
   restored).
5. Jina Reader free key as fallback; Exa's small paid credit reserved for
   semantic queries; never bulk.
6. Provenance discipline: every fact cited (url + quote); fetch outcomes
   logged as memory events (`telemetry` class), extractions persisted as
   `knowledge`.

PRAT lineage note (lore verified in heritage: `prat_router.py` —
"Polymorphic Resonant Adaptive Tools. Collapses 175+ MCP tools into 28 Gana
meta-tools"): the web fleet surfaces as few meta-tools as possible with
sub-routing — the 28-Gana compression discipline is a design law, not an
accident.

## 11. Standing metrics (kaizen loop)

From the A5/B-wave SQL, tracked per session: telemetry:signal ratio per store
(target < 1:1; today 11.4:1 on wmv5), dup% (target <5%; today ≥15–40%),
cost per output token (Aug: 9.4e-6, 7.3× better than Jul), median session
input-ish tokens, recall p50/p95 (74ms/235ms search-only), gem recall on the
excavation pilot. The salience-inversion fix is done when the ≥0.7 importance
band is >90% non-telemetry in every store.

## 12. Implementation sequence

1. **v7.x slice A** — write-path class ceilings + hash-suppression +
   template compaction for friction/karma (§2–§4, §8) + briefing-prefix
   compilation at checkpoint (§7).
2. **Batched fleet rebuild** (already queued) deploys the slice; old-pin
   friction family (`Unknown tool: code.claim`) retires with it.
3. **v8** — write gates + galaxy purpose contracts + strict scoping (§3, §5),
   tiered recall + promotion (§6), web surface revival (§10).
4. **Excavation** — heritage pilot per §9, running concurrently (read-only
   until the slice lands, so re-ingested content is born clean).
