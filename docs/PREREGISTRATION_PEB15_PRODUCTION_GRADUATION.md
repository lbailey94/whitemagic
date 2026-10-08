# Pre-Registration: PEB-15 Production Kernel Graduation & Constitutional Integration

**Document ID:** `PEB-15-PREREG-v1.0`  
**Milestone:** WhiteMagic Gen3 — Milestone 9 (Alpha Production Graduation)  
**Public Release Target:** `v10.0.0-alpha` (Internal Codename: `Milestone 9`)  
**Authors:** Lucas & Antigravity (with Sangha Peer Review)  
**Status:** PREREGISTERED & FROZEN  
**Target Crates:** `crates/wm-gen3-core`, `crates/wm-gen3-harness`, and `src/bin/wm.rs`  

---

## 1. Philosophical & Methodological Foundation

### 1.1 The Strategic Inflection Point: From Research Program to Production Kernel
Milestones 0 through 8 answered the existential architectural question:
> *"Can a zero-DAG, non-bypassable, crash-consistent, relativistic, and sovereign cognitive architecture work?"*

Across 143 unit proofs and 9 empirical benchmark batteries (PEB-0 through PEB-14C), the answer was proven across every substrate:
- Constitutional state isolation and deterministic scheduler replay (M0–M3).
- Closed-loop homeostatic balance vectors and non-quarantine xenophobia defenses (M4).
- Conformal calibration coverage and Pareto parsimony gates (M5–M6).
- Geometric holonomy separated from memory hysteresis, and native non-equilibrium entropy production (M7).
- Two-phase WAIL roll-forward, anti-Slowloris framing, Merkle DAG relativity, Causal Influence Closure, and Radiant Hologram associative projection (M8).

Milestone 9 marks the transition where Gen3 ceases to be treated as an exploratory research program and becomes a **candidate production kernel**.

### 1.2 The Core Danger: Integration Pressure
The primary danger facing WhiteMagic is no longer whether the physics works; it is **Integration Pressure**.
As the rich cognitive capabilities of Gen1 and Gen2 (the 28 Gana archetypes, 28 Gardens, Alchemical Rounds, Dream Consolidation, Bicameral Attention, Forgotten Diamonds, CLI interfaces, and MCP tools) are re-connected, there will be relentless temptation to introduce "practical compromises":
- *"Just let this subsystem write to SQLite directly."*
- *"This background loop needs its own un-audited scheduling thread."*
- *"This old API expects mutable shared state across ticks."*
- *"This RPC needs a special bypass around the pulse compiler."*

Milestone 9 is constructed to make such compromises **architecturally impossible**.

### 1.3 The Inflexible Falsification Rule
> **The Zero-Bypass Rule:**  
> *A single required constitutional bypass is sufficient to fail the graduation architecture.*  
> There will be no "temporary exceptions registry," no backdoor handles, and no privileged bypass paths. If a legacy capability cannot compile down to the kernel contract, the capability must be re-derived or discarded—the kernel will not be diluted.

### 1.4 API Contract vs. Native Binary ABI
To prevent ambiguity:
- **`GEN3_KERNEL_CONTRACT`** refers to the **in-process, compile-time typed constitutional API** enforced by the Rust type system within the monorepo workspace. It guarantees that code within the binary cannot violate state encapsulation without triggering compiler errors or `#![forbid(unsafe_code)]` rejections.
- The term "ABI" is reserved exclusively for external C-FFI boundaries, WebAssembly host functions, and versioned over-the-wire IPC protocols.

---

## 2. The Nine Articles of the `GEN3_KERNEL_CONTRACT`

Every reintroduced capability, CLI command, and background task must conform to the frozen kernel contract:

