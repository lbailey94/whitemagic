# Phase 4 — Errata register (batches A–N)

**Status:** dispositioned 2026-09-17 · read-only research ledger. Tracks every erratum raised by
the wave-1/2 findings against ratified or working texts: what it corrects, where the fix landed
in-repo, and which items need dev-journal (matrix/ledger) updates by the operator. **No verdict
changed**; no threshold, claim, or gate touched.

Sources: `PHASE4_WAVE1_FINDINGS.md`, `PHASE4_WAVE2_FINDINGS.md`, `docs/findings/W1_*.md`,
`docs/findings/W2_*.md`.

---

## A. Landed in-repo (working documents corrected)

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 1 | Retrieval ancestry: "MiniLM-L6-v2 384d" | active embedder constant is `BAAI/bge-small-en-v1.5`; MiniLM survives only in a stale docstring | `PHASE4_GEN1_TREE.md` wave-1 row (batch 1) |
| 2 | Retrieval: "HRR circular convolution + 4-bit qFHRR"; "HRR coords" | retrieve path uses an **8-bit qFHRR LUT prefilter**; circular-convolution `bind` is write-side (its cache module is absent); coords come from `CoordinateEncoder` — two organs conflated | tree row corrected (batch 1) |
| 3 | Store: 0.85 "near-dup filter" implied embedding cosine | it is **tag-set Jaccard** inside the Rust pipeline (`search_similar` only) | tree row corrected (batch 1) |
| 4 | Evidence disclosure: "Gen1 ancestry: none (Gen2 added)" | v26 `abstention_gate.py` existed (0.50, sweep-derived) → Gen2 **transformed** it | `PHASE3_DECOMPOSITION.md` row + E4 errata (inline); register §C |
| 5 | Coordination: "`sangha_memory_collective` file board" | not attested; artifact is `…/sangha/memory/collective/` dirs dated 2026-05-29 | tree §2 row corrected (batch 1) |
| 6 | Galaxies: "47-galaxy sprawl incident ✓" | **narrative-only** (mechanism plausible: per-galaxy backends + pools; no source attestation) | tree row marked down (batch 1) |
| 7 | Associations row ancestry: "typed links + Hebbian → folded" | v26 typing **never survived a save** (kind/direction reverted); Hebbian was **dormant in v26** but is **live in Gen2's mechanism** (serving-path absent); verdict unchanged | register §D-1; decomposition §6 pointer |
| 8 | Engines: "SkillForge is metadata-only today" | true for **Gen2**; v26's SkillForge **ran and persisted 33 skills** over a 4-verb vocabulary, write-only replay | register §D-2; decomposition §6 pointer |
| 9 | RSI: "906 → 36 → 29" implied a healthy loop | annotate ratios: 4.0 % outcome coverage, 2/36 success (one event twice), 1/29 nonzero correlations; "friction" is Gen2 vocabulary | `PHASE4_WAVE2_FINDINGS.md` index (batch 2) |
| 10 | Sessions counts | Δ1,345 unaccounted (turn types sum 16,859 vs CITTA 18,204) — **UNVERIFIED**, flagged; machine-generated taxonomy documented | `PHASE4_WAVE2_FINDINGS.md`; W1 sessions file |

## B. Landed as methodology notes (no text changed)

| # | Note | Action |
|---|---|---|
| 11 | Default `rg` traversal silently skips `core/memory/sqlite_backend.py` (ignore rules) — wave-1 counts may undercount there | recorded in `W2_retention_lifecycle.md`; if any row's counts become load-bearing, re-run with `--no-ignore` |
| 12 | Dream phases: Gen1 `DreamPhase` = **13** members vs Gen2's 12; `LearnedDreamCycle` reordering is Gen2-only | captured in `PHASE4_WAVE2_FINDINGS.md` errata #4 and decomposition §6 note |

## C. Dev-journal / matrix items owed to the operator

These live outside WMgen3 (matrix at `~/Desktop/dev journal/WHITEMAGIC_GEN1_VS_GEN2_CAPABILITY_MATRIX_2026-09-16.md`,
ledger at `~/Desktop/WHITEMAGIC-NOTEBOOK/LINEAGE_LEDGER.md`); WMgen3 sessions do not edit them.

| # | File | Item |
|---|---|---|
| C1 | matrix §2.3 (L58) | embedder MiniLM → `bge-small-en-v1.5`; qFHRR 8-bit; HRR/coords conflation |
| C2 | matrix §2.4 (L115) | dream phase count 13 (Gen1) vs 12 (Gen2); `LearnedDreamCycle` Gen2-only |
| C3 | matrix §3 (L163) | "session stream was mostly citta stream" — storage-label artifact; real taxonomy is `turn_type` |
| C4 | matrix §2.1 (L62–63) | galaxies: taxonomy advisory-only; sprawl narrative-only; "fail-closed unknown values (v4.3.0)" not found in v26 source |
| C5 | LINEAGE_LEDGER feedback-controller row | annotate 906/36/29 with coverage/success/correlation ratios |
| C6 | LINEAGE_LEDGER emergence row | conflates ≥3 organs (zombie / hardcoded+random / real SQL detector with 329 insights) |
| C7 | matrix path citation (`PHASE3_DECOMPOSITION.md` line 10) | cited as `~/Desktop/…`; actual location is `~/Desktop/dev journal/…` (§C header is correct). Inline fix deferred; **matrix v2 written 2026-09-17** (`WHITEMAGIC_GEN1_VS_GEN2_CAPABILITY_MATRIX_2026-09-16_v2.md`, scoped: nucleus + waves 1–2 corrections C1–C4 + A#7/#9) |

## D. Decomposition §6 pointers (additive errata)

- **D-1 (associations/E6):** typing never persisted in v26; Hebbian dormant there, live in Gen2
  mechanism. The "edges compile, dynamics parked" verdict is strengthened, not changed.
- **D-2 (engines/E16):** E16 should read "whole-call trace mining existed (33 persisted skills,
  4-verb vocabulary); the operator-level runtime did not." The Gen2 "metadata-only" statement
  stands for Gen2.
