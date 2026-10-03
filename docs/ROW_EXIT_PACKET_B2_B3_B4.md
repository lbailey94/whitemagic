# Row-exit packet — B2 · B3 · B4 (The Outer Envelope — for operator review)

**Prepared 2026-09-18 (session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7`) · status: EXITED — RATIFIED 2026-09-18.**
Wave plan §2 exit criteria: frozen/grounded specs + adversarial cases wired + ablation designed/demonstrated + journal events declared + receipt; **no inert acceptance test**. This packet completes the outer envelope of Wave 1, establishing the boundary physics of Gen3 as a **Minimal Cognitive Runtime**:

1. **B2 (Temporal Identity)**: Storage/lifecycle preserved as link (`session.*`), continuity/digest compile-side (`recall` + `think`), nodiscovery checkpoints, lossless replay shape (IDs, timestamps, tags), zero empty handoff shells, anti-bloat canon. Waking up to recover exact operational state without fabricating context.
2. **B3 (Negotiated Occupancy)**: Lease ledger enforcement link (`code.claim`) over same-filesystem / shared-store processes, mandatory intent, collision naming, exact-owner release via `lease_id`, read-only snapshot invariance, always-releasable typed-effect asymmetry (`Resource::CoordinationRelease` policy admission guaranteed), pure filesystem discovery. Clear rules for who may act on a scope, why, and how it is relinquished.
3. **B4 (Epistemic Accountability)**: Belief-class records distinct from evidence records (Part 1 Invariant 9), 100% resolution completeness with validation evidence pointers, statutory Brier calibration + Wilson 95 + Empirical-Bayes shrinkage ($w=n/(n+k)$, statutory $k=20.0$), empty-data disclosure (`insufficient_data`), write-through durability. Never rewriting past belief; deriving future calibration from resolved reality.

---

## B2 — Sessions & Continuity (Temporal Identity)

- **Spec:** `docs/specs/W1_B2_sessions_continuity.md`.
- **Implementations:**
  - Link side: `WHITEMAGIC/WMv9/crates/wm-tools/src/expansion/session.rs` and `session_ops.rs` (3,047 LOC).
  - Compile side: Gen3 `recall` over session tags + `think` synthesis; anti-bloat canon (0 session modules in Gen3 core).
- **Acceptance §5:**
  1. Lossless replay shape: `session.export` $\rightarrow$ `session.import` preserves IDs, timestamps, and tags; `session.replay` excludes superseded turns by default and restores lossless on `include_superseded: true`.
  2. No payload-less shells: empty handoffs and missing payloads refused loudly (`import_rejects_missing_payload`); stored checkpoints carry concrete handoff payloads; W0 errata #30 defect class permanently excluded.
  3. Resolution semantics: time-based `created_at` resolution picks newest prior session with turns; empty candidate bypassed; empty store discloses truthful project scoping (`continuity_empty_store_discloses_project_scoping`).
  4. Nodiscovery proof: `session.checkpoint_nodiscovery` stores exact caller-supplied fields with 0 reads, 0 spawns, 0 git discovery; strict mode admits it; git-capturing `session.checkpoint` declares `Resource::Filesystem`, `Resource::Process`, `spawns: true` and is refused under strict mode.
  5. Phrase table test (#2): all `PHRASE_ROUTES` continuity entries route bare and trailing to `session.continuity` before tokenization with confidence 1.0; stopword-only drop prevented. Live MCP verified.
  6. Write-time indexing: write-time Tantivy indexing on `session.record` and `session.import`; drift 0 while serving, unchanged after shutdown.
  7. Superseded visibility: `load_turns` hides superseded turns by default; `include_superseded: true` restores full historical visibility.
  8. Gen3 Anti-Bloat Canon: zero session modules in Gen3 core; zero `wm-tools`/`wm-memory` in `cargo tree`; all closure checks PASS.
- **Bundle:** `receipts/impl_w1_b2_2026-09-18/` (sha256 `f43e403d…`, 54 native Rust contract assertions passed, 8/8 suites green).
- **Receipts:** `receipts/IMPL_W1_B2_ACCEPTANCE_2026-09-18.md`, `receipts/W1_ROW_EXIT_B2_2026-09-18.md`.
- **Disposition:** EXITED / RATIFIED 2026-09-18.

---

## B3 — Coordination & Leases (Negotiated Occupancy)

- **Spec:** `docs/specs/W1_B3_coordination.md`.
- **Implementations:**
  - Link side: `WHITEMAGIC/WMv9/crates/wm-tools/src/expansion/coordination.rs` (shared ledger `<git-common-dir>/wm-leases.json`).
  - Gen3 side: statutes + journal; no lock machinery re-derived in Gen3 core.
- **Scope Qualification**: Demonstrated results strictly apply to same-filesystem / shared-store coordination among local processes using lockfile-guarded atomic renames. Distributed coordination across independent hosts over network filesystems is reserved for a future dedicated Sangha LAN campaign.
- **Acceptance §5:**
  1. Two-writer case: scope collision returns `status: conflict` naming `holder` + mandatory `holder_intent`; exact-owner release enforced via `lease_id`; non-owners refused with `status: not_owner`; scope transitions to `free`.
  2. Read-only discipline: `code.check` and `code.list` execute snapshot-readonly; ledger sha256 invariant; 0 lock/tmp files; expired leases logically absent on check and reportable on list (`include_expired: true`).
  3. Typed-effect asymmetry (9.1.8): `CodeClaimTool` carries `Resource::CoordinationLease` (refusable under stress); `CodeReleaseTool` carries `Resource::CoordinationRelease` (always admitted). Admission policy guarantees work may be refused; relinquishment is never trapped.
  4. Root binding: alternate/escaping root refused when configured root is set; alternate checkout ledger untouched.
  5. Pure filesystem discovery: `.git`/`commondir` resolution walks filesystem directly with 0 subprocess spawns.
  6. Gen3 Anti-Bloat Canon: zero lock/coordination modules in Gen3 core; statutes + journal carry governance; all closure checks PASS.
- **Bundle:** `receipts/impl_w1_b3_2026-09-18/` (sha256 `44099ebf…`, 15 native Rust contract assertions passed, 6/6 suites green).
- **Receipts:** `receipts/IMPL_W1_B3_ACCEPTANCE_2026-09-18.md`, `receipts/W1_ROW_EXIT_B3_2026-09-18.md`.
- **Disposition:** EXITED / RATIFIED 2026-09-18.

---

## B4 — Claims / Belief Class (Epistemic Accountability)

- **Spec:** `docs/specs/W1_B4_claims_belief_class.md`.
- **Implementations:**
  - Link side: `WHITEMAGIC/WMv9/crates/wm-simulation/src/claims.rs` and `crates/wm-tools/src/expansion/claims_tools.rs`.
  - Gen3 compile side: belief-class records, statutory calibration statistics, Part 1 Invariant 9 (belief $\neq$ evidence).
- **Statutory Qualification**: The empirical-Bayes prior sample weight ($k = 20.0$, `CALIBRATION_PRIOR_SAMPLES`) is an explicitly **statutory policy parameter**, not a constitutional law of Gen3 physics. The constitutional invariant is: *Never rewrite original belief; derive calibrated belief from resolved history.* The calibration formula remains versioned, replaceable, and experimentally justifiable.
- **Empty-Data Semantics**: On an empty ledger ($n=0$), the identity transform mathematically represents a neutral no-op, epistemically reported as `calibration_status = insufficient_data`; it does not constitute evidence of raw confidence validation.
- **Acceptance §5:**
  1. Resolution completeness: every resolved claim requires a concrete `ValidationEvent`, date, and traceable provenance source (`source`); resolution pointer rate 100%; resolution irrevocable (`cannot_resolve_twice`); falsifications recorded as misses without oracle confounding. External public web disclosure is not required (local/private cryptographically verifiable sources are admissible).
  2. Calibration reproducible: Brier score (0.1350), gap (−0.1000), hit rate (0.7500), mean confidence (0.6500), Wilson 95 score interval, and empirical-Bayes shrinkage weight ($w=n/(n+20)$) recomputed from raw match output to $10^{-12}$. Raw confidences unchanged on disk.
  3. No destructive sync fixture: seeding over independent rows deletes 0 rows.
  4. Expiry universe: uniform statutory handling of expired claims.
  5. Durability: synchronous write-through on add and resolve; ungraceful kill loses 0 mutations.
  6. Universe labels & Anti-Bloat Canon: calibration outputs name the claims-ledger resolved set; Part 1 Invariant 9 enforced; all Gen3 closure checks PASS.
- **Bundle:** `receipts/impl_w1_b4_2026-09-18/` (sha256 `dea2091f…`, 21 native Rust contract assertions passed, 6/6 suites green).
- **Receipts:** `receipts/IMPL_W1_B4_ACCEPTANCE_2026-09-18.md`, `receipts/W1_ROW_EXIT_B4_2026-09-18.md`.
- **Disposition:** EXITED / RATIFIED 2026-09-18.

---

## Build Provenance Across B2 · B3 · B4

The Gen3 binary hash `target/release/wm-gen3` remained identical across all three receipts:
`a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`
This consistency confirms that Gen3 core required zero code modifications to support B2, B3, and B4—validating the split architecture and anti-bloat canon.

---

## Master Wave 1 & Wave 2 Envelope Summary

With B2, B3, and B4, the entire **Outer Envelope** across Wave 1 and Wave 2 is fully implemented, verified, grounded, and prepared for operator ratification:

| Row | Name | Layer / Split | Status | Evidence Bundle |
|---|---|---|---|---|
| **A1** | Durable store ingestion | Gen3 Core Primitive | **EXITED / RATIFIED** | `impl_a1_2026-09-17` |
| **A2** | Evidence disclosure | Gen3 Core Primitive | **EXITED / RATIFIED** | `impl_a2_2026-09-17` |
| **A3** | Revisions & supersession | Gen3 Core Primitive | **EXITED / RATIFIED** | `impl_a3_2026-09-17` |
| **B1** | Retrieval & ranking | Gen3 Core Primitive | **EXITED / RATIFIED** | `impl_b1_acceptance_2026-09-17` |
| **B2** | Sessions & continuity | Link + Compile Split | **EXITED / RATIFIED** | `impl_w1_b2_2026-09-18` (`f43e403d…`) |
| **B3** | Coordination & leases | Link + Statutes Split | **EXITED / RATIFIED** | `impl_w1_b3_2026-09-18` (`44099ebf…`) |
| **B4** | Claims / belief class | Link + Compile Split | **EXITED / RATIFIED** | `impl_w1_b4_2026-09-18` (`dea2091f…`) |
| **B5** | Galaxies & recall views | Gen3 Provenance View | **EXITED / RATIFIED** | `impl_b5_recall_view_2026-09-17` + `impl_scorer_determinism_2026-09-18` |
| **W2_01** | Relations & associations | Gen3 Field Edges | **EXITED / RATIFIED** | `impl_w2_01_2026-09-17` |
| **W2_02** | Retention & lifecycle | Invariant (`records ≠ relations`) | **EXITED / RATIFIED** | `impl_w2_02_2026-09-18` (`e7c95b88…`) |
| **W2_03** | Currentness strata | Request-time Strata View | **EXITED / RATIFIED** | `impl_w2_03_07_2026-09-17` |
| **W2_04** | Dream & consolidation | Invariant (`consolidation ≠ deletion`) | **EXITED / RATIFIED** | `impl_w2_04_2026-09-18` (`a53a47f6…`) |
| **W2_07** | Self-model inspect | Read-only Inspection View | **EXITED / RATIFIED** | `impl_w2_03_07_2026-09-17` |

*Strategic Roadmap Post-Ratification*:
- Freeze current substrate as **Gen3 Minimal Cognitive Runtime Baseline**.
- **W2_05 (Recipe layer)**: Must earn its existence through empirical expressibility experiments; no speculative abstractions.
- **W2_06 (RSI over journal)**: Gated on independent four-way role separation (`proposer ≠ evaluator ≠ authority ≠ deployer`).

---

## Operator Review & Ratification Block

- [x] Operator review completed
- [x] Operator ratification directive: "I ratify; sign them, and we'll move forward and discuss our next steps - it sounds like we need to test and benchmark extensively before further additions / refinements to the code." — Lucas Bailey (operator) — Date: 2026-09-18
- [x] B2, B3, B4 status promoted to EXITED / RATIFIED
