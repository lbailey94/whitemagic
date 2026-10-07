# Wave-1 spec B1 — Retrieval & ranking

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `309e111` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. The freeze takes effect
only at operator ratification + `receipts/` entry.

**Row:** Retrieval & ranking (wave plan §2; `CLEANLY → compile (earned subset only) · E2, E3`).
**Wire:** `recall` + R/strata; **no Gen2 planners imported** (behavior under test).
**Nucleus touch points:** N2 (earned ordering), N3 (selection explanations), C1 slot (S gated;
not a stage), Part 3 (D2 score policy; invocation pin; candidacy/strata settings).
**Caution carried:** no planner imports; the lexical–semantic design stays **measured**.
**Do not re-raise:** errata A#1/#2 (embedder constant, qFHRR/Jaccard corrections — not this row's
inventory); deprecated ranking organs are DO_NOT_MIGRATE by absence, not by verdict.

---

## 1. Frozen behavioral spec

### 1.1 Scoring (D2 Option B — idf-weighted query support)

- Candidate generation: query tokenized (`field::tokenize`); per-token postings union →
  `lexical_candidates`; optional semantic candidates only when the projection slot runs (§1.2).
  (`crates/wm-gen3-core/src/ops.rs:467-479,555-581`)
- `lex_support = (Σ idf of matched query tokens) / (Σ idf of all query tokens)`, clamped [0, 1]
  (`ops.rs:600-610`). `idf = ln(1 + n/(1+df))` (`ops.rs:479-491`). `sem_support` from the slot
  (cosine above the statutory τ, mapped by `semantic_support`). **`support = max(lex, sem)`**
  (`ops.rs:611-612`). (SOURCE-IMPLEMENTED; ordering MEASURED on frozen corpora)
- **No per-query or corpus normalization**; `score ∈ [0,1]`; `< 0.01` = essentially no
  informative support (scale note, not a floor). Floors `min_score` / `min_coverage` filter on
  `support` and are fail-closed (A2 owns the floor contract). (`ops.rs:613-618`)
- Limit semantics: `limit == 0 → 10`; `candidate_limit == 0 → unbounded`; truncation
  `limit.min(candidate_limit.max(1))`; ranks 1-based (`ops.rs:650-652`).

### 1.2 The earned subset only

- **Imported:** R candidacy + structural strata (N2; A3 owns the relation/ordering contract);
  D2 support; the C1 projection slot under its declared activation (`floor` mode falsified /
  `count` mode confirmed — gated3; not a general stage).
- **Not imported (absence is part of the frozen behavior, not an oversight):** weighted RRF
  k=60 multi-channel fusion; multiplicative entity/importance/recency/lexical rerank;
  cross-encoder blends; conversation-gated bonuses; tag-set Jaccard dedup; qFHRR prefilter;
  weighted multi-galaxy merge. Any import requires a **new registration** (ancestor · wire ·
  acceptance · owner) + fresh holdout.
- **Lexical–semantic design stays measured:** the slot's contribution is the gated3 record
  (O₁ 10/10; CostEfficiency 0.381; ≥2 boundary MissedOpportunity₊₂ = 1.000, parked). No re-tuning
  via the ranking path.

### 1.3 Ordering keys

- `key = support × (1 + recency_weight × recency)`; superseded records (unless
  `include_historical`) multiply by `(1 − supersede_penalty)` (`ops.rs:619-624`). Statutory
  values: recency weight 0.05, supersede penalty 0.60 (NUCLEUS §3).
- `Arbitration::PenaltyMultiplier` (Tier-2 default): sort by `key` desc, then id desc.
  `Structural` (frozen experimental mode): **stratum asc (0 current / 1 unresolved / 2
  superseded), then lexical desc, semantic desc, recency desc, id desc** (`ops.rs:638-648`).
  The strata semantics belong to A3; this row owns the within-stratum key order.
- `include_historical: true` collapses strata to 1 and keeps history visible (`ops.rs:626-634`;
  A3 owns lossless history).

### 1.4 Observable outputs and journal

- `Hit { id, content, source, score, rank, superseded_by }`; applied relations recorded on current
  use (`ops.rs:661-676`). Journal: `selection.decision` (counts + per-selected
  `rank_key/score/semantic_support/stratum/superseded_by`) + `provenance.chain` per hit (A2 owns
  the disclosure vocabulary; **B1 owns the rank fields**). (RUNTIME-OBSERVED, C4/C6)
- Read discipline: recall is read-only over durable state (`ops.rs:454`); it updates **in-process**
  usage counters for later promotion bookkeeping (`ops.rs:664`) — usage is not durable evidence
  and must not be counted as one.