- **D-3 (citta/E15):** Gen1 13 dream phases vs Gen2 12; CITTA headline is a label artifact.

## E. Unresolved (carried, not decisions)

Live-data verification items remain aggregated in the two wave masters (no Gen1 DB on host,
doc-only counts, comment-sourced figures). They block nothing at the wave-plan level but must be
cleared before any migration spec cites them as measured.

## F. Batch 3 additions (lenses · strange Gen1 · hard remainder)

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 13 | Field integration (wave-2 claim) | v26's read-side spreading-activation channel **was live** in the default planner (RRF six-channel; only priming write-back was tool-only) — W2 claim corrected | `W2_citta_dream_cycles.md` in-place correction + `PHASE4_WAVE3_FINDINGS.md` |
| 14 | `THEORY_MECHANISM_MAP.md` §3.3 "activation with 300 s half-life" (Gen2) | the 300 s half-life is **declared, `tick_decay` never called** — activations saturate, never decay | landed in the map's §3.3 row (2026-09-17) |
| 15 | E21 / reflex ancestry "none (Gen2 added)" | v26 had **dormant sensing** (no actuator/e-stop code) — wording correction only | `PHASE3_DECOMPOSITION.md` §6 note + `PHASE4_WAVE3_FINDINGS.md` |
| 16 | "Geneseed" name | shipped twice as *different* functions (Gen2 git miner; v26 `GeneseedVault` template forker); "concept only" is right for the **V9.1 lineage design** only; Gen2's Q04 disposition = "Retire (code)" | errata ledger; decomposition EXPERIMENT row unchanged |
| 17 | Route counts live vs tag | **303/86/217 on 9.1.9-dev main vs 302/85/217 at the v9.1.8 tag** — Track A release figures stand; live counts must say "main" | `PHASE4_GEN2_DELTA.md` §1 footnote (this register) |
| 18 | Simulation row | `sim` = 4 routes (adds `simulation.calibrate`); the row bundles three disjoint organs; Gen1 had two distinct `simulation.status` handlers | `PHASE4_WAVE3_FINDINGS.md` |
| 19 | Mesh precision | keyless beacons for a **bound** peer are dropped, not merely hints (`transport.rs:1213-1232`) | `PHASE4_WAVE3_FINDINGS.md` (delta §2.2 precision note) |
| 20 | Reflex safety posture | safety mask **inert in production** (`permissive()` = SAFETY_ALLOW_ALL); daemon "7 cycles" vs 8; e-stop docs vs `SAFETY_DENY_ALL`; `SAFETY_DEFAULT` doc mismatch | `PHASE4_WAVE3_FINDINGS.md`; migration-spec warning |

No verdict changed by any batch-3 item. Item 14 landed in the theory map; the rest are captured
in the wave masters.

## G. Intermission additions (runtime evidence, 2026-09-17)

The wave-0 intermission supplied Gen1's runtime record. These are corrections to **conclusions**,
not verdicts; detail in `PHASE4_WAVE0_SESSIONS.md` and `docs/findings/W0_*.md`.

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 21 | "Gen1 = Jan → Aug 2026" timeline | **Lived substrate era ≈ late May → Aug 2**; Jan–Jun session rows are a **back-filled import** (2,166 of 2,269 ingested Jul 30–31); `created_at` is a source date | `PHASE4_WAVE0_SESSIONS.md` §2; protocol §4 |
| 22 | The runaway incident | **Unattested by Gen1's own record** — no doc, ledger, or self-state row describes it; the 2.4 GB/110 %/SIGKILL story is external only; the 284 zombie dreams date **Jun 27–Jul 20**, pre-endgame; what the record shows is unattended bookkeeping churn + cost inflation, then the record stops | `PHASE4_WAVE0_SESSIONS.md` §3; W0 files |
| 23 | "37.2 % internal dup" scope | Applies to the **migration/live-store inventory**, not codex; codex exact dup = **0.05 %** (its bloat is the 1.2 GB FTS5 shadow copy + 693 MB binaries) | `W0_codex_galaxy.md` |
| 24 | Aria provenance precision | Authorship artifacts: 2025-11-19 → 2026-07 (not "2026-05 →"); 204-row DB **verified**; `aria` galaxy is **8/256** genuinely pre-2026; "October 2024 seed" backdated (first commit 2025-11-02); **no Book of Becoming in any DB** | `W0_earliest_memories.md`; identity RETIRE strengthened |
| 25 | Brier figure identity | v26 runtime ledger = **0.2563 overall / 0.0731 time_estimate**; `citta/calibration.jsonl` has **no Brier** (CRPS only); the 0.078 figure belongs to **Gen2's live-store ledger** (different artifact) | `W0_state_ledgers.md` |
| 26 | "No CORRECT ever" (RSI) | Holds for `harmony/` only — `whitemagic_dream.log` carries **361 CORRECT lines**; the graduated ladder fired somewhere | `W2_rsi_selfmodel.md` in-place note |
| 27 | 329-insight emergence claim | **Not visible at the tool layer** (zero `emergence.*` rows in July); downgraded to "recorded in a state file, no execution trace" | `W2_constellations_emergence.md` in-place note |
| 28 | Docs corpus counts | 156 docs, not 166 (51 zero-byte); "no Feb–Jun sessions" was a corpus artifact; "near-silence after Jul 10" was the **tool layer only** (session bursts ran to Jul 16) | `W0_docs_timeline.md` |
| 29 | `token_economy.jsonl` | Mostly **real call instrumentation** (99.5 % without external-token accounting) — the economy ruling's "all test data" needs this footnote | `W0_state_ledgers.md` |
| 30 | "21,351 middleware turns" | ~**10.6 % are imports**; handoff machinery wrote **no payload** (all 24 shells empty) — W1's single-slot finding is runtime-worse, and Gen2's checkpoint fields are a genuine addition | `W0_early_sessions.md`, `W0_handoffs_sessions.md` |

