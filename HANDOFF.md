# WMgen3 — HANDOFF (updated 2026-09-19)

> **NEXT SESSION OPENER (docs-sweep close, 2026-09-19; milestone-era tip `8c13904`; tree
> clean):** **The milestone era is complete through M8C and M9 is open.** M0–M8C
> (PEB-0…PEB-14C) implemented, benchmarked and ratified (`receipts/BENCHMARK_*.md`; §1);
> baseline `G3-CRB-1` frozen 2026-09-18. **M9 / PEB-15 (Alpha Production Graduation,
> public target `v10.0.0-alpha`) preregistered 2026-09-19; Gate 9A — the
> `GEN3_KERNEL_CONTRACT` + "Evil Gana" architectural adversary suite — implemented at
> `8c13904` (`crates/wm-gen3-core/src/contract.rs` + `tests/adversary_contract.rs`).**
> Gates 9B (compatibility shell / production `wm` binary), 9C (cognitive re-derivation),
> 9D (alpha reality test) are open; no PEB-15 driver exists yet. **Docs sweep (this
> refresh):** batch 1 landed — B5 spec-hash citation corrected (`docs/ROW_EXIT_PACKET_B5_W2.md`;
> erratum I #38), README + HANDOFF updated to the milestone era, errata batch I (#38–42) —
> `receipts/DOCS_SWEEP_BATCH1_2026-09-19.md`. **Carry:** WEAK stays WEAK (`claim-0003`);
> ledger 8 claims (§3); 9.1.7 control never re-baselined; F4 guard binds relation-count
> metrics; WMv9-tree fixes = Gen2 lane. **Read first:**
> `docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md` →
> `docs/GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md` → `receipts/BENCHMARK_M08C_HOLOGRAPHIC_SANGHA.md`.
>
> **PRIOR OPENER (retained as the record — close of the second 2026-09-17 evening session; tip = the commit
> carrying this block; tree clean):** **Phase-4 synthesis map landed** (`528047e`; receipt
> `PHASE4_SYNTHESIS_MAP_2026-09-17`): 25 function families → 8 PRIMITIVE / 11 GATED / 4 LINK /
> 4 INVARIANT / 3 RECIPE; headline: no further primitive demand identified in the extracted and
> spot-verified corpus; the four missing-primitive candidates unchanged (field, recipe runtime,
> selection layer, credit assignment). Operator framing recorded: Gen1 discovery → Gen2
> selection/consolidation → **Gen3 discernment**. **B5 recall-side scope view: registration
> ratified** (`9b1a61c`; receipt `W1_B5_RECALL_VIEW_REGISTRATION_2026-09-17`; operator review
> added the cross-scope crowd-out case + frozen label grammar + pinned cause
> `no_candidates_in_scope`), **implemented** (`10b48d8`; `RecallQuery.scope`, population filter
> over `corpus:<label>:<tags>` before scoring; tests 48/0/1 + doc 5; closures PASS),
> **acceptance demonstrated with one finding** (`4a26875`; bundle `impl_b5_recall_view_2026-09-17`,
> SHA256SUMS `edf7be53…`): campaign 8/8 PASS (24 labels > Gen2 cap 20; crowd-out with
> candidate_limit=1; filter-not-scorer; empty-view pinned disclosure; malformed-selector
> refusal; explicit-only scan; bare bytes); fresh 0-diff regression ordering/metrics/journal
> **exact** (160 queries, C00/C01); **F-1**: score drift max **2 ULP** vs registered ≤1
> (same-binary rerun baseline already ≤1 ULP; f32 summation-order nondeterminism + cross-build
> codegen; no ordering/metric effect) — **B5 row exit not claimed**. **Operator decision 2 → 1:
> scorer-determinism unit ratified** (`SCORER_DETERMINISM_REGISTRATION_2026-09-17`; **execute
> next session**): declare three orders (`ops.rs:733` `total_idf`, `:390` dispersion entropy,
> `:1126` sweep pair enumeration) → same-binary **0 ULP** bar → F-1 errata → **B5 exit**.
> **W2_02/W2_04 acceptance slices authorized** (`docs/specs/W2_02_04_ACCEPTANCE_PREP.md`;
> specs already frozen + owner assigned — headers stale per errata #33): build
> `driver_w2_02_retention.py` (record persistence through explicit sweeps incl.
> candidate→persistent and persistent→cold **relation** transitions; scans supporting only) and
> `driver_w2_04_consolidation.py` (**matched no-pass A/B control**; semantic object preservation
> instead of file-byte equality; promotion persists across restart; F4 guard); expected core
> change none; stop-and-register on any gap. **Governance:** standing authorization bounded by
> named gates (`W2_SPEC_BATCH_FREEZE_CLARIFICATION_2026-09-17`; errata #36). **Carry:** WEAK
> stays WEAK; ledger 8 claims; 9.1.7 control never re-baselined; F4 guard binds relation-count
> metrics; WMv9-tree fixes = Gen2 lane, never mixed into Gen3 commits.
>
> **PRIOR OPENER (retained as the record — close of the first 2026-09-17 evening session; tip = the commit carrying this
> block; tree clean):** **Canary floor check re-run on the moved code: C1–C6 12/12 PASS** (bundle
> `receipts/canary_2026-09-17_rerun/`, `SHA256SUMS` `01532868…`; frozen bundle untouched; journal
> readings identical 7/7 cells, responses byte-identical 6/7 — `B_off` differs only by wall-clock
> `took_ms` 0→1; receipt `receipts/CANARY_RERUN_2026-09-17.md`). **A1 spec rev 2 ratified**
> (`d437ffed`; amendment receipt `receipts/W1_SPEC_A1_AMEND_2026-09-17.md`): traceback-class noise =
> **refuse-with-journal** (`noise_class`, declared 5-class table `traceback`/`error_line`/`json_blob`/
> `function_repr`/`too_short`, one named constant `< 10`, `WM_GEN3_NOISE=0` ablation; Gen3 has no
> quarantine organ). **Noise implementation landed** (`c12179d`; tests 40/0/1 + 5 doc; release
> `76083d05…`). **A1 acceptance fixtures demonstrated** (receipt `IMPL_A1_FIXTURES_2026-09-17`;
> bundle `receipts/impl_a1_fixtures_2026-09-17/`): noise (5 classes + controls + ablation + ordering
> negative), scope law (per-scope admission/dedup, no global dedup, provenance sources), bare bytes
> (`data.mdb` sha256 identical after refused re-ingest), partial (468 KB item single-outcome +
> budget-forced 120/121 typed partial), drift (SIGKILL mid-batch 494/3000 → reopen coherent, record
> count == replay refusals, replay converges 3000, third pass refuses all; hash-outs verified).
> **B1 acceptance demonstrated** (receipt `IMPL_B1_ACCEPTANCE_2026-09-17`; bundle
> `receipts/impl_b1_acceptance_2026-09-17/`, `SHA256SUMS` `6504cf44…`): stage A reference
> (source-frozen `7ff9181` rebuild) ≡ recorded cells C00 (all off) + C01 (defaults) — 80 queries
> each, ordering/metrics 0 diffs (scores ≤ 1 f32 ULP); stage B candidate ≡ reference on a
> gate-neutralized corpus (both configs, 0 diffs); rank-field audit + no-planner proof PASS.
> Disclosed: recorded cells predate the A1 gate (raw corpora carry spec'd `duplicate_exact`
> refusals; deduped-corpus derivation scripted + hashed), build non-reproducibility (two fresh
> builds differ; `b1c66fec` not reproduced — regression is behavioral), ≤ 1 f32 ULP score
> variation. **W2_03 + W2_07 acceptance demonstrated** (receipt `IMPL_W2_03_07_2026-09-17`;
> bundle `receipts/impl_w2_03_07_2026-09-17/`, `SHA256SUMS` `3344ca9d…`): W2_03 no-knob strata
> (scrubbed env: defaults `[1,0]`/strata `[0,2]`/mode `Structural`; sweep off `[0,1]`/`[1,1]`/zero
> proposals; no `WM_VALIDITY` symbol in binary/source; F4 phantom + deduped metric unit-tested —
> tests 42/0/1); W2_07 inspect contract (tier authority/statutes/adaptive + arbitration + journal;
> one-universe key scan incl. certification/action/optimizer keys; read-only `data.mdb`+journal
> unchanged). **LATE-EVENING ADDITIONS (same session):** A3 acceptance + rev 2 (case 1 declared
> property, operator-ratified; rule v2 gated), W2_01 edges acceptance, B5 scopes acceptance
> (Gen3 compile/link side; compartments/classes declared link-side), A1 case-3 bounds refusal +
> closures (A1 3/7/10, B1 case 2), `docs/ROW_EXIT_PACKET.md` ready for signature (A1/A2/A3/B1),
> errata §H + protocol §9 (gate-neutralized regression recipe; behavioral pins). **Ops:** 9.1.8
> fleet deployed (`~/.local/bin/wm` `cc5b4004…`, 11/11 units, backup kept) +
> `checkpoint_nodiscovery` rhythm active; parity + read-path audit done; remaining ops =
> **JSON write-through + stress fixtures** (operator/WMv9). **External review queued
> (2026-09-17):** (a) **B5 recall-side scope view** — the label→ontology bridge; needs its own
> registration + a fresh 0-diff regression (it changes the recall surface); (b) **Phase-4 synthesis
> map** (Gen1/Gen2 organs → Gen3 primitives; code boundary stays closed until the acceptance
> campaign finishes); (c) W2_02/W2_04 as the first endogenous mechanisms. Reproducibility
> vocabulary (source/artifact-instance/behavioral equivalence) + first-class transform records
> landed (`receipts/transforms/TRANSFORM_gate_neutralize_v1_2026-09-17.md`; protocol §9).
> **Carry:** counts
> generated; WEAK stays WEAK; ledger 8 claims; 9.1.7 control never re-baselined; F4 guard binds
> relation-count metrics.
>
> **PRIOR OPENER (retained as the record — close of the third 2026-09-17 session; tip = the commit carrying this
> block; tree clean):** **Wave-1 specs are frozen + ratified (batches A + B)** — eight specs under
> `docs/specs/` per `PHASE4_WAVE_PLAN.md` §7: **A1** durable store + ingestion gate
> (`cf638395…`; journal owns `duplicate_exact`; gate identity = (content SHA-256, source, kind),
> per scope), **A2** evidence disclosure (`aa84a5ac…`; one vocabulary `insufficient_evidence`,
> floors fail-closed, no swept thresholds), **A3** revisions/supersession (`3adedac0…`; no Gen2
> agreement claimed, F4 guard binds relation-count metrics); **B1** retrieval/ranking
> (`9b293d01…`; earned subset only, no planner imports, 0-diff negative control), **B2**
> sessions/continuity (`68cce27a…`; link + compile split; adopt `checkpoint_nodiscovery`; no
> payload-less shells), **B3** coordination (`917c4bef…`; typed effects + always-releasable
> asymmetry; snapshot reads; no mutable-JSON board), **B4** claims/belief class (`a3f9df8f…`;
> resolution completeness; one calibration universe; no destructive sync; write-through),
> **B5** galaxies/compartments (`80a99e62…`; labels as views; fail-closed unknowns; membership ≠
> authz; cap bypass closed-or-named). Receipts `receipts/W1_SPEC_A{1,2,3}_FREEZE_2026-09-17.md`
> and `receipts/W1_SPEC_B{1..5}_FREEZE_2026-09-17.md`; owners assigned (operator, this session).
> Each spec carries: frozen behavioral spec · selection history with per-statement evidence levels
> · 9.1.7+9.1.8 adversarial cases · ablation with journal instruments (rungs) · wrapper-side
> acceptance — no inert tests. **Wave-2 specs are frozen + ratified** (batch receipt
> `receipts/W2_SPEC_BATCH_FREEZE_2026-09-17.md`): relations/edges (`b355bdda…`),
> retention/lifecycle (`c9a2f09f…`), currentness strata (`df769f30…`), dream/consolidation
> (`71f66725…`), recipe layer (`60dcf5f3…`; gated on its anti-bloat review),
> RSI-over-journal (`4a980a08…`), self-model/inspect (`09ed2e9f…`). **Implementation slices
> landed + demonstrated (wrapper-side):** A1 exact-hash gate (`8c5e32f`; receipt
> `IMPL_A1_GATE_2026-09-17`; bundle `impl_a1_2026-09-17/`: refusals journaled `duplicate_exact`,
> store set unchanged, cross-process) and A2 `insufficient_evidence` vocabulary (`a588ae1`;
> receipt `IMPL_A2_VOCAB_2026-09-17`; bundle `impl_a2_2026-09-17/`: one reason set, causes
> `no_candidates`/`no_results_above_floors`, control intact). **Toolchain:** pinned 1.98.0
> (`1194761`; receipt `TOOLCHAIN_PIN_1_98_0_2026-09-17`) + repo-wide rustfmt sweep (fmt clean
> under the pin, tests green, A1/A2 drivers re-run). **Gen2 9.1.8 fold-in register:**
> `docs/PHASE4_GEN2_FOLDIN.md` — one-screen dispositions + the **deploy-window checklist**.
> **Next slices:** remaining
> acceptance wiring — **A2 substrate acceptance complete** (floors `41532c6`; read-only +
> starvation/route disclosure `e3c6c6d`; receipts `IMPL_A2_FLOOR_BOUNDS_2026-09-17` /
> `IMPL_A2_DISCIPLINE_2026-09-17`; additive `projection_ran`/`projection_error` noted in the
> journal schema doc);
> A1 scope/drift/partial/noise cases; B-row acceptance harnesses; then the ops backlog (see the
> fold-in shortlist: deploy → nodiscovery rhythm, bundle↔journal parity, read-path audit, JSON
> write-through, stress fixtures). Gated
> rows wait: recipe anti-bloat review, Hebbian promotion policy, field propagation task,
> learned-phase/conformal experiments.
> **Read first:** `PHASE4_WAVE_PLAN.md` §7/§9, `docs/specs/W1_*` + `docs/specs/W2_*`,
> `PHASE4_WAVE1_FINDINGS.md` + `PHASE4_WAVE2_FINDINGS.md` (divergences),
> `WAVE_EXTRACTION_PROTOCOL.md`. **Carry:** counts
> generated; WEAK stays WEAK; ledger 8 claims (0003 WEAK); 9.1.7 control never re-baselined; F4
> guard binds relation-count metrics. **Ops backlog:** WMv9 9.1.8 deploy (bundles
> `checkpoint_nodiscovery`; then switch session rhythm), remaining JSON-store write-through,
> safety-mask/egress per the handoff note.
>
> **PRIOR OPENER (retained as the record — close of the second 2026-09-17 session; tip = the commit carrying this
> block; tree clean):** the nucleus is **frozen** (`docs/NUCLEUS.md`, sha256 `73c5a9cf…`; receipt
> `receipts/NUCLEUS_FREEZE_2026-09-17.md`; canary evidence `receipts/canary_2026-09-17/`) and the
> operator-side queue is **complete** (checkpoint mitigation; WMv9 claims write-through `16198ea`
> committed, deploy deferred; matrix v2 + safety-mask/egress handoff in `~/Desktop/dev journal/`).
> The **Phase-4 wave plan is landed** (`docs/PHASE4_WAVE_PLAN.md`, 30-row DO_NOT_MIGRATE
> appendix). **Next artifact: Wave-1 spec batch A** — durable store + ingestion gate · evidence
> disclosure · revisions/supersession — one frozen spec per capability (behavioral spec ·
> selection history · 9.1.7+9.1.8 adversarial cases · ablation · owner; per
> `PHASE4_WAVE_PLAN.md` §7), then batch B (retrieval, sessions, coordination, claims, galaxies/
> compartments). **Read first:** `PHASE4_WAVE_PLAN.md`, `NUCLEUS.md`, `PHASE4_ERRATA.md` (do not
> re-raise), `WAVE_EXTRACTION_PROTOCOL.md`. **Carry:** counts generated; names are search leads;
> WEAK stays WEAK; ledger 8 claims; 9.1.7 control never re-baselined. **Ops backlog:** WMv9 9.1.8
> deploy (bundles `checkpoint_nodiscovery`; then switch session rhythm), write-through for the
> remaining JSON stores, safety-mask/egress per the handoff note.
>
> **PRIOR OPENER (retained as the record — first 2026-09-17 session; tip `86ac838`, tree clean, 27
> findings files + 30-item errata register):** Phase 3 is closed on paper; **all source extraction is
> complete** (waves 0–5). **The next artifact is the nucleus freeze**
> (`docs/NUCLEUS_FREEZE_CRITERIA.md`): compile `NUCLEUS.md` (four-part snapshot: constitutional
> core · earned cognitive nucleus · statutory baseline · reproducibility pins), verify pins, run
> the canaries (closure canaries · R ablation · count-gate ablation · provenance completeness ·
> **round-trip relation kinds** · **reachable-effectful acceptance**), then operator ratification
> + receipt. **It gates all construction.** After it: the **Phase-4 wave plan** with the
> DO_NOT_MIGRATE appendix (per `WAVE_EXTRACTION_PROTOCOL.md`). Operator-side in parallel: scoped
> matrix v2 (nucleus + Waves 1–2 rows only); WMv9 ops (flush-on-shutdown for JSON stores,
> `checkpoint_nodiscovery` adoption, safety-mask/egress handoff); optional SD-card
> `data-backups`/`benchmark-results` scan and W-pilot over Gen2 tags. **Read first:**
> `PHASE4_WAVE0_SESSIONS.md` (what Gen1 really was), `PHASE4_ERRATA.md` (§A–G; do not re-raise),
> `WAVE_EXTRACTION_PROTOCOL.md` (rules), the day's blocks below. **Carry:** counts generated;
> names are search leads not identity; establish timeline provenance before era claims; new
> extraction demand-driven only. **Ledger:** wmv9 claims 8 — 0000 falsified · 0001/0002/0004
> falsified · 0003 arbitration pending/WEAK · 0005/0006 falsified · 0007 validated. **Quirk:**
> wmv9 `session.checkpoint` captures WMv9's git HEAD — put the WMgen3 commit in the note.
>
> **NUCLEUS FROZEN (2026-09-17, this session, post-pass):** the freeze ceremony is complete with
> operator ratification. Frozen artifact `docs/NUCLEUS.md` (four-part snapshot: constitutional
> core · earned cognitive nucleus [N1 provenance/H4-H6 · N2 R + currentness strata · N3 selection
> explanations · N4 journal-as-evidence · N5 audit discipline · conditional slot C1 = S with
> scoped `count < 2` activation] · statutory baseline · reproducibility pins; sha256
> `73c5a9cf…`); receipt `receipts/NUCLEUS_FREEZE_2026-09-17.md`. Step-2 pins regenerated with no
> mismatches (binary `b1c66fec…` byte-identical rebuild; `wm contract` 302/70; live ledger 8/8;
> full corpus/harness re-hash pass). **Canaries C1–C6 all PASS** — evidence bundle
> `receipts/canary_2026-09-17/` (`SHA256SUMS` `941abc80…`): closures static + 28/28 tests +
> runtime refusal with zero violations; R ablation ordering/strata flip; count-gate fired-set
> contrast (floor mode misses the 1-candidate case); 100 % provenance completeness; relation
> round-trip intact across processes; reachable-effectful inventory. Disclosed: F1 decomposition
> drift (ratified `cb8235e9` → current `194f081c`, additive errata only), F2 criteria drift
> (canaries added in `86ac838`), F3 binary supersession (`b51112e9` → `b1c66fec`), **F4 duplicate
> proposals within one sweep** (`existing` snapshotted pre-loop, `ops.rs:751`; flagged for a
> future registration, not a blocker). **The Phase-4 construction gate is open** — each migration
> still needs its frozen behavioral spec + 9.1.7 fix list as adversarial tests + wrapper-side
> evaluation + ablation. **Next artifact: the Phase-4 wave plan + DO_NOT_MIGRATE appendix**
> (`PHASE4_GEN1_TREE.md`, `PHASE4_GEN2_DELTA.md`, `WAVE_EXTRACTION_PROTOCOL.md`), then the
> operator-side queue (scoped matrix v2, WMv9 ops: flush-on-shutdown / `checkpoint_nodiscovery` /
> safety-mask-egress handoff). Carry rules unchanged; ledger 8 claims (0003 stays WEAK).
>
> **WAVE-0 INTERMISSION COMPLETE (2026-09-17, same session):** runtime evidence recovered — the
> full Gen1 galaxy store was found locally (`WHITEMAGIC_GEN1_v26_MEMORY_CORE/v26/state/users/
> local/galaxies/`; sessions 21,351 rows, codex 21,821, pre-2026 galaxies), plus `tool_usage.db`
> (5,998 calls) and state ledgers; the SD card was mounted/read-only scanned (archives +
> nightly backups + signing keys — left untouched) and proved unnecessary for this pass. Eight
> findings files (`docs/findings/W0_*.md`) + master `PHASE4_WAVE0_SESSIONS.md` +
> `WAVE_EXTRACTION_PROTOCOL.md` (phenotype ladder, evidence levels, timeline-provenance rule,
> do-not-migrate taxonomy) + errata §G (10 items). Headline corrections: **Gen1's lived era is
> ≈ late May → Aug 2** (Jan–Jun rows are back-filled imports); **the runaway is unattested by
> Gen1's own record** (churn + cost inflation, then the record stops; 284 zombie dreams date
> Jun 27–Jul 20); codex dup is 0.05 % not 37.2 %; Aria provenance is thin (8/256 genuine
> pre-2026 rows; no Book of Becoming in DBs); Brier 0.078 belongs to Gen2's ledger (v26 runtime
> = 0.2563/0.0731). No verdict changed; six findings changed evidence level. **Next: nucleus
> freeze → wave plan.**
>
> **PHASE-4 STUDY OPENED (2026-09-17, same session, post-pass):** **Track A — Gen2
> capability-source study** (`docs/PHASE4_GEN2_DELTA.md`): reference-pin decision (experimental
> control stays **9.1.7**; **9.1.8 is the capability-source reference**), full 9.1.7→9.1.8 delta
> ledger (15 commits; declared schemas 70→85; coordination truth-up/AHIMA Target A; mesh ingest
> hardening phase 1; onboarding/startup; truth hygiene) with nucleus/adversarial/source
> relevance per change. **Track B — Gen1 v26 tree build** (`docs/PHASE4_GEN1_TREE.md`): wave
> taxonomy (surfaces → native cognitive → lenses → strange Gen1 → hard remainder), wave-1
> candidate rows with verified ancestor pointers, and the source-extraction worklist for the
> next deep pass. Capstone = the Phase-4 wave plan; **migrations remain gated on the nucleus
> freeze**. **Wave-1 extraction batch 1 complete (same day):** six subagent findings files in
> `docs/findings/` (retrieval · sessions/continuity · coordination · claims/prescience ·
> galaxies/compartments · Gen2 9.1.8 source map), indexed with consolidated errata candidates
> and migration-spec divergences in `PHASE4_WAVE1_FINDINGS.md`; tree-doc rows corrected
> (embedder constant, qFHRR 8-bit, Jaccard dedup, advisory-only coordination, narrative-only
> sprawl); errata wording pending operator dispositions. **Wave-2 extraction batch 2 complete
> (same day):** seven findings files (`docs/findings/W2_*`: associations/relations,
> constellations/emergence, retention/lifecycle, citta/dream, engines/recipes, RSI/self-model,
> Gen2 wave-2 map), indexed with errata + divergences in `PHASE4_WAVE2_FINDINGS.md`. Headline
> corrections: v26 typed links never survived a save; SkillForge actually ran (33 persisted
> skills, write-only replay); "never self-certify" violated at mechanism level (4.0 % outcome
> coverage, maker = checker); the CITTA 18,204 headline is a storage-label artifact; Gen1 dream
> = 13 phases; Gen2 divergences flagged (Hebbian live in wm-memory, retention ≠ lifecycle,
> calibration = four disjoint universes). **Waves 3–5 extraction batch 3 complete (same day):**
> six findings files (`docs/findings/W3_*`: lenses/projection, Geneseed, simulation/imagination,
> field/activation, mesh/transport, reflex/MandalaOS boundary) + `PHASE4_WAVE3_FINDINGS.md`;
> errata register extended (`PHASE4_ERRATA.md` F-13…F-20). Headline: v26's coordinate channel
> was a silent always-on stage and Gen2 coords are hash-derived (no inherit-able lens); Gen2's
> 300 s decay never ticks; today's Geneseed is an unrelated git miner (V9.1 design has zero
> code); Gen2 mesh has one real gate + unsigned RPC frames; the reflex hardware path is live
> with an **inert safety mask**. **All source extraction is complete; the next artifact is the
> Phase-4 wave plan.**
>
> **UPDATE (2026-09-17, Phase-3 entry session):** (1) **Phase-3 entry decision record drafted** —
> `docs/PHASE3_ENTRY_DECISION.md` (gate interpretation: Phase 2 LOSS absorbed through the
> successor program ⇒ gate satisfied by completion, not victory; the ≥2-candidate insufficiency
> boundary parked as its own open research question; docs-only; **pending operator
> ratification**). (2) **§2.1–§2.4 verdict drafts complete** in `docs/PHASE3_DECOMPOSITION.md`
> (§2.1 effective under the ratification; §2.2–§2.4 pending pass ratification; evidence keys
> E1–E24). Highlights: session family split (storage/lifecycle `link`, continuity/digest
> `compile`), identity RETIREd for practice forms (provenance duty already carried),
> Geneseed/simulation/constellations/mesh are EXPERIMENT rows with manifest gates; governance
> mostly PRESERVE (statutes + seam) with closures/canaries CLEANLY; **shipped-vs-dormant audit
> corrected three misfilings** (`violet` = engagement tokens + model signing, `drive` =
> autonomic, `god.nodes` = graph analytics) and retired the only literal symbolic dispatch
> (`bagua.dispatch`, Charter §3.10); economy ruling upheld (monetary RETIRE; the shipped
> `bounty.*` submission/outcome ledger is preserved, not XRP economy). (3) **`docs/NUCLEUS_FREEZE_CRITERIA.md`** drafted (admission,
> exclusion, freeze procedure, amendment rule). (4) **Claims-ledger integrity incident +
> reconstruction** — the wmv9 ledger lost everything registered after Sep 16 15:35 to an
> ungraceful user-manager restart at 09:28 (these JSON stores flush only on graceful shutdown);
> restored to the chronological mapping: claim-0001 P2B · 0002 P2C · 0003 arbitration
> (pending/WEAK) · 0004 P2E · 0005/0006 GATED-S-001/002 (falsified) · **0007 GATED-S-003 count
> criterion (validated)**. Post-loss references ("claim-0001/0002/0003 = GATED-S…") are errata;
> see `receipts/LEDGER_RECONSTRUCTION_2026-09-17.md` and the corrected note in
> `docs/ARCHITECTURE_CONSOLIDATION.md`. (5) Dispositions recorded: **TIE parked**,
> **projection-agreement dormant** (§6 threads 2 and 4); the **≥2 boundary** is thread 7.