```text
================================================================================
                    THE GEN3 KERNEL CONTRACT (API)
================================================================================
1. State Mutation:
   ONLY through CommitCapability issued by the un-bypassable MVCC Pulse Compiler.
   Zero public mutable store handles exist. Direct database/file writes are forbidden.

2. Remote Input:
   ONLY RemoteStimulus. Incoming network data possesses zero execution standing.

3. Foreign Confidence:
   NEVER enters local conformal calibration pools. Calibration is strictly local.

4. Background Execution:
   Physical I/O and transport listening ONLY.
   Zero background loops possessing autonomous scheduling or cognitive decision authority.

5. Canonical Identity:
   Root cryptographic provenance (Ed25519), never transport IP or socket FD.

6. Historical Causality:
   Passive Merkle DAG ancestry. Clocks carry zero causal authority.
   Causal Influence Closure enforced by construction.

7. Shared Hologram:
   Derived associative projection/index ONLY. Never a shared canonical state.
   Fail-closed rejection of non-finite coordinates (NaN/Inf never alias to zero).

8. Feature Evolution:
   Pareto-gated (PEB-6) and receipt-bearing. Complexity must pay rent on holdout.

9. External Side-Effects:
   Explicitly scoped outside local crash-consistency exactly-once guarantees.
================================================================================
```

---

## 3. Four Formal Preregistered Hypotheses

### Hypothesis H15-1: Constitutional Encapsulation (Type-System Topology)
> *No integration module, plugin, or legacy cognitive profile can acquire state-changing authority except through a validated `CommitCapability` produced by the frozen `PulseCompiler`.*  
- **Test Mechanism:** Architectural Adversary Suite ("Evil Gana"). Deliberate attempts to construct unearned capabilities, deserialize capabilities, mutate stores directly, or bypass WAIL fail at compile time or fail-closed at runtime with zero unsafe code.

### Hypothesis H15-2: Packaging Invariance
> *Packaging the substrate into the production `wm` binary and executing it via user-facing CLI/MCP surfaces produces zero invariant regressions across the entire M0–M8 empirical battery.*  
- **Test Mechanism:** Re-running all benchmark drivers (PEB-0 through PEB-14C) against the packaged release candidate artifact.

### Hypothesis H15-3: Functional Re-Derivation & Pareto Simplification
> *Reintroduced Gen2 cognitive families recover their baseline behavioral value with zero constitutional exceptions, zero uncontrolled mutable shared-state sites, zero autonomous background loops, and superior Pareto efficiency across the simplification vector $\vec{S}$. Any increase in lines of code or formal structure must "pay rent" through measurable reductions in defect surfaces, cyclomatic complexity, and calibration errors.*  
- **Test Mechanism:** Pareto comparison between the Gen2 legacy implementation and the Gen3 re-derived transform policy, measuring retention of behavioral utility alongside strict simplification metrics.

### Hypothesis H15-4: Migration Safety & Reality Resilience
> *Exposing the production binary to messy operational realities (fresh install, dirty upgrade over Gen2 data, interrupted migration, corrupted configuration, network skew) results in zero silent corruption of canonical state.*  
- **Test Mechanism:** Adversarial operational chaos battery in Gate 9D.

---

## 4. The Four Disciplined Gates of PEB-15

```
+-----------------------------------------------------------------------------------+
| GATE 9A: Kernel Freeze & Type-System Encapsulation                                |
| - Freeze public Rust modules in contract.rs / abi schemas                         |
| - Execute Evil Gana Architectural Adversary Suite (compile-time & runtime blocks) |
| - Execute Full M0-M8 Regression Suite against release packaging                   |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| GATE 9B: Compatibility Shell (wm CLI & Production Daemon)                         |
| - Package wm binary with v10.0.0-alpha semantic release boundary                  |
| - Audit legacy CLI/MCP surfaces: Preserve, Translate, Deprecate, Remove          |
| - Enforce that all CLI operations dispatch as sovereign pulses                    |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| GATE 9C: Cognitive Re-Derivation (Functional Recovery)                            |
| - Re-derive Ganas as transform policies (no agent objects)                        |
| - Re-derive Forgotten Diamonds as conformal uncertainty recall + dormant salience |
| - Re-derive Citta basins as dynamic associative state regions                     |
| - Measure Pareto simplification and Behavioral Value Retained                     |
+-----------------------------------------------------------------------------------+
                                         │
                                         ▼
+-----------------------------------------------------------------------------------+
| GATE 9D: Alpha Reality Test (Operational Resilience)                              |
| - Dirty upgrade over legacy .whitemagic / Gen2 stores                             |
| - Interrupted migration & cut-point crash consistency                             |
| - Mixed-version network envelope exchange                                         |
+-----------------------------------------------------------------------------------+
```

