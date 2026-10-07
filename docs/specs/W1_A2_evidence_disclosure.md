# Wave-1 spec A2 — Evidence disclosure

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 (cross-cutting spec template) at WMgen3 tip `b7565ee` (tree clean), under the frozen nucleus
(`docs/NUCLEUS.md`, sha256 `73c5a9cf…`). **Owner: unset — operator assigns at freeze.** The freeze
takes effect only at operator ratification + `receipts/` entry. Docs-only: no code, no gates, no
verdicts, no thresholds.

**Row:** Evidence disclosure (wave plan §2 row: `CLEANLY → compile (contract) · E4`).
**Wire (Gen3 expression):** declared floors + explicit `insufficient_evidence`; provenance chains.
**Nucleus touch points:** N1 (provenance chains), N3 (selection explanations), N4
(journal-as-evidence), N5 (audit discipline — flags published, never deleted; raw + adjudicated
reporting); Part 1 invariants 3 (provenance on every durable record), 6 (truthful surfaces —
abstention over silent success).
**Caution carried (wave plan):** v26 `abstention_gate` existed → **transformed** (E4 errata; do
not re-raise as "Gen1 ancestry: none"). The "no swept thresholds" case is mandatory.
**Do not re-raise:** errata A#4 (the ancestry correction is landed); errata #6 (galaxy sprawl) is
not this row.

---

## 1. Frozen behavioral spec

Observable behavior, inputs/outputs, journal events, statutory parameters named (Tier-2). Nothing
benchmark-derived.

### 1.1 Contract — retrieval never silently claims absence

- **Input:** `RecallQuery { query, limit, candidate_limit, include_historical, min_score,
  min_coverage }` (`crates/wm-gen3-core/src/ops.rs:93-100`). **Floors (`min_score`,
  `min_coverage`) are caller-declared per invocation** — the statutory invocation pin runs
  `--min-score 0 --min-coverage 0` (NUCLEUS §3; harness recipe). (SOURCE-IMPLEMENTED)
- **Output:** `Hit { id, content, source, score, rank, superseded_by }` (`ops.rs:103-110`), plus a
  per-result journal disclosure (below).
- **Abstention is explicit, with a closed reason vocabulary:**
  - empty/stopword-only query → `selection.decision{abstained: true, reason: "no_query_tokens"}`
    (`ops.rs:460-466`; RUNTIME-OBSERVED);
  - non-empty query where all candidates fall below declared floors → **explicit
    `insufficient_evidence`** in the journal (`selection.decision{abstained: true, reason:
    "insufficient_evidence"}`). This is the migration's target vocabulary; the current
    `no_candidates` reason maps to it at implementation, and the mapping is recorded in the
    receipt. The wave row's `no_results_above_floors` is the *cause annotation*, not a second
    reason token. **One vocabulary, named here.**
  - a silent empty result is forbidden: every empty return carries exactly one abstention event.