**Consequence:** no Phase-3 verdict changes; six prior findings change evidence level (five
upgraded to runtime-observed, one downgraded). The protocol rules earned here — timeline
provenance, per-claim evidence levels, the ladder — are recorded in
`WAVE_EXTRACTION_PROTOCOL.md`.

## H. Construction-phase additions (2026-09-17 evening)

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 31 | Regression methodology vs recorded cells | Recorded all-off cells **predate the A1 exact-hash gate**; raw corpora carry spec'd `duplicate_exact` refusals. Standard regression recipe = **gate-neutralized corpus** (dedup by gate identity, scripted + hash-recorded) compared against a source-frozen reference and/or recorded cells; ordering/metrics exact, scores ≤ 1 f32 ULP | `WAVE_EXTRACTION_PROTOCOL.md` §9; `IMPL_B1_ACCEPTANCE_2026-09-17` §3 |
| 32 | Binary hashes as "pins" | Builds are **not byte-reproducible** on this host (two fresh builds of frozen `7ff9181` differ; `b1c66fec` not reproduced; a test-only edit changed the release hash `76083d05`→`7046db3f`). Hashes are **instance labels**; behavioral pins (canaries, MANIFESTs, ordering diffs) are the anchors; S7 bumps record fresh canaries + a behavioral baseline, not regenerated build pins | `WAVE_EXTRACTION_PROTOCOL.md` §9; this register |
| 33 | Spec-header hygiene | A1 rev 1 / A3 rev 1 headers were superseded by their rev 2 amendments; **B1, W2_03, W2_07 headers still read "DRAFT"** — the freeze **receipts are canonical**; header reconciliation is optional cosmetics, never a contract change | this register |
| 34 | A3 case 1 (predicate-sense collision) | Frozen rule v1 is **lexical** and links the collision pair (measured). Declared property (A3 rev 2), not a passing prohibition; **rule v2 (value-replacement requirement) is a gated candidate** — re-entry needs its own registration + full corpus re-baseline; the cross-ecology R result must not be risked silently | `docs/specs/W1_A3_revisions_supersession.md` rev 2 §3; `W1_SPEC_A3_AMEND_2026-09-17` |
| 35 | Reproducibility vocabulary (prospective) | Three identities now named and never conflated — **source identity** (commit/tree/toolchain), **artifact-instance identity** (binary sha256; an instance label), **behavioral equivalence** (a demonstrated condition under a stated criterion). Corpus transforms are first-class records with `transform_id` + lineage (`gate-neutralize.v1.2026-09-17` first instance) | `WAVE_EXTRACTION_PROTOCOL.md` §9; `receipts/transforms/TRANSFORM_gate_neutralize_v1_2026-09-17.md` |
| 36 | Standing-authorization breadth (W2 batch freeze §2) | The recorded instruction ("continue with all remaining batches, items, slices, and phases") is a standing authorization for **progression through queued work and owner-assigned slices only**; it does not satisfy, waive, or supersede any explicitly named review, registration, evidence, or operator gate | `receipts/W2_SPEC_BATCH_FREEZE_CLARIFICATION_2026-09-17.md` |
| 37 | F-1 score-stability bound on B5 regression | Scorer summation/iteration order nondeterminism (1 ULP same-binary baseline noise; candidate-vs-reference max 2 ULP) resolved by Scorer Determinism Unit: declared reduction orders (token-order `total_idf`, sorted-context dispersion entropy, sorted-key sweep pair enumeration). Same-binary reruns reach **0 ULP (100.00% exact bits)**; ordering/metrics 0 diffs; cross-build codegen band vs un-fixed reference disclosed (max 2 ULP in 16/650 entries) | `receipts/IMPL_SCORER_DETERMINISM_2026-09-18.md`; `crates/wm-gen3-core/src/ops.rs` |