### 1.5 Statutory parameters named (Tier-2, none swept)

D2 score policy · invocation pin (`--limit 10 --candidate-limit 100 --min-score 0
--min-coverage 0`) · recency weight 0.05 · supersede penalty 0.60 · τ = 0.694 (slot only) ·
arbitration mode default per NUCLEUS §3.

### 1.6 Non-goals

No planner imports · no learned weights · no score nudges · no benchmark-derived parameters · no
changes to abstention vocabulary (A2) or strata semantics (A3).

---

## 2. Selection history

**Ancestor (Gen1 v26):** the retrieval stack accreted one ranking organ per feature wave —
8-stage planner with weighted RRF k=60 (lexical 1.0 · semantic 1.0 · spatial 0.5 · entity 0.3 ·
graph 0.4), multiplicative second-pass rerank (entity .25 / importance .20 / recency .15 /
lexical .15), cross-encoder 0.6/0.4 blend with heuristic fallback, conversation-gated additive
bonuses, `dedup_threshold 0.85` tag-Jaccard, abstention 0.50, qFHRR 8-bit prefilter
(`W1_retrieval.md`). The planner and legacy path shipped side by side with parity never confirmed
(`unified.py:759-787`).

**Selection fate:** modes folded; ranking policy made **behavior under test** and excluded from
the A/B (decomposition row 2); the earned subset (R + strata + D2 support) survived; no Gen2
planner imported (`DEPENDENCY_MANIFEST.md:54`).

**Gen3:** `recall` implementation as §1; evidence levels — scoring formula SOURCE-IMPLEMENTED,
ordering MEASURED (five corpora; consolidation §4), journal events RUNTIME-OBSERVED (C2/C4/C6),
slot contribution MEASURED gate-scoped (gated3).

---

## 3. Adversarial cases

1. **Optional-stage reordering** — toggling the projection slot on/off changes ordering only via
   its declared gate effect; any additional ordering delta is a defect (translation of the v26
   stage-order mutation class).
2. **No implicit filtering** — records sharing tags are never dropped (the v26 tag-Jaccard
   0.85 legit-drop class cannot exist here; assert duplicates survive).
3. **No warm-up nondeterminism** — the v26 cross-encoder background-load class does not exist
   (not imported); assert repeated queries in one process are order-stable given identical state.
4. **No score nudges** — freshness/supersession affects ordering only through strata +
   statutory penalty (no ±0.15/±0.20-style adjustments).
5. **Floors fail-closed (#3)** — out-of-range floors are structured errors, never silent
   disablement (A2 boundary table re-run here against the ranking path).
6. **Drift honesty (#5)** — a drifted index yields coherent recall or explicit degraded
   disclosure, never silent zero.
7. **Read-only discipline (9.1.8)** — recall takes no locks on the durable store and writes
   nothing durable; usage counters are in-process only.
8. **Starvation (9.1.8)** — reads stay open under starvation; zero results are disclosed per A2
   (never inferred from stress).

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| R sweep (`WM_GEN3_SWEEP=0`) | strata ordering + proposals | flat strata 1, zero `relation.proposed` (C2) | RE-ENTERS (ordering change is measured) |
| Projection slot (`WM_GEN3_PROJECTION`) | count-gate fired sets reproduced (C3) | ordering = lexical-only | RE-ENTERS (gate-scoped) |
| Planner negative control | frozen ordering | adding any planner must produce **0-diff vs frozen corpora or a registration** | EFFECTFUL (an unauthorized import is caught as a diff) |

Rungs: `selection.decision` (EXECUTED) → ordering deltas (EFFECTFUL) → cross-process stability
(PERSISTENT) → ablation flips (RE-ENTERS). EXTERNAL not claimed. No inert passengers: every rank
field added must be consumed by an acceptance check.

---

## 5. Acceptance + owner

Wrapper-side (harness; counts generated, never narrated):

1. **Frozen-corpus regression** — all switches off: per-query ordering identical to the frozen
   cells (0-diff pattern).
2. **C2/C3 templates** — sweep and count-gate ablations reproduce their recorded fired sets and
   ordering flips.
3. **Per-result disclosure** — every hit carries the A2 fields + B1 rank fields; ordering is
   reconstructible from the journal (auditability).
4. **Floor boundary table** — fail-closed on out-of-range.
5. **No-planner proof** — a syntax-level/behavioral check that scoring contains no unregistered
   multiplicative term; any addition fails the frozen-corpus diff.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W1_SPEC_B1_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
