# Phase 4 — Wave-1 findings (deep pass)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_GEN1_TREE.md` (§4 worklist). Format per row: **observed behavior · selection history ·
candidate Gen3 expression/manifest · adversarial cases · ablation**.

---

## Row 3 — Revisions/supersession

**Ancestor (v26):** `core/memory/temporal_kg.py` — the Temporal Knowledge Graph ("Gap C" of the
Memory & Cognitive Systems Strategy 2026); fact vocabulary in `unified_types.py` (LinkType:
`related · extends · contradicts · supersedes · temporal · causal · cascade`).

**Observed behavior.**
- Facts stored as `(subject, predicate, object, valid_from, valid_to, superseded_by)` in a
  dedicated SQLite table (`temporal_kg.db`); `is_current = valid_to is None and superseded_by
  is None`.
- `assert_fact(subject, predicate, object, valid_from, supersede=True)`: asserting a new fact
  marks existing current facts for the same key superseded.
- Queries: `get_current_facts`, `get_fact_history`, `changes_since(date)`.
- **Search coupling (FAMA):** fresh facts get a temporal **boost +0.15**, superseded facts a
  **penalty −0.20**; `get_superseded_memory_ids()` lets retrieval exclude them.
- Facts do **not** enter themselves: population requires `extract_and_assert` (extraction from
  memory text).

**Selection history.** v26 needed (a) an extraction step, (b) a separate fact DB, (c) an inline
score adjustment. Gen2 kept revision chains and currentness as *behavior*; Gen3's R earned
currentness as a derived relation (`shared-rare + value-diff + temporal` → `supersedes` edges +
structural strata) with **no extraction stage and no score nudges**. The homology is
"prefer the current value when state changed"; the organs differ completely.

**Candidate Gen3 expression.** Already compiled (pass: CLEANLY → compile; E2/E3). Manifest for
any future hardening: wire = typed `supersedes` relation + strata (existing); acceptance = the
adversarial battery below; owner unset.