> **UPDATE (end of the GEN3-GATED-S-001 session):** Gated-S executed and closed —
> `experiments/testbed_ii/gated/REPORT_GATED.md` (registration freeze `98175b9`,
> implementation freeze `bf5c0a0`, results + report `5717504`). New switch
> `WM_GEN3_PROJECTION_GATED=1` + `projection.gate` journal events; regression proof
> (new binary, switch off ≡ frozen c11: 80 per-query × 6 fields = 0 diffs); fresh corpus
> seeds 401–410 (reproducible, `PYTHONHASHSEED=0` pinned in MANIFEST; frozen
> `generator_a.py` imported verbatim); audit controls 20/20 + 40/40, 80/80 runs valid,
> journals zero-violation. **Headline: falsified (gate-scoped) on P3 cost** — g1 total
> query wall 0.901 × g2 (bar ≤ 0.3); per-query model reload in both cells makes the
> registered bar unreachable under the harness. P2 ordering PASS (g1 36 ≥ g0 34, g1 36 ≥
> g2 36), P4 PASS (53 ≥ 51), Regime B **opportunity-limited** (|O|=0; the one g2-only
> R@5 hit is the audit-flagged `T1_delivery`). Gate fired 7/80 (all T2 absent-topic,
> lex_support_max=0), activation rate 8.75 %, cold fired latency mean 1010 ms. Dormant
> gate suppresses stale labels (T1s 0/20 g1 vs 3/20 g2). Taxonomy g1: LABEL 19 + LEX_TAU 4
> + REACH 1. "Gated projection" as a family not disposed of; future activation study needs
> a lexical–semantic-mismatched ecology + a cost model where the pass is the dominant term.
> Everything in §§2–5 (frozen organism, recipes, discipline, pitfalls) remains valid.
> Open threads: projection-agreement diagnostic decision (thread 4), TIE parked (§7).
> Phase 3 blocked; claim-0003 stays WEAK.
>
> **BOOKKEEPING + NEXT (same session, post-close):** GEN3-GATED-S-001 claim registered in the
> wmv9 ledger and resolved falsified (claim-0001; claim-0000 aligned to its Phase-2
> falsification). `docs/ARCHITECTURE_CONSOLIDATION.md` updated: gated row + TBII 401–410
> column + the dormant-gate stale-label dividend (research note, not a claim). Regime-B v2
> draft: `experiments/testbed_ii/gated2/PRE_REGISTRATION_GATED_S_002.md` — mismatch ecology
> (customer-support inbox) + two opportunity regimes (zero-overlap transport / partial-overlap
> discrimination) + pass-scoped cost (`projection_pass_ms`); mechanism frozen; **DRAFT for
> operator approval — no implementation before approval.** Projection-agreement stays dormant
> until v2.
>
> **GEN3-GATED-S-002 EXECUTED AND CLOSED (same session):** operator approved the draft as
> written; implementation freeze `9fa5fda` (instrumentation `projection_pass_ms`, regression
> proof 240+80 per-query × 6 = 0 diffs; mismatch corpus 501–510, engine-token-validated
> zero/partial overlap, A3 pre-freeze all 20 pairs > τ, range 0.6967–0.7701; audit 20/20 +
> 40/40). **Headline: the opportunity arrived** — |O| = 20 (O₀ zero-overlap 10, O₊
> partial-overlap 10). **O₀ transport PASS 10/10** (gate fires at lex_support_max = 0.0000;
> mechanical g1 ≡ g2). **O₊ discrimination FAIL 0/10** (one distractor token → support
> 0.173–0.295 = 17–30× the 0.01 floor → gate dormant). **P2 FAIL** (g1 26 < g2 34; cost of
> dormancy, not dilution). **P3′ PASS 0.159** (pass-scoped; captures 84 %). **P4 PASS**
> (46 ≥ 36). Verdict: **falsified (gate-scoped)** — the 0.01 floor is a zero-support detector,
> not an insufficiency detector; S-with-R on the designed-mismatch ecology shows its largest
> contribution yet (adjudicated g2 53 vs g0 36) — conditional lens confirmed in its designed
> regime, activation policy rejected. Claim registered + resolved falsified (claim-0002).
> Report: `experiments/testbed_ii/gated2/REPORT_GATED2.md`. Projection-agreement stays
> dormant; any insufficiency-based activation rule is a recorded design question, not planned.
>
> **GEN3-GATED-S-003 EXECUTED AND CONFIRMED (same session):** registration + implementation
> freeze `bb25c1f` (count gate `WM_GEN3_PROJECTION_GATED=count` + gate diagnostics; regression
> A old modes 240×6 = 0 diffs; regression B count mode on burned 501–510 reproduced the sim
> exactly: fired 30/80, M2 33 = g2, adj 53 = g2; fresh corpus 601–610 = 100 Q with validated
> candidate-count classes; audit 20/20 + 60/60; A3 all 30 pairs > τ, range 0.697–0.774).
> **Headline: CONFIRMED (gate-scoped), ledger claim-0003 VALIDATED.** |O| = 30 split cleanly:
> O₀ 10 → Recovery₀ 10/10 (mechanical); **O₁ 10 → Recovery₁ 10/10 — one lexical candidate is
> structurally insufficient for state resolution**; O₊₂ 10 → **MissedOpportunity₊₂ = 1.000**
> (every ≥2-candidate opportunity missed — boundary disclosed, not solved). P2a PASS
> (g1 M2 49 ≥ g0 30 incl. probes); item-D probe fired on all 10 with **zero degradation**
> (g0 = g1 = g2 = 10/10); P3 CostEfficiency **0.381** ≤ 0.5; P4 69 ≥ 50. Activation 40/100 =
> 0.40; useful ratio 0.50; T2 fires (10) reported separately. Report:
> `experiments/testbed_ii/gated3/REPORT_GATED3.md`. Analyzer key hygiene: qids repeat across
> seeds — all analysis must key `(seed, qid)` (a qid-keyed pass was caught and fixed; v2's
> published aggregates were independently verified per-seed and are unaffected). Next:
> operator direction — the count signal is earned; the ≥2 boundary would be a new primitive.