- **Floors are fail-closed:** out-of-range floor values are caller errors, refused with a
  structured validation error — never silently filtered out or disabled (the 9.1.7 `min_trust`
  `.filter(0.0..=1.0)` defect class, Tier 1 #3). No code path disables a declared floor.

### 1.2 Contract — every returned result carries provenance

- Per result, the journal emits `provenance.chain{result_id, chain, complete: true}`
  (`ops.rs:679-685`). At result granularity the chain must be **100 % complete** (H4; canary C4:
  complete in all seven runs, zero `closure.violation`). (RUNTIME-OBSERVED)
- Per recall, the journal emits `selection.decision` with the selection explanation: `considered`,
  `lexical_candidates`, `semantic_candidates`, `arbitration`, `dispersion`, `selected[]` entries
  carrying `id · rank · rank_key · score · semantic_support · stratum · superseded_by`, plus
  `abstained` and `reason` (`ops.rs:687-695`). N3.

### 1.3 Contract — no swept thresholds, ever

- Floors are **declared** (caller or statute), never swept; no benchmark-derived threshold may
  reinterpret the abstention boundary (v26's 0.50 default was sweep-derived and is
  DO_NOT_MIGRATE #10-class). The D2 score policy's `< 0.01` note is a **scale description**
  ("essentially no informative support"), not a floor.
- Any future floor change is a Tier-2 statutory act (NUCLEUS §3; S6), not a tuning.

### 1.4 Link boundary — which side discloses what (divergence discipline)

- The Gen2 **evidence bundle v0** is the live product surface (capability source; W1 source map
  §2, `memory_ops.rs:45-183`): entry fields `id · galaxy · retrieval{route,score,matched_terms,
  via} · source_time{created_at,basis,event_time,basis} · history{revision_count,superseded,
  chain_valid,current} · integrity · visibility{private,model_exclude} ·
  coverage{representation,truncated,exact_read_available}` + `conflicts{count,pairs}`;
  cold-only ⇒ `unavailable_cold_record`. (SOURCE-IMPLEMENTED + live)
- The Gen3 **journal** is the evidence surface: `selection.decision` + `provenance.chain` must be
  sufficient to reconstruct route, score, basis, chain, and currentness for every returned result
  (H4 wording). The wrapper-side acceptance joins the two; a divergence between bundle and journal
  is a **finding**, not a silent choice.
- Degraded routes disclose explicitly (Gen2 `recall_mode`: `hybrid | episodic | fts |
  importance | none`; the never-silent rule applies on both sides): a degraded path must not be
  indistinguishable from healthy-with-zero-results.

### 1.5 Statutory parameters named (Tier-2, none swept)

Invocation pin floors (`--min-score 0 --min-coverage 0`; NUCLEUS §3) · D2 score policy
(`archive/research/PHASE1_SCORE_POLICY.md` §5) · audit protocols v1.2/v1.3 (flags published, never deleted; raw +
adjudicated reporting — N5).

### 1.6 Journal events owned by this spec

`selection.decision` (reasons: `no_query_tokens`, `insufficient_evidence`, plus the strike reason
`duplicate_exact` from A1 where relevant) · `provenance.chain`. The `insufficient_evidence` token
is **owned here**; renaming or aliasing it is a spec revision, not a runtime decision.

### 1.7 Non-goals

No ranking changes; no confidence scores; no semantic calibration (claims row, batch B); no
multi-view/Pareto ordering (dormant); no thresholds of any kind; the Gen2 bundle is not
reimplemented on the Gen3 side.

---

## 2. Selection history

### 2.1 Ancestor (Gen1 v26)

`core/memory/abstention_gate.py` ("Gap D"): abstains when top-result relevance falls below a
threshold (default 0.50, "determined by threshold sweep — TPR 100 % / FPR 0 % on a 500-memory
benchmark"); relevance = 0.5·cosine + 0.3·keyword-overlap + 0.2·min(1, 10·RRF); clamp [0, 0.8];
wired **only** in the memory tool handler when `abstention_threshold` kwarg or
`WM_ABSTENTION_THRESHOLD` env is set — not a `memory.search` default (W1_retrieval:59-64).

### 2.2 Observed behavior

Threshold-based abstention existed and was opt-in/standalone; its headline precision claim is
sweep-derived and therefore non-transferable. Default-flow reachability of the gate is
**UNVERIFIED** (only explicit kwarg/env wiring was found) — do not cite it as default behavior.

### 2.3 Selection fate

- Threshold abstention **rejected as a primitive** (benchmark-derived); Gen2 **transformed** it
  into declared floors + explicit `insufficient_evidence` + evidence bundle v0 (delta; E4 errata;
  findings row "Errata candidate — Evidence-disclosure ancestry").
- Gen3 fell to: record provenance + selection explanations + journal (decomposition row; E4:
  `selection.decision` with `abstained`, `provenance.chain` completeness, `boundary.refusal`;
  H4/H6 standing 100 % / zero across eight corpora; audit 20/20 + 40/40). This spec freezes that
  contract and adds the explicit-insufficiency vocabulary.

### 2.4 Evidence-level register (per statement, protocol §3)

| Statement | Level |
|---|---|
| v26 `abstention_gate.py` behavior + 0.50 sweep origin | SOURCE-IMPLEMENTED |
| v26 gate reachable only via kwarg/env (default flows) | STATICALLY-REACHABLE; **UNVERIFIED** for default flows |
| Gen2 floors/`insufficient_evidence`/bundle v0 | SOURCE-IMPLEMENTED + live |
| Gen3 `selection.decision` / `provenance.chain` / C4 completeness | RUNTIME-OBSERVED (canaries C4, C6) |
| "No swept thresholds" | Statute (Tier-2), not measured |

---

## 3. Adversarial cases

Each case must exist as a runnable acceptance assertion before the row exits; no inert passengers.

**From the 9.1.7 audit fix list (Tier 1):**

1. **Out-of-range floor (#3)** — `−ε / 0 / 0.5 / 1 / 1+ε` boundary table; out-of-range must be a
   structured caller error (fail closed). A silently disabled floor is the exact defect class.
2. **Drift disclosure (#5)** — `index_ok: true` with store↔index drift is forbidden; status must
   report explicit degraded state (or reconcile), never healthy.
3. **Partial success (#6)** — a result claimed as returned but failed mid-capture must disclose
   `partial_success` with detail, not completeness.

**From the findings:**

4. **No swept-threshold regression** — the abstention contract must not regress into a tuned
   threshold; floors declared, never swept (the mandatory case recorded in the E4 errata).
5. **Labeled-answer-is-superseded (LABEL/state-conflict class)** — v26's −0.20 superseded penalty
   could make a labeled answer worse (FAMA coupling, W1_retrieval:82-85); Gen3 must keep
   testbed-audit flags visible rather than tune anything (N5). No score nudge is permitted as a
   "fix."
6. **Cold record** — a candidate that is cold-rotated must disclose `unavailable_cold_record`
   rather than "no evidence" (link-side bundle class); on the journal side the query must still
   abstain explicitly, never silently.
7. **Route degradation** — each route (`hybrid | episodic | fts | importance | none`) must be
   disclosed; a stub-embedder fallback must not read as a full hybrid result.

**From the 9.1.8 additions (delta §3.2):**

8. **Read-only discipline** — disclosure reads never take locks and never mutate what they read
   (snapshot-read reference behavior: `code.check`/`code.list`, 9.1.8 §2.1); a live writer must
   not block the disclosure path, and an inspection must not refresh state it only observes.
9. **Starvation-vs-refusal distinction** — under stress/starvation, reads stay open (typed
   `WM_HOMEOSTASIS_FROZEN` is not a justification for silent emptiness); insufficiency is reported
   as insufficiency, starvation as starvation, each with its own token.

---

## 4. Ablation

Disabling the mechanism must change a measured outcome; the journal is the instrument (rungs 4–8,
protocol §1).

**Mechanism ablated: explicit disclosure (floors + insufficiency event + per-result chain).**

| Measure | Disclosure on | Ablation | Rung evidenced |
|---|---|---|---|
| `insufficient_evidence` emissions on an all-below-floor query | exactly 1 per query | 0 (hits silently listed or empty) | EXECUTED |
| `provenance.chain.complete` rate | 100 % of returned results | uncomputable / incomplete | EFFECTFUL (journal-visible state change) |
| Silent-empty count (reads with zero hits and zero events) | 0 | > 0 | EFFECTFUL |
| Journal hash-out linkage (N4) | per-run manifest `journal_ok` + hash | run invalid, not silently unmeasured | PERSISTENT |

Not claimed: RE-ENTERS — disclosure changes what is *explained*, not what is *ordered*; an
ordering delta under this ablation is a defect, not a result (the wave row keeps ranking behavior
under test).

---

## 5. Acceptance + owner

Wrapper-side evaluation (harness reads journals; counts generated, never narrated):

1. **Provenance completeness (C4 template)** — every returned result has
   `provenance.chain.complete = true`; rate computed from the journal, expected 100 %.
2. **Explicit insufficiency** — all-candidates-below-floors query yields exactly one
   `insufficient_evidence` event and zero hits; never a silent empty.
3. **Floor bounds** — boundary table passes; out-of-range refuses fail-closed.
4. **Vocabulary uniqueness** — the journal contains only tokens from the closed reason set; counts
   per token generated from the journal.
5. **Audit visibility** — the labeled-conflict fixture reports its audit flag with no score
   adjustment (raw + adjudicated reporting).
6. **Degraded-route honesty** — stub-embedder run discloses its route and never reports hybrid.

**Owner:** unset — operator assigns at spec time.
**Exit criteria (wave plan §2):** frozen spec + adversarial cases wired + ablation designed and,
where implemented, demonstrated + journal events declared (above) + receipt; **no inert acceptance
test**.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W1_SPEC_A2_FREEZE_<date>.md` (spec sha256 + verified pins +
      session attestation)

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; the spec text changes by a new frozen revision with its
own receipt. Nothing in this spec authorizes code by itself; implementation follows the row's
gate.