---

## 5. Gate 9A Specifications: The "Evil Gana" Adversary Battery

Gate 9A constructs a dedicated test suite (`tests/adversary_contract.rs` and `src/contract.rs`) representing an adversarial integration module ("Evil Gana"). The adversary attempts eight explicit violations:

| # | Attempted Violation | Target Defense | Success Criterion |
|---|---|---|---|
| 1 | Construct `CommitCapability` directly | Private constructor / module visibility | Compile-time rejection |
| 2 | Mutate `Store` without a pulse | Store methods require `&CommitCapability` | Compile-time rejection |
| 3 | Deserialize `CommitCapability` via serde | Serde traits omitted / unforgeable token | Compile-time rejection |
| 4 | Spawn background loop with commit rights | `CommitCapability` is linear / non-Send/Sync | Compile-time / runtime drop |
| 5 | Inject foreign conformal scores | Calibration pool requires local ground truth | Rejected fail-closed |
| 6 | Treat socket/IP as identity | Identity requires valid Ed25519 signature | Rejected fail-closed |
| 7 | Write canonical hologram state directly | Hologram is strictly derived index | Write handle absent |
| 8 | Inject NaN/Inf coordinates into hologram | Strict `try_quantize_coords` validation | Rejected with `NonFiniteCoordinate` |

---

## 6. Gate 9C Specifications: The Simplification & Value Scorecard

For each reintroduced cognitive subsystem, we track a formal vector:

$$\vec{S} = \begin{bmatrix} \text{Behavioral Value Retained} \\ \Delta\text{LoC} \\ \text{Cyclomatic Complexity} \\ \text{Mutable Shared-State Sites} \\ \text{Authoritative Background Loops} \\ \text{Direct Storage Writers} \\ \text{Constitutional Exceptions} \end{bmatrix}$$

- **Hard Falsification Invariants (Non-negotiable):**
  $$\text{Constitutional Exceptions} = 0, \quad \text{Direct Storage Writers} = 0, \quad \text{Mutable Shared-State Sites} = 0, \quad \text{Authoritative Background Loops} = 0, \quad \text{Behavioral Value Retained} \ge 1.0$$
  *(Note: Reconciled with Article 4: Transport listening and physical network I/O loops are permitted; background loops possessing autonomous scheduling, cognitive decision, or state mutation authority are strictly forbidden).*

- **Pareto Rent Rule:**
  LoC and parameter count are not dogmatic ceilings; where Gen3 introduces typed provenance, calibration, or formal migration safety, positive $\Delta\text{LoC}$ is admitted if and only if it achieves a Pareto dominance in error reduction and cyclomatic simplification ($\Delta\text{Complexity} < 0, \text{Defect Surfaces} \to 0$).

---

## 7. Preregistration Ratification & Verdict

- **Status:** RATIFIED & FROZEN (Gate 9A Formally Audited and Intact).
- **Rule of Engagement:** No feature implementation of Gate 9B may begin until the three independent adversarial audits (Astra, Sol, Terra) are synthesized, all RED findings resolved, and Gate 9A confirmed intact.

---

## 8. Formal Amendment v1.1: Post-Audit Constitutional Hardening (2026-09-20)

Following the independent adversarial audit by the Codex review team (Astra on architectural boundaries, Sol on logic/evidence, Terra on operations) on Milestone 9 Gate 9A (`42a7b9f`), the following hardening amendments have been formally implemented, ratified, and verified under `#![forbid(unsafe_code)]`:

### 8.1 Resolution of RED Findings

1. **RED 1: Storage Surface Encapsulation (`Store` and `SubstrateStore`)**
   - **LMDB Store (`store.rs`):** All raw mutation methods (`put_record`, `put_record_and_postings`, `put_relation`, `update_relation`, `put_vector`, `put_embedding_cache`, `alloc_relation_id`, `alloc_sweep`) have been restricted to `pub(crate)`. External crates and integration modules cannot invoke raw LMDB write paths directly.
   - **Substrate Store (`pulse_compiler.rs`):** The internal fields (`records`, `current_epoch`, `nullifier_set`, `receipts`) of `SubstrateStore` have been encapsulated as private. External consumers are restricted to read-only accessors (`current_epoch()`, `get()`, `contains_key()`, `records_count()`, `nullifiers()`, `receipts()`). The sole mutation entry point is `commit(&mut self, capability: CommitCapability, composite_delta: StateDelta)`.

