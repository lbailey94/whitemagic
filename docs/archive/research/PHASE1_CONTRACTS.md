# Phase 1 — Field & Operation Contracts

**Status:** working draft for review · 2026-09-16 · companion to `PHASE1_EXPERIMENT_INTERFACE.md` ·
**not binding until referenced by the pre-registration at freeze.**

Constraints adopted for this document (recorded 2026-09-16): the **anti-bloat law** ("every
mechanism must justify why it belongs in the substrate rather than emerging from it; deletion is
the judge"), the **six-question selection-contract template**, a **one-page budget per
operation**, the **ablation-debt ledger**, and the **implementation gate** (if the implementing
session needs a module this document does not name, this document goes back to review).
Storage decision: **LMDB from the start** (durability is mandatory — the harness reopens the
store per query; same crate family as the control for storage-physics parity).

---

## 0. Template and rules

**Scope of the claim under test.** Phase 2 tests one narrow proposition: *a single predeclared,
ablatable temporal-relation primitive plus generic selection reproduces multiple historically
separate Gen2 behaviors without importing their behavioral machinery.* It does **not** test
broad emergence — relation promotion, clustering, higher-order structure and constellation
formation are later concerns (§2.3.6, Phase 3).

Every operation answers the same six questions (≤1 page each; overflow goes to §6, not here):

1. **Population** — what can it see?
2. **Influence** — what information may influence selection?
3. **State change** — what is it permitted to change?
4. **Refusal** — what conditions force refusal (vs abstention)?
5. **Inspect** — what must `inspect` expose afterward?
6. **Intrinsic vs emergent** — which behavior is built in; which must arise from repeated
   application? (Anything intrinsic with behavioral teeth owes an ablation entry — §5.)

Two standing prohibitions apply to every implementation: no hidden modules (implementation gate),
and no symbolic system may dispatch (`CHARTER.md` §3.10).

---

## 1. Minimal substrate schema

### 1.1 Record (`x`) — the durable epistemic object

| Field | Type | Notes |
|---|---|---|
| `id` | opaque stable string | returned by `remember` in input order; echoed by `recall` (interface I6) |
| `content` | text | verbatim corpus/turn content in Phase 1 |
| `class` | `evidence \| belief \| speculation` | set at construction; corpus import = `evidence` |
| `domain` | `world \| system \| simulated \| reported` | set at construction; corpus import = `reported`; **immutable** (Closure 2, v0.1.1) |
| `source` | string/ref | import provenance (e.g. `bench_seed1:session_004:turn_3`) |
| `provenance` | chain | origin → creation path → (any) derivation links; append-only |
| `confidence` | f32 ∈ [0,1] | asserted-state confidence, not relevance |
| `horizon` | enum/optional | validity expectation (Phase 1: `open`) |
| `status` | `transient \| candidate \| persistent \| cold` | lifecycle (§1.3) |
| `created_at` | source time + ingest time | both, when available |

### 1.2 Relation (`e`) — the adaptive field edge

Minimal form `e = (w, s, c, t)` per consensus (`DESIGN_CANON.md` §4):

| Field | Meaning |
|---|---|
| `w` | learned strength (support/usage reinforced) |
| `s` | sign/direction (relation polarity) |
| `c` | resource cost (selection weight against expensive structures) |
| `t` | trust/confidence |

Plus the minimum identity fields: `id`, `kind` (Phase 1: `supersedes` only — §2.3), `src`/`dst`
record ids, `class` (= `speculation` until reinforced), `created_by` (rule id + contributing
record ids), `created_at`, `state` (`candidate | persistent | cold`). Relations are adaptive state;
they are never evidence about the world (Closure 2).

### 1.3 Lifecycle

`transient → candidate → persistent → cold`; rotation not deletion; snapshot before mutation.
Phase 1 application: corpus-imported records enter `persistent` (authoritative input);
inferred relations enter `candidate`, and promotion/demotion is **owned by `think`** under
statutory policy (§2.3, A6): `persistent` after surviving ≥1 sweep and appearing in ≥1 journaled
selection; `cold` after K unused sweeps. `recall` journals usage but never mutates lifecycle
state — no unnamed maintenance subsystem exists. No lifecycle state change may alter `class`,
`domain`, or `content`.

### 1.4 Journal (append-only)

Decisions and refusals are recorded so `inspect` and the experiment can audit them: relation
proposals + outcomes, selection decisions (population considered, rule applied, chosen), refusal
events, canary probes, and violation events (schema: `CLOSURE_TESTS.md` §3). The journal is the
observable surface the interface doc's §5 instrumentation reads.

---

## 2. Operation contracts

### 2.1 `remember` — what earns persistence

1. **Population:** the batch of candidate records presented in the call; nothing else.
2. **Influence:** declared fields only (`content`, `class`, `domain`, `source`, `confidence`,
   `horizon`) plus statutory intake rules. No inference may *add* world-evidence; no field may
   be silently upgraded (Closure 2).
3. **State change:** creates records and appends journal entries. It does **not** create
   relations, does not modify existing records, and does not call `think` (see §2.3 invocation
   policy).
4. **Refusal (not abstention):** invalid/missing `class` or `domain`; `domain = world` without a
   ratified channel (already structurally enforced); malformed batch; budget-exceeded
   (fail-closed per Charter §3.1) — all refusals are loud, structured, and journaled.
5. **Inspect:** for each id — class, domain, source, provenance chain, lifecycle state, and any
   refusals from the call.
6. **Intrinsic vs emergent:** intrinsic = validation, id assignment, append-only writes.
   Emergent = nothing (a store must not be clever).

### 2.2 `recall` — current-state reconstruction, not a filing cabinet

1. **Population:** all records in scope (Phase 1: the single substrate store). Retrieval
   candidates = lexical matches over `content` (stock engine allowed) ∪ records reachable through
   relations from lexical candidates (bounded hop budget — statutory).
2. **Influence:** the query text; request constraints (`limit`, `candidate_limit`, `min_score`,
   `min_coverage`, `include_historical`); relation trust `t` and cost `c`; lifecycle `status`;
   recency/source time. **Not permitted:** corpus-specific keyword lists, hardcoded session ids,
   the `has_answer` import tag as a relevance signal.
3. **State change:** **none** (read-only; journal entry only). Currentness is resolved by
   ranking, not mutation.
4. **Refusal:** never — an empty selection is an **abstention** (empty `results` list, per
   interface I7), not an error. Resource exhaustion may refuse loudly (fail-closed).
5. **Inspect:** per result — why it was selected (which candidates, which rule, scores
   contributed), its currentness state (active / superseded-by-X with relation id), and the
   abstention reason when empty.
6. **Intrinsic vs emergent:** intrinsic = candidate generation, scoring, ranking, current-state
   ordering. Emergent = none claimed in Phase 1 (any "smart" behavior must come from relations
   `think` proposed, not from recall heuristics).

**Score convention (pinned here, interface I8):** each result carries `score ∈ [0,1]`; records
below the statutory relevance floor report `< 0.01`; a query whose best candidate is below floor
returns either an empty list or sub-floor scores (T2 abstention depends on this; no silent
mid-scale returns).

**Currentness policy (pinned here):** `include_historical:false` means **current-preferred
ranking, not exclusion** — historical/superseded records remain retrievable, ranked below
current ones unless query relevance overwhelmingly favors them. Rationale: (a) T1 needs the
current value at rank 1 while T8 needs both sides of a change visible in the top 10
(interface §4); both are satisfied by one policy; (b) dropping records silently contradicts the
substrate's abstention culture. This is a Gen3-side interpretation of a shared request argument;
it is documented pre-freeze and applies to both arms only as each system implements it.

### 2.3 `think` — relation candidacy (the honest core of the experiment)

1. **Population:** records/newly ingested content in the epoch the sweep is told to consider
   (Phase 1: the post-ingest window; explicit invocation only).
2. **Influence:** record text, source times, provenance, existing relations. Not permitted:
   corpus metadata (`metadata.old_fact` etc. are **not** visible to the substrate), session ids
   beyond provenance, or benchmark labels.
3. **State change:** creates **candidate relations** (§1.2) and journal entries; evaluates
   statutory promotion/demotion of existing relations at sweep time (§1.3). Promotion is owned
   here, never by `recall`. Never mutates records. Never asserts world-evidence; relation
   `class = speculation`.
4. **Refusal:** budget-exceeded (bounded sweep — statutory pair budget), malformed input.
5. **Inspect:** every proposal with its contributing records, the rule that proposed it, and the
   score components; plus the current promotion state.
6. **Intrinsic vs emergent:** intrinsic = exactly the candidacy rule below (declared, ablatable).
   Emergent = relation promotion, clustering, higher-order structure (Phase 3 concerns).

**Pre-declared candidacy rule (Phase 1, single relation kind `supersedes`).** Two records are
co-referent if they share ≥1 extracted subject key (rare content terms after stopword filtering,
plus shared provenance-topic when derivable). A record *asserts a value* when a sentence links a
subject key to a value token through a state/possession/consumption pattern. When two co-referent
records assert different values and one has later source time, `think` proposes
`later → supersedes → earlier`, with confidence from source recency and provenance strength;
ties propose nothing. **No sentiment, no domain semantics, no contradiction lexicon.** The rule
is stated here to be ablated: the Phase-2 candidate arm runs twice, with and without relation
candidacy, and the difference is reported (H8's ablation discipline applied to intrinsic
machinery). If T8/T1 behavior cannot be reached without adding corpus-shaped exceptions, that is
a **loss finding** for the thesis as written — not a license to grow the rule.

**Genericity property test (required before Phase 2, non-scored).** The same candidacy code
path, with no added vocabulary, must identify temporal replacement on a frozen set of
out-of-corpus examples spanning unrelated domains, e.g.: `Alice moved from Atlanta to Denver` /
`the server was upgraded from 2.1 to 2.2` / `the car color changed from red to blue` /
`her role changed from engineer to manager` / `he used to own a bike, now he owns a car`.
These are contract/property tests (`proptest` is an allowed dependency — `DEPENDENCY_MANIFEST.md`
§2), not scored hypotheses. New vocabulary or a corpus-shaped exception fails the test **by
definition**: if the extractor only works on MemoraStrict's linguistic forms, the rule is a
benchmark engine, not a primitive.

**Invocation policy (D1 — resolved):** the adapter triggers one bounded `think` sweep after
each `batch_create` chunk completes. Write-time inference is chosen because the control also
pays inference/indexing cost at ingest, and query latency stays deterministic.

### 2.4 `inspect` — the explanation surface (also the Phase-0 gate obligation)

1. **Population:** substrate state, journal, statutes, constitution view (read-only).
2. **Influence:** the request scope; nothing adaptive may influence what inspect reports.
3. **State change:** none (read-only).
4. **Refusal:** none for permitted scopes; out-of-scope constitutional mutation questions return
   the tier map, not an error.
5. **Inspect (of inspect):** trivially, its own scope and read-only status.
6. **Obligations (from `CLOSURE_TESTS.md` §3):** for any state: tier owner · readers · writers ·
   path · authority; plus selection explanations (`recall`/`think`), violation log, and the
   relation ledger with contribution records. `inspect` must never certify more than the journal
   contains.

---

## 3. Interface obligations (from `PHASE1_EXPERIMENT_INTERFACE.md`)

The adapter (`crates/wm-gen3-harness`, plumbing only) maps `memory.batch_create → remember`,
`memory.episodic_search → recall`, `sandbox.set_limits → statutes`, and triggers §2.3's sweep.
Everything in interface §1's I1–I9 is a hard requirement; in particular: ids stable and ordered,
`results` always a list, `score` per result, no handshake required, durable store reopened per
query process, and no crash on unknown routes.

## 4. What is deliberately absent (Phase 1)

No embeddings/vector search · no contradiction/contradiction-scoring module · no session module ·
no garden/engine classes · no importance/recency scoring ported from Gen2 · no conflict lexicon ·
no LLM calls · no Gardener/Engines · no hyperedges or constellations (Phase 3, evidence-gated).
Every absence is a Phase-2 ablation datum, not an oversight.

## 5. Ablation-debt ledger (each row must eventually be tested or resolved)

| # | Mechanism | Claim it earns its place? | Ablation |
|---|---|---|---|
| A1 | Supersedes candidacy rule (§2.3) | To be proven | candidate arm with sweep disabled vs enabled (T8/T1) |
| A2 | Relation trust `t` as selection weight | To be proven | run with `t` fixed at 1.0 |
| A3 | Bounded relation-hop expansion in `recall` | To be proven | hop budget 0 vs N |
| A4 | Current-preferred ranking policy | To be proven | `include_historical` symmetric vs preferred |
| A5 | Confidence/recency blend in proposal confidence | To be proven | uniform confidence |
| A6 | Relation promotion/demotion policy (survival + journaled use) | To be proven | candidate-forever vs lifecycle |

## 6. Decisions (resolved 2026-09-16, pre-freeze review)

- **D1 — `think` invocation — RESOLVED:** one bounded sweep after each `batch_create` chunk
  (write-time inference; query latency stays deterministic).
- **D2 — score scale — RESOLVED (constant pinned at freeze):** fixed, corpus-independent,
  monotone map from lexical score to `[0,1]`; **no per-query or per-corpus min/max
  normalization** (a max-normalized best match would read `1.0` even when irrelevant — banned);
  zero lexical overlap → `0.0`; the `<0.01` abstention floor is a harness convention applied to
  the mapped score. The map's one constant is pinned in the frozen pre-registration and checked
  for floor behavior during the declared non-scored smoke run — never tuned on benchmark results.
- **D3 — relation kinds — RESOLVED:** `supersedes` only; "conflict" is a derived analytic label
  (co-referent incompatible values) for H3/H8 counts — no second stored kind.
- **D4 — promotion policy — RESOLVED, no hidden module:** owned by `think` at sweep time:
  `candidate → persistent` after surviving ≥1 sweep **and** appearing in ≥1 journaled selection;
  `→ cold` after K unused sweeps. Both numbers are statutory and inspectable; `recall` never
  mutates (A6).
- **D5 — lifecycle breadth — RESOLVED:** corpus imports fixed at `persistent`; lifecycle
  machinery exercised on inferred relations only, so the experiment cannot silently depend on
  cooling behavior.

## 7. Review gate

This document is the interface the implementation session may rely on **only after** the open
decisions above are resolved and the document is referenced by the frozen pre-registration.
Any module need not named here returns this document to review: that is the implementation gate
working as intended, not a blocker.