**For:** the next working session (human operator + AI session).
**Read first:** `docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md` (current gate) →
`docs/GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md` (physics/phenotype spec) → `docs/DESIGN_CANON.md`
(design record).
**This document:** practical state, exact commands, discipline rules, known pitfalls.
**Current tip at writing:** milestone-era tip `8c13904` (this docs-sweep refresh lands on
top; tree clean); baseline `G3-CRB-1` (`receipts/BASELINE_GEN3_COGNITIVE_RUNTIME_1_2026-09-18.md`).

---

## 1. Where things stand (one screen)

- **Phase 0 closed** (charter v0.1.1 ratified, control frozen, claims registered).
- **Phase 1 built** — minimal substrate: `remember · recall · think · inspect` over LMDB, JSONL
  journal, closures live (Law/Evidence), closure scans green.
- **Phase 2 executed and closed: LOSS** — Gen3 vs frozen Gen2 v9.1.7 on MemoraStrict
  (T8 0/15 vs 15/15; T1+T6 20/40 vs 40/40). `claim-0000` falsified.
- **Four successor experiments executed**, each frozen before its runs:
  | Experiment | Cell contrast | Outcome |
  |---|---|---|
  | P2B projection | C00/C01/C10/C11 | projection rejected (M1 solo, recall, M4); **claim-0001 falsified** |
  | P2C interaction | same cells, unseen seeds 6–10 | reach interaction replicated; ordering did not; **claim-0002 falsified** |
  | P2D arbitration | B0/B1/B2, unseen seeds 11–15 | best-ever cell (34/40, M2 85 %) but ΔReach bar headroom-impossible → **WEAK; claim-0003 pending** |
  | P2E dispersion | D0/D1, unseen seeds 16–20 | unblocks 4/6 margins, net redistribution; **claim-0004 falsified** |