**Adversarial cases (for the frozen spec).**
1. Same subject+predicate, genuinely different predicate senses ("prefers Rust" vs "wrote
   Rust") — v26 extraction would over-supersede; R must not.
2. Facts with no `valid_from` — FAMA degrades to no signal; test temporal-absence explicitly.
3. The labeled answer *is* the superseded value (the LABEL/state-conflict class): v26's −0.20
   penalty makes this worse; Gen3 must keep testbed-audit flags visible rather than tune.
4. `changes_since`-style window queries — confirm Gen3 can answer them from the journal without
   a fact table (journal-as-evidence).

**Ablation.** Disable R → ordering should revert (already proven A1/A4 on MemoraStrict; keep
for any successor corpus).

## Row 1 — Store/dedup mechanism

**Ancestor (v26):** `core/memory/deduplication.py` ("Campaign C001: Quarantine
Rehabilitation") + per-backend `content_hash` primitives (`backends/*`: `find_by_content_hash`,
postgres upsert; `galaxy_manager` cross-galaxy hash skip; `sqlite_schema` content_hash since
v14.1.1) + search-side near-dup filter (`enable_dedup`, `dedup_threshold: 0.85`).

**Observed behavior.**
- **Dedup was cleanup, not a gate:** content SHA-256 existed as a column and in some backends,
  and duplicates were hunted post-hoc by a rehabilitation campaign (plus noise patterns:
  tracebacks, `Error:`/`Exception:` lines, raw JSON blobs, function reprs, < 10 chars).
- Result: the migration inventory found **59,831 rows / 35,930 distinct → 37.2 % internal
  dup** (matrix §2.1) — accumulation happened first, cleanup never finished.
- Near-duplicate *search* filtering existed but at a tuned 0.85 threshold; exact-hash caching
  (`find_by_content_hash`) is the mechanical half.

**Selection history.** Gen2 turned idempotence into a property of the *path*, not a campaign:
per-file SHA-256 ingest ledger (9.1.8 onboarding), content-hash embedding cache, and
`memory.deduplicate` as an explicit destructive operation instead of a background purge
(Charter §3.2 rotation-not-deletion is the ruling that Gen1's purge campaigns were missing).

**Candidate Gen3 expression.** Pass row: ingestion gates CLEANLY → compile; the store row
compiles. Manifest for the dedup gate: wire = exact-content-hash refusal + journal entry
(`remember.refusal` reason `duplicate_exact`), near-dup left to selection/ranking disclosure;
acceptance = the cases below; owner unset.

**Adversarial cases.**
1. Exact duplicate across galaxies — scope labels differ; is it the same record? (v26 skipped
   cross-galaxy dup on transfer; Gen3 must decide per scope, not globally.)
2. Same content, different context/episode — must **not** collapse (context is the caller's
   provenance, not the bytes).
3. Near-dup (paraphrase) — the 0.85-style threshold is banned as tuned; any semantic dedup
   needs a declared battery + registration.
4. Noise purge vs quarantine — v26 purged tracebacks; Gen3 may only rotate/quarantine
   (Charter §3.2), and record refusals in the journal.

**Ablation.** Toggle the exact-hash gate; expect duplicate count to rise, no change in
retrieval ordering (a gate, not a scorer).

## Errata candidate — Evidence-disclosure ancestry (found during this pass)

`core/memory/abstention_gate.py` exists in v26 ("Gap D"): abstains when top-result relevance
falls below a threshold (default 0.50, "determined by threshold sweep — TPR 100 % / FPR 0 % on
a 500-memory benchmark"), scoring on cosine + FTS5 overlap + RRF.

The ratified decomposition row says **"Gen1 ancestry: none (Gen2 added)"** for evidence
disclosure. Proposed correction: **v26 had threshold-based abstention**; Gen2 *transformed* it
(declared floors + explicit `insufficient_evidence`, evidence bundles); Gen3 journals it. The
verdict (CLEANLY → compile) is unchanged — this is an ancestry/errata item for operator review,
plus an adversarial case: the abstention contract must not regress into a swept tuned
threshold; floors are declared, never swept.

## Subagent batch 1 (2026-09-17) — file index

Six parallel read-only extractions (Gen1 v26 tree + Gen2 9.1.8 source). Detail lives in
`docs/findings/`; headlines here.

| File | Scope | Headline findings |
|---|---|---|
| `findings/W1_retrieval.md` | retrieval stack | default hybrid = 8-stage planner with weighted RRF (k=60); rerank is **multiplicative on RRF** (entity .25 / importance .20 / recency .15 / lexical .15 / FAMA .10); CE is a 0.6/0.4 blend with async load → warm-up-order non-determinism; `dedup 0.85` = **tag-set Jaccard** (not cosine); abstention 0.50 is standalone/opt-in; retrieve-path HRR = **8-bit qFHRR LUT prefilter** (bind is write-side; its cache module is absent) |
| `findings/W1_sessions_continuity.md` | sessions/continuity | turn taxonomy is **machine-generated** (middleware auto-records tool calls) — the 21,351 turns are a tool-call log; turns written through a private backend handle, **bypassing ingestion gates** (consistent with the 37.2 % dup); `current_state.py` dual-store with a cap-bypassing `update()`; "Total Recall" is three divergent paths; `continuity/grounding.py` etc. are **dormant** (no importers) — name ≠ function |
| `findings/W1_coordination.md` | coordination | v26 `ResourceManager` was **advisory-only** (no edit path consults it; silent no-op fallback); collective memory = plain read-modify-write JSON, no lock; handoff single-slot **silently drops** a second session; real parallel-session interference (2026-07-16, turns #904–#925) was handled narratively; v26 `list_locks` mutated while listing — exactly what 9.1.8 `snapshot_readonly` fixes |
| `findings/W1_claims_prescience.md` | claims/prescience | v26 **did ship Brier/Murphy/ECCE** (not just points) — seed set all-validated → degenerate (BS 0.1149, gap −0.332); ledger **destructively syncs** to the YAML seed (runtime rows erasable by curation); points not mechanically reproducible (6/52 rows deviate; sum 1,474.3 vs header 1,468); external-validation = free-text human curation; "external convergence" = org-name regex |
| `findings/W1_galaxies_compartments.md` | galaxies/compartments | galaxies were **single-valued physical containers** (one column, one SQLite DB per name; no enum enforcement, no cap); taxonomy **advisory only** (never called by the write path); isolation partially wired (search/assoc filter, not transfer); compartments = shelter templates with **silent degradation** and Dharma fail-open on engine error; 47-DB fd exhaustion has a visible mechanism but no source attestation |
| `findings/W1_gen2_source_map.md` | Gen2 9.1.8 map | load-bearing pointers per wave-1 row (write gate, ingest ledger, bundle v0, hash-chain revisions, episodic anchors, checkpoint pair, leases + strict asymmetry, capability gate/tokens, claims, galaxy caps, retention). Four divergences flagged — see below |

## Consolidated errata candidates (dispositioned 2026-09-17 — see `PHASE4_ERRATA.md`)

1. **Retrieval ancestry:** active embedder constant is `BAAI/bge-small-en-v1.5` (MiniLM-L6-v2
   survives only in a docstring); `HRR circular convolution + 4-bit qFHRR` should read
   **8-bit qFHRR LUT prefilter** with circular-convolution `bind` write-side (cache module
   absent); "HRR coords" conflates qFHRR with `CoordinateEncoder` — two different organs;
   the 0.85 "near-dup" filter is **tag-set Jaccard**, not embedding cosine. Fix the wave-1
   tree row and note the matrix §2.3 conflation.
2. **Coordination ancestry:** `sangha_memory_collective` is not attested in the v26 tree; the
   artifact is `.../sangha/memory/collective/` dirs dated 2026-05-29. Reword tree §2 row 6.
3. **Galaxies ancestry:** matrix §2 L63's "fail-closed unknown values (v4.3.0)" is not present
   in v26 source (nearest: empty default capabilities + silent tier degradation); the
   compartment→galaxy access mapping appears Gen2-side. The 47-galaxy sprawl is
   **narrative-only** (mechanism plausible; no attestation) — tree row marked down from ✓.
4. **Sessions counts:** the nine turn-type counts sum to 16,859 vs CITTA 18,204 → **Δ1,345
   unaccounted** (flagged UNVERIFIED); plus a dual-default truth-hygiene item
   (`session_record` default False in settings vs middleware default-on unless env == "0").
5. **Claims provenance nits:** stale CLI docstring/test numbers; TZPF vs `summary()` diverge on
   `expired` handling. No verdict or ancestry change.

## Migration-spec divergences flagged (Gen2 source map)

1. Findings use journal vocabulary (`remember.refusal` / `duplicate_exact`); 9.1.8 dedup is a
   **non-journaled short-circuit** + `write_gate` disclosure with `dup_count`/importance decay
   — specs must say which side implements the disclosure.
2. E11 cites checkpoint work to `session_ops.rs`; the 9.1.8 checkpoint + `checkpoint_nodiscovery`
   live in `wm-tools/src/expansion/session.rs` — a spec reading only `session_ops.rs` misses the
   migration target.
3. **No first-class `supersedes` relation exists in Gen2** — currentness is hash-chain
   revisions + episodic change-marker anchoring (`superseded-by:` tags only on session turns).
   Gen2 is behavior, not relation; Gen3's R is the relation-form. Do not claim Gen2 agreement.
4. Cap-20 galaxy registry vs a possible physical bypass path; `_meta.compartment` is membership,
   not authenticated authz — UNVERIFIED items carried into the specs.

## Remaining open questions (aggregate)

Live-data claims that need a data/host check before being used in any spec: the 16,219
embeddings / 0.26 ms figures (docs-corpus only); whether HRR prefilter or abstention were ever
default-active in shipped flows; whether oracle/time-estimate claims were actually deleted in a
live state DB; the 2026-05-29 collective origin event; the two-writer postmortem document
itself; the "batch docs" mapping (only Jul-27 benchmark JSONs found). Queued but not yet
extracted: `constellations.py` / `constellation_algorithms.py`, `association_miner.py` /
`causal_miner.py`, `unified_types.py` LinkType vocabulary (wave-2 material).
