# WhiteMagic Governance Kernel: Formally Verified in Bend 2

Executable specification and formal verification of WhiteMagic's capability-security and evolutionary governance invariants in **Bend 2**, compiled to **BendTT** interaction-combinator lambda terms.

---

## Overview

Bend 2 introduces **Law-Driven Development**: reference observers are defined in `SPEC.bend`, open claims are stated in `LAWS.bend`, the implementation is written in `main.bend`, and constructive proofs verifying those claims are written in `PROOF.bend`. The Bend compiler verifies all laws via `bend PROOF.bend` (`ALL PROOFS CHECK`).

`whitemagic_governance` models capability security and autonomous agent governance invariants using Bend's affine dependent type system ($q=1$).

---

## The 9 Formally Verified Invariants

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

---

## File Structure

* [`main.bend`](./main.bend): Core executable types (`Cap`, `ScopeToken`, `PassSlot`, `Fate`, `Hexagram6`, `PrayMask`) and state transition functions.
* [`SPEC.bend`](./SPEC.bend): Pure reference observers and specification predicates (`has_cap`, `implies`, `can_execute`, `is_promoted`, `expected_next_epoch`).
* [`LAWS.bend`](./LAWS.bend): Specification file containing the 9 formal law statements.
* [`PROOF.bend`](./PROOF.bend): Complete constructive proofs for all 9 laws checking via case analysis, structural induction, and equality rewrites.
* [`LICENSE`](./LICENSE): MIT License (`SPDX-License-Identifier: MIT`).

---

## Reproducing & Publishing

### 1. Verify All 9 Laws
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

### 3. Import from BendHub (`0xe7cbe6684dd31616b6b8e2f83096a120`)
Published permanently to BendHub under MIT License (`0xe7cbe6684dd31616b6b8e2f83096a120`):
```bend
import Base
import 0xe7cbe6684dd31616b6b8e2f83096a120/main.bend as WM
import 0xe7cbe6684dd31616b6b8e2f83096a120/LAWS.bend as LAWS
import 0xe7cbe6684dd31616b6b8e2f83096a120/PROOF.bend as PROOF
```
Verify with the formal Lean 4.34.0 BendTT kernel:
```bash
BEND_NO_TELEMETRY=1 bend PROOF.bend --verdict
```