- **Failure taxonomy frozen** (42 failures): LEX_TAU dominant and recurring (18), LEX 8, LABEL 6
  (audit-caught), TIE 4 (small recurring), STRAT/STATE2/REACH uniques. Relations exonerated;
  failures are within-stratum evidence competitions. 10/12 structural failures show a latent
  cosine advantage for the correct turn (ungated) — projection-agreement is a *diagnostic
  candidate*, not a claim.
- **Audit protocol v1.2** (`docs/GROUND_TRUTH_AUDIT_PROTOCOL.md`) froze before P2E scoring;
  6 flags on seeds 1–15, 2 on 16–20; it caught a pseudo-gain that raw numbers would have scored
  as success.
- **Phase 3 CLOSED:** entry decision ratified 2026-09-17 (`docs/PHASE3_ENTRY_DECISION.md`);
  compile-pass verdicts effective (`docs/PHASE3_DECOMPOSITION.md`); Phase-4 wave plan
  authorized; waves 0–2 executed (A1–B5, W2_01–W2_04, W2_07 exited 2026-09-17/18; W2_05
  recipe layer and W2_06 RSI remain gated).
- **Milestone era (2026-09-18/19):** M0–M8C implemented, benchmarked and ratified —
  PEB-0/1/4 · PEB-2/3 · PEB-5/8 · PEB-6 · PEB-7 · PEB-9/9.5/10 · PEB-11/12 · PEB-13 ·
  PEB-14A/B/C (`receipts/BENCHMARK_*.md`); baseline `G3-CRB-1` frozen 2026-09-18.
  **M9/PEB-15 (Alpha Production Graduation, target `v10.0.0-alpha`) preregistered
  2026-09-19; Gate 9A (kernel contract + Evil Gana suite) implemented at `8c13904`;
  Gates 9B–9D open.**
