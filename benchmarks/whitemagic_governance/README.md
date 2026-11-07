# WhiteMagic Governance Kernel: Formally Verified in Bend 2

Executable specification and formal verification of WhiteMagic's capability-security and evolutionary governance invariants in **Bend 2**, compiled to **BendTT** interaction-combinator lambda terms.

---

## Overview

Bend 2 introduces **Law-Driven Development**: reference observers are defined in `SPEC.bend`, open claims are stated in `LAWS.bend`, the implementation is written in `main.bend`, and constructive proofs verifying those claims are written in `PROOF.bend`. The Bend compiler verifies all laws via `bend PROOF.bend` (`ALL PROOFS CHECK`).

`whitemagic_governance` models capability security and autonomous agent governance invariants using Bend's affine dependent type system ($q=1$).

---

## The 16 Formally Verified Invariants (Laws 1–16)

| Law | Classification | Formal Invariant | Operational Guarantee |
|---|---|---|---|
| `capability_attenuation_monotone` | Capability Security | `has_cap(attenuate(P, M), c) => has_cap(P, c)` | Subagents and delegated tasks can only narrow permissions; authority cannot escalate. |
| `attenuation_idempotent` | Algebraic Soundness | `attenuate(T, T) == T` | Re-applying the same capability mask is an exact identity ($A \cap A = A$). |
| `jti_replay_rejected` | Linear Token Safety | `consume_pass(slot).can_execute == False` | Single-use Mandala passes strictly reject replay attempts upon consumption. |
| `pareto_never_promotes_regression` | Constitutional Safety | `has_regression => is_promoted(adjudicate) == False` | No candidate genome is promoted if any protected metric regresses. |
| `pareto_dominance_promotes` | Constitutional Liveness | `(!regression && fitness && provenance) => is_promoted == True` | A strictly dominant candidate with valid provenance is guaranteed promotion. |
| `hexagram_involution` | Geometric Symmetry | `invert_hex(invert_hex(h)) == h` | Complement mutation across all 64 King Wen Yijing hexagrams is a strict involution (${\sim}({\sim}H) = H$). |
| `superopt_idempotent_absorption` | Algebraic Optimization | `superopt(g, superopt(g, rest)) == superopt(g, rest)` | PRAY-phase denotation merging absorbs duplicates without altering semantics ($M \cup (M \cup R) = M \cup R$). |
| `pray_mask_commutative` | Algebraic Soundness | `merge_pray(a, b) == merge_pray(b, a)` | Conjunction of Sutra PRAY denotations is commutative ($A \cup B = B \cup A$). |
| `crystal_anti_rollback_monotonicity` | Monotonic Epoch Step | `advance_epoch(rev) == 1n + Nat.add(rev, 0n)` | Advancing a Citta Crystal revision epoch by `1n` equals the strict successor of the identity revision. |
| `sigma22_non_dispatching` | Wave 2 (`W2-P27`) | `has_cap(render_sigma22_symbol(lens), c) == False` | Rendering any $\Sigma_{22}$ symbolic spectrometer lens holds zero capability authority. |
| `zero_memory_auth_laundering` | Wave 2 (`W2-P25`) | `has_cap(resolve_authority(True, lease), c) == False` | Authority claimed from recalled memory never confers live capability rights. |
| `mmmbaby_non_compensatory_veto` | Wave 2 (`W2-P9`) | `mmmbaby_vitality(f1, f2, False, f4, f5, f6) == False` | Breaching any single vital floor vetoes composite vitality (zero sacrifice tolerance). |
| `prodrug_receptor_exclusivity` | Wave 2 (`W2-P32`) | `cleave_prodrug(False, epoch, seal) == False` | Intercepted prodrug envelopes outside their target receptor remain inert. |
| `y1_disarm_overrides_thresholds` | Wave 3 (`W3-P19`) | `y1_actuate(False, armed, enter, exit) == False` | Disarming `WM_ACTUATION=0` unconditionally forces Observe-only (`Step 0`), overriding all thresholds. |
| `runner_non_conflation_truth` | Wave 3 (`W3-P29`) | `claim_strict_os_isolation(False, egress, ll) == False` | Non-strict runner classes (`bwrap`-only) never falsely claim strict OS isolation. |
| `cpr06_authority_grant_required` | Wave 3 (`W3-P30`) | `ratify_cpr06_receipt(False, head, pq) == False` | Side-effecting Continuity Receipts missing an explicit `authority.grant` are rejected. |

---

## File Structure

* [`main.bend`](./main.bend): Core executable types (`Cap`, `ScopeToken`, `PassSlot`, `Fate`, `Hexagram6`, `PrayMask`, `Sigma22Lens`) and state transition functions.
* [`SPEC.bend`](./SPEC.bend): Pure reference observers and specification predicates (`has_cap`, `implies`, `can_execute`, `is_promoted`, `expected_next_epoch`).
* [`LAWS.bend`](./LAWS.bend): Specification file containing the 16 formal law statements (`Laws 1–16`).
* [`PROOF.bend`](./PROOF.bend): Complete constructive proofs for all 16 laws checking via case analysis, structural induction, and equality rewrites.
* [`LICENSE`](./LICENSE): MIT License (`SPDX-License-Identifier: MIT`).

---

## Reproducing & Publishing

### 1. Verify All 16 Laws
```bash
BEND_NO_TELEMETRY=1 bend PROOF.bend --check-only
```
**Output:**
```text
ALL PROOFS CHECK
Use --verdict for mathematical validity.
```

### 2. Execute the Governance Pipeline
```bash
BEND_NO_TELEMETRY=1 bend main.bend
```
**Output:**
```text
64n
```

### 3. Import from BendHub (`0x0e024c0379406f469e12da1d8267c06e`)
Published permanently to BendHub under MIT License (`0x0e024c0379406f469e12da1d8267c06e`, superseding 13-law `0x0d479d846e9ce92faa45a2346110fce8` and 9-law `0xe7cbe6684dd31616b6b8e2f83096a120`):
```bend
import Base
import 0x0e024c0379406f469e12da1d8267c06e/main.bend as WM
import 0x0e024c0379406f469e12da1d8267c06e/LAWS.bend as LAWS
import 0x0e024c0379406f469e12da1d8267c06e/PROOF.bend as PROOF
```
Verify with the formal Lean 4.34.0 BendTT kernel:
```bash
BEND_NO_TELEMETRY=1 bend PROOF.bend --verdict
```