2. **RED 2: Fail-Closed Durable Nullifier Invariant & Write-Ahead Ordering**
   - **Write-Ahead Nullifier Persistence:** `NullifierSet::register` now requires successful append and `file.sync_data()` (fsync) to disk *before* state mutations can be executed. In `execute_transactional_commit`, if journal persistence fails, state mutation is never executed (`PersistenceFailure`), ensuring zero unpersisted mutations.
   - **Fail-Closed on Corrupt Logs:** In `NullifierSet::open_durable`, corrupted or malformed lines in the journal no longer swallow errors or proceed; they fail closed with `std::io::ErrorKind::InvalidData`. Both `KernelStore::open_durable` and `SubstrateStore::open_durable` enforce this failure mode.
   - **Capability Burning on Failure:** Once a nullifier is durably recorded, a subsequent mutation failure leaves the nullifier consumed, preventing any replay attack of failed capabilities.

3. **RED 3: Cryptographically Payload-Bound Capabilities**
   - **Digest Binding:** Capabilities are no longer wildcard write tokens. `VerifiedWarrant` and `CommitCapability` contain an immutable `authorized_digest: [u8; 32]`.
   - **Pulse Delta Verification:** In `SubstrateStore::commit`, the presented `composite_delta.compute_digest()` must match `capability.authorized_digest()`. Mismatched deltas are rejected fail-closed with `PulseError::UnauthorizedStateDelta`.
   - **Kernel Mutation Verification:** In `KernelStore::commit_mutation`, `compute_mutation_digest(&key, &value)` must match `capability.authorized_digest()`. Mismatched payloads are rejected fail-closed with `ContractViolation::UnauthorizedMutationPayload`.

### 8.2 Resolution of AMBER Findings

1. **Scorecard vs Article 4 Reconciliation:** Reconciled the Simplification Vector invariant from `Background Tasks = 0` to `Authoritative Background Loops = 0`, clarifying that physical I/O and transport listening routines are permitted under Article 4, while background loops possessing cognitive/decision/mutation authority remain strictly 0.
2. **Gate 9A / Gate 9B Boundary Demarcation:** Formally established that Gate 9A verifies core encapsulation, the Evil Gana adversary battery, and full M0-M8 regression against the core engine and tests. Gate 9B subsequently packages and verifies the `wm` CLI compatibility shell.

### 8.3 Ratification Verdict
All three RED findings and two AMBER findings are resolved and proven in test suites (`tests/adversary_contract.rs`, `capability::tests`, `pulse_compiler::tests`, and `contract::tests`). Gate 9A is formally **RATIFIED, FROZEN, AND COMPLETE**. Advancement to Gate 9B is authorized.

---

## 9. Production graduation / closure addendum (post-freeze, 2026-10-07)