- **Next:** M9 Gates 9B–9D per `docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`
  (9B compatibility shell / production `wm` binary · 9C cognitive re-derivation · 9D alpha
  reality test). `claim-0003` (the arbitration claim) stays WEAK/unresolved (do not “finish” it).

## 2. The frozen organism (what must *not* change for Testbed II)

| Piece | Pin |
|---|---|
| R — supersedes candidacy | rule `candidacy.v1.shared-rare+value-diff+temporal`; divisor 20 / floor 2; pair budget 200k |
| S — projection | bge-small `Qdrant/bge-small-en-v1.5-onnx-Q` (snapshot `52398278842…`, hashes in `receipts/DEPENDENCY_EXCEPTION_EMBEDDINGS_2026-09-16.md`), CLS/L2/384d, brute-force cosine, **τ = 0.694** |
| Arbitration | structural strata 0/1/2 (current/unresolved/superseded), within-stratum lexical → semantic → recency → id |
| Score policy (D2) | idf-weighted query support; property tests in `ops::tests` |
| Switches | `WM_GEN3_SWEEP=0` (A1) · `WM_GEN3_PROJECTION=1` · `WM_GEN3_ARBITRATION=structural` · `WM_GEN3_DISPERSION=1` (falsified; default off) · `WM_GEN3_EMBED_CACHE=<path>` (model cache, read-only) · `WM_GEN3_JOURNAL=<path>` · `WM_GEN3_JOURNAL_HASH_OUT=<path>` |

