# Dream Cycle Post-Mortem — Recursive Telemetry Inflation (2026-08-30 → 09-01)

Status: incident closed on inspiron (store purge 2026-09-01); design
requirements herein are **v8 ship-list items**. Author: inspiron-prime.
Evidence archive: 1,648 memories, full metadata
(`store-telemetry-archive-20260901.json`).

## 1. Incident summary

Over four days the dream/consolidation cycle (running inside `wm serve`,
no daemon required) grew the store from a ~400-memory working set to
1,765 memories of which **1,648 (93%) were machine self-talk**:

| day | telemetry minted |
|---|---|
| 2026-08-30 | 113 |
| 2026-08-31 | 413 |
| 2026-09-01 | 1,122 |

The minting rate *accelerated* — each cycle's outputs became the next
cycle's inputs.

## 2. Anatomy of what was minted

| kind | count | shape |
|---|---|---|
| hypothesis (hub confirmation) | 1,051 | `Hypothesis: Hub memory '<snippet>' (reach=N) confirmed as cross-cutting pattern — current consolidation is appropriate.` |
| dream summary | 534 | `Dream summary: N memories in G galaxy tagged 'T' (avg importance: X).` |
| strategy snapshot | 63 | `Strategy [tag]: N memories (avg importance: X). Themes: … Snippets: <hundreds of embedded snippet references>` |

The strategy memories embedded hundreds of prior-telemetry snippets
inline — a memory that was itself an index of telemetry.

## 3. The verdict-monotony proof (why this was not insight)

- **1,042 of 1,051 hypotheses carry the byte-identical verdict**:
  "confirmed as cross-cutting pattern — current consolidation is
  appropriate." Zero variance across ~1,000 runs.
- **Hub fixation was 100% self-referential**: the top quoted hub
  subjects are friction entries, friction-count strategies, and dream
  summaries. Not one user decision, session arc, or project memory was
  ever confirmed as a hub.
- **Novel forms: 9 of 1,648** — all the same template with different
  reach numbers. No new claim was ever asserted.
- The cycle also minted **ghost references** to friction entries after
  those entries were purged (2026-09-01 morning), and kept publishing
  count-snapshots of a world that no longer existed.

Conclusion: the loop produced no unique, novel, or useful conclusion in
1,648 memories. Its only genuine output was the *pattern of its own
failure* — this document.

## 4. Root causes

- **R1 — no self-exclusion.** Consolidation consumed its own outputs
  (hypotheses about strategies about hypotheses).
- **R2 — no novelty gate.** An identical verdict minted a new memory
  every cycle. Nothing compared "what am I about to write" against
  "what have I already written."
- **R3 — no GC.** Consolidation never retracted or cleaned references
  to deleted memories.
- **R4 — no volume governor.** Nothing capped minting rate or
  telemetry share of the store.
- **R5 — namespace pollution.** Telemetry landed in the same galaxies
  and search indexes as user content (`research` was 99% telemetry),
  degrading retrieval for real queries.
- **R6 — hub bait.** The (now-gated) friction autolog fed the cycle
  high-salience junk that dominated reach metrics, so the cycle
  "confirmed" friction hubs ~1,000 times.

## 5. v8 design requirements (testable)

1. **D1 — self-exclusion**: dream/consolidation outputs carry a
   `rsi:telemetry` class and are excluded from future consolidation
   inputs. Test: run two cycles; cycle 2's inputs must not contain
   cycle-1 telemetry.
2. **D2 — verdict dedup**: a conclusion identical (content-hash or
   near-dup) to an existing un-expired one must not mint. Test: two
   identical runs mint exactly one memory.
3. **D3 — consolidation GC**: deleting a memory invalidates telemetry
   that references it. Test: delete a hub; referencing telemetry is
   retracted or flagged stale on next cycle.
4. **D4 — governor**: per-galaxy minting caps (rate + share-of-store).
   The cycle self-throttles when telemetry exceeds e.g. 10% of a
   galaxy. Test: force low cap; verify throttling, not silent growth.
5. **D5 — namespace separation**: telemetry is written to a dedicated
   galaxy/index, excluded from user search scopes by default, surfaced
   only on explicit request.
6. **D6 — novelty requirement**: a hypothesis must assert a predicate
   not already present in the telemetry corpus (hash + semantic
   near-dup). The 1,042-identical-verdicts case must be unrepresentable.
7. **D7 — observability**: `wm doctor` / status expose minting rate,
   telemetry ratio, and largest-tag growth; alarm thresholds surface in
   doctor output (the trust survey's by-tag table was our early
   warning — make it standing).
8. **D8 — input hygiene**: consolidation inputs exclude exogenous
   junk classes (post-S9 the friction autolog is off by default; D1/D5
   keep the loop from re-feeding itself).

## 6. Recovery playbook (what worked, for the next incident)

1. **Detect**: trust survey (source × trust × tag table) + a search for
   template prefixes; a telemetry ratio above ~20% of any galaxy is
   already pathological.
2. **Harvest**: read-only side server; classify with content-prefix +
   tag safety rules (prefixes first — tag-only classification over-
   matches); export full metadata to an external archive. Zero loss.
3. **Purge**: transaction.begin → chunked `memory.batch_delete` →
   verify counts per galaxy → commit. Script it; hand-transcription of
   1,600 ids is error-prone (we tried; one typo in 63).
4. **Reindex**: full Tantivy rebuild after mass deletion; verify
   template-prefix searches return only legitimate narration.
5. **Re-survey**: the trust table becomes honest and small.
6. **File the upstream fix** (this document) — purge without the fix
   just restarts the clock.

## 7. What was kept

The full 1,648-memory archive is retained on archival storage. If v8's
dreamer ever needs a corpus of *what recursive self-consolidation looks
like*, this is a complete, timestamped specimen — the negative example
that justifies D1–D8.