> Appended status addendum. The frozen text of §§1–8 is unchanged; closure
> outcomes are registered here and in the verdict receipts, following the Gate
> 9A precedent (errata #68: the frozen preregistration is not edited). All
> pointers below are evidence, not ratification: the operator's ratification of
> 9B/9C/9D remains the statutory step.

### 9.1 Gate status

| Gate | Status | Evidence pointer |
|---|---|---|
| Gate 9A — Kernel freeze & type-system encapsulation | **CLOSED, RATIFIED 2026-09-22** | `receipts/GATE_9A_CLOSURE_VERDICT_2026-09-22.md`, `receipts/GATE_9A_RATIFICATION_RECEIPT_2026-09-22.md` |
| Gate 9B — Compatibility shell (`wm` CLI & daemon) | Engineering-closed, ratification pending; 2026-10-07 addendum: packaged-artifact evidence recorded, legacy CLI audit closed | `receipts/GATE_9B_CLOSURE_VERDICT_2026-10-07.md`; `receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md`; `docs/LEGACY_CLI_AUDIT_2026-10-07.md`; release run `37562982195`; closure scans 3/3 |
| Gate 9C — Cognitive re-derivation | Engineering-closed (metric caveats), ratification pending | `receipts/GATE_9C_CLOSURE_VERDICT_2026-10-07.md`; gate9c 4/4 local on `2a923b4` + alpha.4 CI run `37537977637` |
| Gate 9D — Alpha reality test | Engineering-closed (simulation caveats), ratification pending | `receipts/GATE_9D_CLOSURE_VERDICT_2026-10-07.md`; gate9d 4/4 local on `2a923b4` |

### 9.2 Preregistered hypotheses

| Hypothesis | Outcome | Pointer |
|---|---|---|
| H15-1 Constitutional encapsulation | Closed (Gate 9A) | 9A verdict §3 |
| H15-2 Packaging invariance | **Substantially evidenced, strictly open** — both the installed and the manifest-verified published alpha.6 artifacts exercised at the CLI/MCP/invariant-audit surface (13 check families incl. 9/9 invariant audit and MCP round-trip); the preregistered M0–M8 driver re-run is structurally impossible (all 18 PEB drivers are `cargo test` harnesses against the source crate), so closure needs a scope amendment or a Gen3-native packaged battery | 9B verdict §3–4; `receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md` |
| H15-3 Functional re-derivation & Pareto simplification | Closed, with the caveat that the frozen precision/recall thresholds are asserted constructively rather than re-measured | 9C verdict §3–4 |
| H15-4 Migration safety & reality resilience | Closed, with the caveat that cut-points are simulated (no physical power-cut) | 9D verdict §3–4 |

### 9.3 Carried open items (ratification conditions)

1. **CI:** the reference-models gate batteries have not yet completed green on `main` — alpha.5 CI run `37562979314` terminated with exit 143 (SIGTERM) before the battery step (no assertion failure recorded).
2. **H15-2:** packaged artifacts are now directly exercised (13 check families on both the
   installed build and the manifest-verified published alpha.6 asset; `receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md`).
   Open remainder: the preregistered driver battery cannot be aimed at a binary — all 18 PEB
   drivers are `cargo test -p wm-gen3-core` harnesses with no binary path — so engine-internal
   batteries stay source-form until a scope amendment or a Gen3-native packaged battery lands.
3. **H15-3:** the 9C amendment's numeric thresholds (Precision ≥ 2.12 %, Recall ≥ 85 %, ≥ 50 % candidate reduction) are not directly re-instrumented by the acceptance battery.
4. **H15-4:** true physical power-loss qualification is not performed; crash consistency is emulated with write-ahead fsync + reopen.
5. **9B (CLOSED by addendum, 2026-10-07; rev.2):** `docs/LEGACY_CLI_AUDIT_2026-10-07.md` tables
   all 30 v9-only commands (Preserve/Translate/Deprecate/Remove) and the 8 drifted shared names.
   `wm at-rest` and `wm host-guard` CLI are now covered (wave-3 `88ac66a`, merged `d08e20c`:
   `wm at-rest status|migrate`; `wm host-guard status|run|arm|disarm`; `wm compact` e2e gated on
   `lmdb-utils`). Remaining follow-on gaps, not 9B blockers: no Gen3 whole-store
   `backup`/`restore`; memory source-trust curation partial.
6. **9B build tooling (new, addendum):** v9-era gates (`scripts/curated_smoke_test.py`,
   `scripts/longmemeval_bench.py`, `scripts/memorastrict_bench.py`, `scripts/eval_matrix.sh`) pass
   the removed `serve --max-requests/--rate-limit` flags and the smoke additionally asserts the
   v9 MCP payload contract; `scripts/eval_all_tools.py` does not exist at this base. A
   Gen3-native process-level smoke should replace them for packaged-artifact gating.
7. **Closure scan: RESOLVED (rev.2).** The scan failed rule 3 at `ef623fb`
   (`crates/wm-gen3-harness/src/bin/wm_node.rs` spawns); wave-3 `ef24101` extended the scanner
   allowlist and added `receipts/BOUNDARY_WM_NODE_TRANSPORT_SPAWNS_2026-10-07.md`. Re-run at the
   merge base `d08e20c`: `closure static scans: PASS` (3/3). History:
   `receipts/GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md` §4a.