Frozen cells must remain **behavior-identical** with all switches off (regression proofs were
done at each freeze: per-query diffs = 0).

## 3. How to run things (recipes)

```bash
# build & test (offline; model cache required only for projection cells/tests)
cd ~/Desktop/WMgen3
WM_GEN3_EMBED_CACHE=~/Desktop/WHITEMAGIC/WMv9/.fastembed_cache cargo test --offline
cargo build --release --offline            # ALWAYS after code changes (bins are not built by cargo test)
bash scripts/check_closures.sh             # dependency rule + mutation-surface rule

# harness invocation (run from WMv9 scripts dir; --data selects the corpus)
cd ~/Desktop/WHITEMAGIC/WMv9
BIN=~/Desktop/WMgen3/target/release/wm-gen3
CACHE=~/Desktop/WHITEMAGIC/WMv9/.fastembed_cache
env WM_GEN3_PROJECTION=1 WM_GEN3_ARBITRATION=structural WM_GEN3_EMBED_CACHE=$CACHE \
  WM_GEN3_JOURNAL=$OUT/seed16.journal.jsonl \
  python3 scripts/memorastrict_bench.py --binary $BIN --data <corpus-dir> --seeds 16 \
  --categories T8 T1 T6 T2 --limit 10 --candidate-limit 100 --min-score 0 --min-coverage 0 \
  --per-case --output $OUT/ab_run.json
# control arm: --binary ~/.local/bin/wm (frozen v9.1.7, sha256 47b5c28e…)
```