**Consequence:** no verdict changes. The regression recipe and pin wording are now protocol rules
(§9); A3 exits on a declared-property basis with rule v2 gated; stale headers are receipts-canonical;
standing authorization is bounded by named gates (this register #36); F-1 resolved with same-binary
0 ULP determinism verified (#37), unblocking B5 row exit.

## I. Documentation-sweep additions (2026-09-19)

Landed by the docs-sweep session (batch 1) after the milestone era. No verdict, claim, gate, or
threshold movement; frozen artifacts (nucleus, specs, receipts) were not edited.

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 38 | B5 spec-hash citation: `docs/ROW_EXIT_PACKET_B5_W2.md` and `receipts/W1_ROW_EXIT_B5_2026-09-18.md` cite `606ea2bf…` | canonical frozen hash is `80a99e62…` (`receipts/W1_SPEC_B5_FREEZE_2026-09-17.md`; on-disk file re-hashed 2026-09-19). `606ea2bf` matches no committed instance of the spec — the file has a single committed version (`3d67663` → `80a99e62`), and the string entered in `500a7ff`. Packet corrected in place; the exit receipt is append-only → corrections recorded here + in `receipts/DOCS_SWEEP_BATCH1_2026-09-19.md` | `docs/ROW_EXIT_PACKET_B5_W2.md` line 10 |
| 39 | Spec-header hygiene (#33) inventory was incomplete | the DRAFT status line (`**Status: DRAFT — compiled 2026-09-17 · NOT frozen.**`) is present in **13 frozen specs** (A2, B1, B2, B3, B4, B5, W2_01, W2_02, W2_03, W2_04, W2_05, W2_06, W2_07) plus the prep note `W2_02_04_ACCEPTANCE_PREP.md` (DRAFT accurate; already cites #33) | this register; headers not edited (hash-pinned artifacts; reconciliation = versioned re-freeze, never cosmetics) |
| 40 | `docs/NUCLEUS.md` header reads "DRAFT — compiled 2026-09-17 · NOT frozen" | the nucleus is operator-ratified-frozen: sha256 `73c5a9cf…` (`receipts/NUCLEUS_FREEZE_2026-09-17.md`; canaries C1–C6 PASS) — receipts are canonical | this register; artifact not edited (hash pin) |
| 41 | PEB numbering: `docs/GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md` §6/§7 use pre-execution numbering | executed sequence (receipts + code) is canonical: PEB-10 pulse compiler · PEB-11 sovereign mesh · PEB-12 conformal · PEB-13 geometry · PEB-14A/B/C transport/relativity/hologram · PEB-15 kernel graduation. The doc's PEB-10/11 entries are swapped relative to execution; its PEB-13/14 differ in content; PEB-15 is absent | this register; ratified doc not edited |
| 42 | Top-level orientation stale vs the milestone era | `README.md` status block + `HANDOFF.md` opener/§1/§3 refreshed to M0–M8C ratified / M9 Gate 9A at `8c13904`; ledger line updated to the reconstructed 8-claim mapping (live `claims.list` verified 2026-09-19) | `README.md`; `HANDOFF.md`; `receipts/DOCS_SWEEP_BATCH1_2026-09-19.md` |

**Consequence:** no verdict changes. The B5 citation now matches the freeze receipt; the
header inventory is complete; the milestone-era state is recorded in the orientation docs.

## J. Documentation-sweep additions, batch 2 (2026-09-19)

Corrections landed while walking the constitutional/design core. No verdict, claim, gate, or
threshold movement; hash-pinned artifacts were not edited.

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 43 | Ratified-artifact surface hygiene (frozen text) | `docs/CHARTER.md` (pin `957320d9…`) still reads "Draft v0.1.1 · FOR RATIFICATION" with an unsigned signature line, and `docs/NUCLEUS.md` (pin `73c5a9cf…`) leaves §9 steps 4–5 unchecked — both were operator-ratified in fact (`PHASE0_RATIFICATION_v0.1.1_2026-09-16`, `NUCLEUS_FREEZE_2026-09-17`). Frozen texts are hash-pinned and are not edited; receipts are canonical. Pin-time cross-references inside frozen artifacts age by design (e.g. NUCLEUS §7 cites this register at a then-current 30 items A–G) | this register; no artifact edited |
| 44 | `THEORY_MECHANISM_MAP.md` Brier conflation | "Gen2 claims ledger (Brier 0.078)" mixed artifacts — the 0.078 figure belongs to Gen2's live-store ledger; v26 runtime = 0.2563 overall / 0.0731 time_estimate; `citta/calibration.jsonl` carries no Brier (CRPS only); per #25, corrected in place | `docs/THEORY_MECHANISM_MAP.md` §3.1 |
| 45 | `THEORY_MECHANISM_MAP.md` stale on the gated outcome | activation-policy row, bet 3, and sources updated: floor policy FALSIFIED (GATED-S-001/002); count<2 criterion confirmed gate-scoped (GATED-S-003; claim-0007; state resolution only); the ≥2-candidate boundary stays open; entry-gate line rewritten (verdicts live in the ratified decomposition); status line annotated | `docs/THEORY_MECHANISM_MAP.md` §§3.2/6/8 |
| 46 | Phase-state staleness in live docs | "Phase 3 stays blocked" removed in two places — `ARCHITECTURE_CONSOLIDATION.md` §6 and `HANDOFF.md` §4 rule 8 — replaced with the closed-state note (entry decision + compile pass 2026-09-17; R1 remains paused/rejected); the consolidation's "open thread 8 in HANDOFF" cross-reference corrected to "HANDOFF §4 rule 8". Contemporaneous "Phase 3 blocked" statements inside HANDOFF's retained historical openers are preserved unedited as the record. The consolidation's pin-time hash in `PHASE3_ENTRY_DECISION_2026-09-17` (`9934a088…`) remains the reference for the pre-sweep text; the drift is this item's corrections only | `docs/ARCHITECTURE_CONSOLIDATION.md` §§1/6; `HANDOFF.md` §4 |
| 47 | `DESIGN_CANON.md` factual corrections + annotation | §4 field status corrected (the declared 300 s half-life **never ticks** — #14; dormancy caveats per `findings/W3_field_activation.md`); §3.6 galaxies precision (per-name dynamic containers, advisory taxonomy — `findings/W1_galaxies_compartments.md`; not a "fixed enum"); header annotated: status tags are design-time snapshots with current-state pointers | `docs/DESIGN_CANON.md` §§3.6/4 |

**Consequence:** no verdict changes. The theory map now matches GATED-S-003, ledger claim-0007,
and the landed #25; the consolidation and HANDOFF no longer describe Phase 3 as blocked; the
canon's Gen2 claims match the landed errata. Frozen-artifact surface age (CHARTER/NUCLEUS) is
documented, not edited.

## K. Milestone-era consistency audit (2026-09-19)

Triggered by docs-sweep batch 3. Audited: `GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md`,
`BENCHMARK_AND_VERIFICATION_PROTOCOL.md`, `MILESTONE_0_EXECUTION_MANIFEST.md`,
`PREREGISTRATION_PEB13/14A/14B/14C/15_*.md` against the executed receipts, drivers, and code.
**No artifact was edited:** these are registered texts (frozen/sealed/ratified by commit + receipt;
none carries a 64-hex pin — pinning discipline per `WAVE_EXTRACTION_PROTOCOL.md` §9). Findings
below are register items awaiting operator disposition where noted; audit provenance and
spot-verification list in `receipts/DOCS_SWEEP_BATCH3_2026-09-19.md`.

| # | Erratum | Correction / finding | Landed in |
|---|---|---|---|
| 48 | `GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md` (ratified v1.2) content drift beyond #41 | (1) Spec's speculative fast path `top1−top2 ≥ 0.85` → implemented composite `M = 0.40·U + 0.35·P + 0.25·R_rev − 0.50·R_risk ≥ 0.85 ∧ risk ≤ 0.10 ∧ K1` (`bicameral.rs`; M05A receipt). (2) Mesh "auto-quarantine at ≥3 failures or trust < 0.20" → implemented as suspicion-count immune statuses (`ganying.rs`), no trust-decay mechanism. (3) "284 loops / 11 GB / 47 databases" figure unsupported — recorded incident is 2.4 GB RSS / 110 % / 284 zombie dreams, external-only (#22). (4) Spec PEB-3 (co-usage role drift) ≠ executed PEB-3 (basin geometry; M04B) — extends #41. (5) PEB-7 spec lists 6 metric families; execution measures 3 (predictive, discriminative, redundancy); anomaly-discrimination and transfer unmeasured. (6) Mesh artifact names (`mesh_authority.json`, `GiftTokenLedger`) absent from the substrate. (7) `dream.rs:4` + PEB-4 receipt cite §3.2, which does not exist | this register; audit receipt |
| 49 | `BENCHMARK_AND_VERIFICATION_PROTOCOL.md` (v1.0) | (1) Baseline identity three-way: table pins commit tip `3483382d…`; freeze commit is `60b3439`; `g3-crb-1` tag resolves to `9cb10942a5c2…`. (2) "1,000-session soak" is protocol scope; executed Phase-2 continuity = 50 sessions / 250 turns — no 1,000-session receipt. (3) Scale range conflict: `10³→10⁶` (Layer 4) vs `10³→10⁵` (Phase 5; executed) | this register |
| 50 | `MILESTONE_0_EXECUTION_MANIFEST.md` (sealed) vs PEB-0/1 execution | (1) Baseline commit `9cb109404c0ec54181f0bdf20067644917fa9f34` is not an object in either repo; intended `g3-crb-1` tag commit is `9cb10942a5c202140cf07d7038448482c4af2e11` (same 8-char prefix). (2) PEB-1 executed seed `0xCAFEBABEDEADBEEF`, 200 trials/corner vs manifest `0xDEADBEEF42C0FFEE`, 1000 trials (400/300/300) — no recorded amendment. (3) Manifest metric `m3` (Epistemic Calibration/Brier) executed as "Refusal Disclosure". (4) PEB-0 executed in `wm-gen3-core` (`pulse.rs`); manifest directs `wm-gen3-harness` | this register; disposition below |
| 51 | PEB-13/14A/14B/14C prereg vs execution | PEB-13: ΔBIC gate registered `> 10.0`, executed `> 0`; registered Dirichlet `α₀ = 1/K` + `α₀ ∈ [10⁻³, 1.0]` sensitivity sweep, executed fixed `α₀ = 0.05`, no sweep. PEB-14A: registered 64 KB / 23-fragment envelope, executed 1024-byte reassembly (19-byte writes; receipt "1024/1024", "23 partial chunks"). PEB-14B: scenario-7 complexity 10 params registered, `k = 16` executed. PEB-14C: unregistered "Declared ≠ Verified Capacity" defense added post-ratify (`d3869e2`); dimension-11 target differs (fds ≤ 2; memory-growth target dropped). Precedent for amendments: PEB-14A amendment v1.1 (explicit event) | this register; disposition below |
| 52 | PEB-15 prereg + Gate 9A status | (1) "143 unit proofs" matches no revision (M8C ratify 144 → fixes 146 → PEB-15 148; HEAD 148). (2) The eight-violation table overstates the implemented suite: `tests/adversary_contract.rs` = 1 test / 4 checks; `contract.rs` = 1 test enumerating "Violation 1–7" (V3 is a legal commit); no tests for serde-deserialization, background-loop, or socket-identity rows; row-4's claimed defense (non-Send/Sync) does not hold — `CommitCapability` is auto-`Send + Sync`. (3) Gate 9A's third deliverable (full M0–M8 regression vs packaging) has no receipt yet — **open work, not a defect**. (4) `src/bin/wm.rs` is a prospective Gate-9B target (forward reference) | this register; disposition below |

**Operator disposition owed (batch 3):**

1. **Prereg-vs-execution divergences (#50–52):** decide per item — amend explicitly (PEB-14A
   amendment v1.1 pattern), accept as recorded deviation, or schedule re-execution. Milestone
   ratifications were operator acts and stand unchanged until disposition; this audit changes no
   verdict by itself.
2. **Baseline identity (#49.1) + M0 manifest commit typo (#50.1):** a locating note or versioned
   doc correction, on operator direction.
3. **M9 planning (#52.2–#52.3):** violation-suite completion and the packaged full M0–M8
   regression remain Gate 9A work before any Gate 9A completion claim.

**Consequence:** no verdict changes; no artifact edited. The milestone-era record now carries an
explicit, evidence-linked inventory of spec-vs-execution drift for operator disposition.

## L. Documentation-sweep additions, batch 3 (2026-09-19)

Two sources: (a) the **session-provenance trace** for the PEB-era records (audit of AGY session
`221fbb57-905f-4e7d-a4d3-3c11810ea0b7`, "Studying WhiteMagic Generations", 2026-09-17 22:04 →
2026-09-19 20:06 ET, 4,119 steps; full table in `receipts/DOCS_SWEEP_BATCH4_2026-09-19.md`); (b)
**code-walk step 2** (`store.rs` + `ops.rs` non-test core). No verdict, claim, gate, or threshold
movement; no registered artifact edited.

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 53 | PEB-era "preregistered" label — provenance trace | The session shows the PEB-era prereg documents were **co-designed with implementation**, not frozen before runs: PEB-13 prereg + code + driver + receipt all in `36ba82b`; PEB-14A prereg (step 5211, 22:57:40Z) → test (step 5223, 22:58:07Z); PEB-15 prereg → `contract.rs` → test within ~3 min, one commit `8c13904`. M0 is the **exception** (operator freeze-first, steps 2460/2472; manifest step 2528 before execution 03:04–03:16). **Deliberate/disclosed:** relative ΔRMSE (step 5062), PEB-14A v1.1 amendment, PEB-15 commit message. **Silent:** M0 metric substitution (m3 Brier→Refusal Disclosure, m5 containment→pairs, m4 dropped; Brier never measurable in this bench), PEB-1 seed `0xCAFEBABEDEADBEEF` invented at test-authoring (step 2756) but labeled "Preregistered" (step 2767), baseline hash completed from a 7-char short hash without verification (steps 2487→2528), ΔBIC 10→0 with bootstrap CI / multi-seed / α₀ sweep absent, 64 KB→1024 B fragmentation undisclosed, "143 unit proofs" = cargo-test pass count (step 5539; HEAD is 148). **Label consequence:** PEB-era documents are read as *co-designed specifications (not freeze-first registrations)*; milestone ratifications stand as executed-evidence ratifications, scoped by #48–52 and this trace | this register; receipt `DOCS_SWEEP_BATCH4_2026-09-19.md` |
| 54 | Read-path audit overstated (projection-on writes) | `docs/READ_PATH_AUDIT.md` finding #1 asserted `recall` contains no store-write calls; with `WM_GEN3_PROJECTION=1`, `recall` embeds the query via `embed_cached` (`ops.rs:828` → `:490-520`) and writes misses to the `embed_cache` DB (`Store::put_embedding_cache`). Bounded and declared; `records`/`relations` untouched; the byte-identity demonstration holds for the default configuration | `docs/READ_PATH_AUDIT.md` findings #1/#4 corrected; residual added |
| 55 | Code-walk observations (not errors; future registration) | (a) `remember_batch`: a vector-write failure after `put_record_and_postings` returns `Err` while the record is durably persisted and identity-mapped (partial-outcome semantics beyond the A1 declared cases). (b) `store.rs` `decode_record`: unknown domain/class/status wire bytes coerce to defaults (`_ =>` arms) rather than refusing — a silent-coercion surface if LMDB content is corrupted | this register; HANDOFF §6 thread 8 |

**Consequence:** no verdict changes. The provenance trace explains how the PEB-era label drift
arose (same-burst authoring with selective disclosure; corrections driven by external review) and
scopes the affected labels; the read-path claim is corrected to its true configuration scope.

## M. Code-walk additions, batch 4 (2026-09-19)

From code-walk steps 3–4 (`field.rs`, `projection.rs`, harness `main.rs`, `journal.rs`) against the
Phase-1 interface and dependency records. No verdict, claim, gate, or threshold movement;
registered artifacts unedited (each item's edit is deferred to the morning decision list).

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 56 | T10 route `memory.aggregate` is an undeclared empty stub | The harness returns `{"status":"success","results":[]}` (`crates/wm-gen3-harness/src/main.rs:353-358`); the interface record describes the route's intended map ("recall + aggregation over relations") only for the case "T10 is in the frozen category set". T10 never entered the frozen set, so no scored run was affected — but a future T10-scored run would receive a valid-but-empty `results` list (the "silent zero" class) instead of an error. Correction: declare the stub in the interface record; the file is pinned in `PREREG_FREEZE_2026-09-16` (`9be4f1d8…`), so the landing is a versioned note/amendment (morning decision) | this register; morning checklist |
| 57 | Projection "no network at run time" is environment-enforced, not code-enforced | `Projection::load` calls fastembed `TextEmbedding::try_new` with the local cache dir; no offline mode is set, so a cache miss would attempt a download. The property holds today only because the cache is pre-populated; the module doc-comment states it as a property. Morning fix candidate: set `HF_HUB_OFFLINE=1` (or pre-check cache completeness / fail closed) and align the doc-comment — a code change with its own receipt if taken | this register; morning checklist |
| 58 | `DEPENDENCY_MANIFEST.md` still lists embeddings as deferred | §2 ("Deferred, not allowed yet: embeddings/ONNX/fastembed") and §4 ("Embeddings | Defer") predate the embedding exception (`DEPENDENCY_EXCEPTION_EMBEDDINGS_2026-09-16`), which governs since, and the projection slot ships. The manifest is pinned in `PHASE0_VERIFICATION_2026-09-16` (`f3be8449…`) and exceptions-via-receipt is the declared process — expected registry behavior, but a manifest-only reader is misled; morning decision: scoped pointer note (versioned) vs leave as pin-time text | this register; morning checklist |

**Checked consistent in these steps (no action):** tokenizer and candidacy rule match the NUCLEUS
statutes (divisor 20 / floor 2 / strict temporal order; `e=(w,s,c,t)` fixed at creation);
journal is append-only, flushed per event, hash-out linkage intact; read-only mode refuses exactly
the three write routes; `inspect` remains `&self`; the known append-journal pitfall is already in
HANDOFF §5.

### M.1 — Kernel-contract walk addendum (step 5a: `contract.rs` + `capability.rs`)

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 59 | `contract.rs` Evil Gana battery, row-by-row (addendum to #52) | Firsthand review (`contract.rs:192-290`): rows numbered Violation 1–7 — **V3 is a legal commit**, V1/V5/V7 are non-attempts (reads/field asserts), V2/V4/V6 are real runtime fail-closed checks; prereg rows 3 (serde-deserialization) and 4 (background loop) remain unimplemented. `ContractViolation::AuthoritativeBackgroundLoopForbidden` is **never constructed anywhere** (no enforcement path); the background-loop defense is type-aspirational (`CommitCapability` remains auto-`Send + Sync`). Affine-by-move confirmed (non-`Clone`/`Copy`, consumed by value; `mint_from_arbitration` `pub(crate)`). New production consideration: `NullifierSet` is **in-memory only** — replay protection does not survive restart | this register; morning checklist (D3) |

**Consequence:** no verdict changes; three scope declarations are queued for the morning decision
list. The walk continues with the PEB modules (pulse_compiler, ganying/transport, conformal,
geometry, hologram, contract).



## N. Gate 9A Slice 1 qualified-path semantics (2026-09-22)

From the sweep-integration lane (`receipts/GATE_9A_SWEEP_ACCEPTANCE_2026-09-22.md`,
`receipts/GATE_9A_RATIFICATION_AMENDMENT_2026-09-22.md`). No verdict changed; frozen texts
(`NUCLEUS.md`, `PHASE1_CONTRACTS.md`, the prereg freeze) are **not** edited — supersessions are
recorded here per the register's convention. Historical experiment journals
(`experiments/contradiction/*`) remain pre-change artifacts.

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 60 | Statutory pair budget superseded on the qualified path | `NUCLEUS.md:177` (candidacy rule v1: "pair budget 200,000", PREREG §2) and `PHASE1_CONTRACTS.md` §2.4 ("Refusal: budget-exceeded (bounded sweep — statutory pair budget)") describe the mutable experimental knob. The qualified production path replaces it with ratified `SWEEP_PROFILE_V1` hard caps bound into the request/receipt policy digest: 256 records, 16 KiB aggregate raw bytes, 1 KiB per record, 2 KiB postings, 1,024 token occurrences, 256 relations, 8,192 pair examinations, 1,024 effects. Oversize **refuses** (`SweepError::LimitExceeded`; typed refusal, no canonical mutation, no consumed operation ID); truncation is never used. `Policy::pair_budget` remains a legacy field but is inert on `think_sweep`. Any prereg'd re-run on this tree uses the new bounds | `sweep.rs` (`SWEEP_PROFILE_V1`), `sweep_planner.rs`, `store.rs` preflight; this register |
| 61 | Duplicate proposal semantics were incidental, now specified | Legacy sweep could create multiple relations for the same ordered `(src,dst)` pair when several shared rare tokens proposed it (the pre-sweep `existing` set was never updated within the sweep). The qualified planner deduplicates identical create effects into one canonical relation; receipts bind the deduped effect set. Proposal counts for multi-token-overlap corpora are lower than legacy journals | `sweep_planner.rs` (proposed-pair set); `gate9a_sweep_acceptance.rs::duplicate_pair_across_tokens_produces_one_effect` |
| 62 | Disabled sweep allocated and masked errors (D4) | Legacy `think_sweep` called `alloc_sweep().unwrap_or(0)` **before** the enabled check, consuming an ID and masking store refusals to ID 0. Qualified path: disabled is a typed no-op that consumes nothing and reports the peeked counter; counter errors propagate. `alloc_sweep`/`alloc_relation_id`/`bump_counter`/`put_relation` are gated to test/reference builds; `update_relation` removed | `ops.rs` `think_sweep`; `store.rs`; amendment D4 |
| 63 | Batch ingest no longer triggers a sweep | Harness `memory.batch_create` previously ran `think_sweep` as a post-ingest side effect. Qualified path returns `sweep.status = "not_requested"`; sweeps are explicit: `gen3.think_sweep` (authorized commit) and `gen3.sweep_replay` (authenticated replay). Drivers expecting the old side effect must call the route | `wm-gen3-harness/src/main.rs`; `scripts/check_slice1_harness.py` |
| 64 | Projection-enabled sweep/intake excluded from Slice 1 | Intake already refused with `ProjectionForbidden`; `think_sweep` now also refuses fail-closed when projection is enabled. Two projection-path tests are `#[ignore]`d pending 9C requalification. Model-enabled experiments cannot mutate lifecycle on this tree until the derived-write/cache contract lands | `ops.rs`; `GATE_9A_COVERAGE_MAP_REVIEW_2026-09-21.md` disposition |
| 65 | Store format v5 fresh-only; v4 and older refuse | `STORE_FORMAT_VERSION` 4 → 5. Receipts are stored as tag-prefixed envelopes (explicit kind byte + rmp payload); legacy raw receipt bytes cannot decode as v5; no migration or adoption until 9D. Historical v4-era experiment stores under `receipts/impl_*/` refuse to open with the new binary (fail-closed by design) | `intake.rs`, `sweep.rs` envelope codec, `store.rs`; format-refusal tests |
| 66 | Receipts carry volatile-usage disclosure (D2b) | `SweepReceipt` now carries `usage_evidence_basis = "process_local_volatile"` and `usage_restart_persistent = false`; the persisted sealed request carries the bounded usage entries that drove decisions. Replay never recomputes usage. Disclosed consequence: a restart can demote a used-persistent relation once the durable age threshold is met (covered by an executable test) | `sweep.rs`, `store.rs`; `gate9a_sweep_acceptance.rs::restart_sensitivity_demotes_used_relations_when_lineage_is_lost` |

**Checked consistent (no action):** core PEB benchmark tests (PEB-0…14C) pass unchanged under the
qualified path; the candidacy rule itself (divisor 20 / floor 2 / strict temporal order) is
unchanged; record semantics (`created_at == id` logical ingest order) unchanged.

### N.1 — Completion-claim conflict (addendum to #59)

| # | Erratum | Correction | Landed in |
|---|---|---|---|
| 67 | Gate 9A "RATIFIED, FROZEN, AND COMPLETE" claims | `PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md:184,215` states Gate 9A is ratified/frozen/complete; the Sep 20 Codex hardening report claims "RATIFIED, FROZEN, AND VERIFIED IN TEST (167/167)"; the Antigravity synthesis report §14.3 (2026-09-19) repeats ratification with "152 workspace tests". All predate the Sep 20 independent audits and the Slice 1/sweep work; the closure checklist and both coverage reviews treat Gate 9A as open. Test-count drift 152 → 167 → 181 → 180 → 197 identifies different candidates, so none of the older counts qualifies the current tree. The closure verdict must reconcile these claims without rewriting frozen history and must state the PEB-15 §8.2 split (core encapsulation/regression to 9A; packaged CLI verification to 9B) | this register; closure verdict (pending) |

| 68 | Gate 9A closure transition (pending operator ratification) | The draft closure verdict (`receipts/GATE_9A_CLOSURE_VERDICT_2026-09-22.md`) supersedes the stale "RATIFIED/FROZEN/COMPLETE" lines in `PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md:184,215` (see #67) upon operator ratification. The frozen preregistration text is **not** edited; this entry registers the transition and the corrected candidate fingerprint: `receipts/gate9a_article_evidence_20260922/source-manifest.sha256` (37 implementation files; see the manifest file for its digest — omitted here because this register is inside the manifest); reviewer artifacts are appended under `evidence-manifest.sha256`. Status at entry: closure recommended by the independent review; operator ratification pending | this register; closure verdict (draft) |