Corpora: `experiments/semantic_projection/holdout{,_p2d,_p2e}/` (seeds 6–10, 11–15, 16–20;
`MANIFEST.json` hashes) · WMv9 `benchmarks/data/memorastrict/` (seeds 1–5).
**All four splits are scored — never reuse them for confirmation.**

Analysis scripts: `experiments/semantic_projection/analyze_p2{b,c,d,e}.py` (+
`experiments/contradiction/analyze_results.py`). Pattern: pooled metrics, interaction/verdict
blocks, per-seed tables; ground truth stays wrapper-side.

Diagnostics & audits:
```bash
python3 experiments/semantic_projection/ground_truth_audit.py          # audit v1.2 → report json
python3 experiments/semantic_projection/failure_taxonomy.py            # classes → taxonomy json
python3 experiments/semantic_projection/failure_taxonomy.py --diag <file>   # merge ungated cosines
# A3 ungated cosines (read-only test; pairs from failure_diag_pairs.json or built-ins):
WM_GEN3_DIAG_PAIRS=…experiments/semantic_projection/failure_diag_pairs.json \
WM_GEN3_EMBED_CACHE=$CACHE cargo test --offline a3_diagnostic_ungated_cosine -- --ignored --nocapture
```

Claims ledger (wmv9 store, via federated MCP):
- `claims.add` requires `statement`, `source_date`, `predicted_outcome`, `falsification_criteria`
  (+ optional `domain`, `confidence`).
- `claims.resolve` requires `claim_id`, `validated` (bool), `event`, `event_date`.
- Current (8 claims; `claims.list` verified live 2026-09-19): 0000 falsified (Phase 2) ·
  0001 falsified (P2B) · 0002 falsified (P2C) · **0003 pending (WEAK — P2D arbitration,
  deliberately unresolved)** · 0004 falsified (P2E) · 0005/0006 falsified (GATED-S-001/002,
  gate-scoped) · **0007 validated (GATED-S-003 count gate, gate-scoped)**. Mapping:
  `receipts/LEDGER_RECONSTRUCTION_2026-09-17.md`.

## 4. Discipline rules (non-negotiable, earned the hard way)

1. **Nothing runs before its freeze receipts** (plan + holdout; implementation freeze before
   cells). Every freeze pins hashes; any change re-baselines.
2. **Fresh holdout for every confirmation.** Discovery and confirmation sets never swap roles;
   scored seeds are burned.
3. **Raw + adjudicated reporting** with the audit protocol (flags always published, never
   deleted). Never silently drop questions.
4. **No tuned weights, no blended scores, no benchmark-derived parameters.** Thresholds come
   from declared batteries/designs only. Ablate everything with behavioral teeth.
5. **WEAK stays WEAK** — do not narrate outcomes upward (or downward) after the fact.
6. **Headroom-aware reach:** `H = (R_exp − R_base)/(N − R_base)` only when the baseline has ≥ 4
   misses; otherwise the endpoint is ceiling-limited and ordering carries the claim.
7. **T8 is an external capability probe** (0/15 in every experiment; the missing primitive is a
   general semantic bridge). **T9 stays an untouched guardrail.**
8. **R1 pair gating remains paused** until selection is understood (Phase 3 closed 2026-09-17 on
   the ratified entry decision; R1 itself stayed rejected).

## 5. Known pitfalls (learned in-session)

- **Stale binary:** `cargo test` does not rebuild bins. Run `cargo build --release --offline`
  before any harness run. One A1 run was invalidated this way (caught by journal schema).
- **Journals append:** use a fresh `WM_GEN3_JOURNAL` per run, or you get mixed runs in one file.
- **Duplicate statement texts** exist in corpora: dedup for display, but map cosines by both
  name and text (done in `failure_taxonomy.py`).
- **Representative current turn** = the *latest* value-bearing turn; older turns with the same
  value string may be legitimately superseded (fixed in taxonomy).
- **Substring artifacts:** `sport` ⊂ `transport`; match token/phrase boundaries (audit v1.2).
- **`--bm25-only` in the harness is a no-op** (does not switch the retrieval route).
- **Query-time projection cost** is dominated by per-process model reload (~180 ms) + embedding;
  warm throughput ≈ 0.1 texts/ms on this CPU. Not optimized by design.
- **Control T8 advantage** comes from hand-authored enrichment (`enrichment.rs`), not contradiction
  machinery — attribute T8 losses to bridging.
- **Coin the next metric before the next run** — reach bars need headroom; margins need defined
  blocker semantics.

## 6. Open threads (for whoever picks this up)

0. **Testbed II (A)** — **CLOSED** (this session): `experiments/testbed_ii/a/REPORT_A.md`.
   Q1 yes (R improves ordering), Q2 projection inert, Q3 ceiling-limited/non-inferior,
   Q4 LEX_TAU non-transfer. Findings F-A1..F-A5 in report §7.
1. **Testbed II (C) pre-pilot** — closed (previous session); see `REPORT_PRE_PILOT.md`.
2. **TIE class diagnosis** (equal-evidence inversions) — Testbed II shows 1 TIE on 40
   correct-label Q; own study still open. **Parked (2026-09-17):** no study opened; the class
   stays visible in the taxonomy; re-entry only with a fresh registration + holdout.
3. **Audit protocol v1.3** — now frozen and validated (Testbed II (A)); v1.2 stays pinned
   for Phase 2 corpora. The old seed-18 `book_genre` case is still unresolved for v1.2.
4. **Projection-agreement ordering** — with projection inert on Testbed II (F-A1), decide
   whether the carried diagnostic (projection-agreement ordering) has a future at all.
   **Dormant (2026-09-17):** not adopted as an ordering view; re-entry requires a new
   registration + fresh holdout (multi-view notes remain the map).
5. **Multi-view selection direction** (`RESEARCH_NOTES_MULTI_VIEW_SELECTION.md`) — evidence
   bundles / Pareto / context arbitration; explicitly not implemented.
6. **Phases 3+** run under the entry decision record; Gen2 v9.1.7 remains product and control
   (production tree untouched throughout — WMgen3 has never written to `WMv9`).
7. **≥2-candidate semantic-insufficiency boundary** — parked (2026-09-17) as its own research
   question; not a Phase-3 work item, no `<3` staircase. gated3 disclosed
   `MissedOpportunity₊₂ = 1.000`; T2 fires are a priced-in cost of the confirmed `count < 2`
   rule. Re-entry would be a new registration, not a threshold extension.
8. **Code-walk findings (2026-09-19; errata L #54–55):** recall's projection-on path writes the
   query embedding cache (`embed_cache`; `docs/READ_PATH_AUDIT.md` corrected); `remember_batch`'s
   vector-write failure persists the record while returning `Err` (partial-outcome semantics
   beyond the A1 declared cases); `store.rs` wire decode coerces unknown enum bytes to defaults
   instead of refusing. Flagged for future registration; none changes a verdict.
