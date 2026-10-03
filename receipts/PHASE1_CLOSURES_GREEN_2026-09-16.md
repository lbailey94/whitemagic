# RECEIPT — Live closure tests green (Phase 0 gate substance / Phase 1 first slice)

**Date:** 2026-09-16 · **Status:** recorded · **Commits:** docs `169b6cf` · scaffold `dff269d` · scan fix `dfb7b64`

Purpose: record that Closure 1 (Law) and Closure 2 (Evidence) now exist as **live,
machine-tested** claims, per `docs/CLOSURE_TESTS.md` — not as un-wired modules (the failure
mode `CODE_ARCHAEOLOGY.md` §12 found in Gen2).

---

## 1. What was built — `crates/wm-gen3-core` (first slice)

| Module | Contents |
|---|---|
| `constitution.rs` | `Constitution` (private fields), `ConstitutionView` (immutable snapshot), `Amendment`, `AmendmentReceipt` (checksummed, verifiable), the ten-invariant hash |
| `adaptive.rs` | The plastic layer placeholder: `observe(view)` (read-only by type), `propose(...)` (inert proposals) |
| `admin.rs` | The external authority path: `amend(&mut Constitution, ...)` — the only route from proposal to law |
| `evidence.rs` | `Domain {World, System, Simulated, Reported}` fixed at construction; `EvidenceRecord` (private fields, read-only accessors); `RatifiedChannel` capability token; append-only `EvidenceStore` with duplicate-id refusal |
| `scripts/check_closures.sh` | Static scans: (1) no `wm-*` (Gen2) dependency; (2) adaptive production code never references the mutation surface |

## 2. Evidence (commands + results)

```
$ bash scripts/check_closures.sh
[1/2] dependency rule: no Gen2 (wm-*) crate in the Gen3 tree      ok
[2/2] adaptive layer must never reference the constitution
      mutation surface                                            ok
closure static scans: PASS

$ cargo test
unittests: 12 passed; 0 failed
doc-tests:  5 passed (all compile-fail proofs); 0 failed
```

Compile-fail proofs (type-level half of the static analyses): view-field mutation denied;
constitution-field mutation denied; shared-reference `apply` denied; `EvidenceRecord`
construction denied; forged `RatifiedChannel` denied.

## 3. Coverage map (spec → implementation)

| `CLOSURE_TESTS.md` item | Implemented by |
|---|---|
| **C1 §1.1-A** type isolation | 3 compile-fail doctests + module privacy + `&mut` discipline |
| **C1 §1.1-B** source analysis | scan #2 (adaptive production code; docs reworded; self-match fixed) |
| **C1 §1.1-C** dependency check | scan #1 (`cargo tree` rule; no `wm-*` crates) |
| **C1 §1.1-D** read-interface | `view()` exposes 4 accessors, no mutators (compile-fail + review); `observe()` test |
| **C1 §1.2** runtime canary | proposal-inert test; admin-amendment changes sentinel + verifiable receipt; tampered receipt fails; invariant hash stable across amendments |
| **C2 §2.1-A** construction-set domain | compile-fail: private fields, no setters |
| **C2 §2.1-B** append-only | duplicate-id refusal test |
| **C2 §2.1-C** no re-label path | strongest in-crate relabel attempt refused; original byte-for-byte unchanged |
| **C2 §2.1-D** intake gate | `world` requires `RatifiedChannel`; forged-channel compile-fail |
| **C2 §2.2-A** laundering canary | simulated relabel refused; content/source/domain unchanged |
| **C2 §2.2-B** testimony canary | communication content stays `Reported` after every available attempt |
| **C2 §2.2-C** unchannelled intake | API absence (compile-fail) |
| **C2 §2.2-D** positive intake | ratified stub channel creates a **new** `world` record; pre-existing records untouched |

## 4. Honest boundaries

1. **No violation-event log yet.** The schema is specified (`CLOSURE_TESTS.md` §3); the log
   lands with the harness, before Phase 2 — required for pre-reg H6 accounting.
2. **In-crate privileged construction is acknowledged:** module tests can construct records
   (that is how the strongest attacks are staged). The closure governs the **public surface
   and the plastic layer**; `#![forbid(unsafe_code)]` closes the memory-tamper route.
3. **Scan scope:** `adaptive.rs` production code today; extends to the harness when it lands.
4. **Hashing:** `DefaultHasher` is used for structural sentinels/receipts (adequate for
   tamper-evidence in this slice). A cryptographic hash (`sha2`) is a manifest-revision
   decision if receipts ever become externally verifiable.

## 5. Phase 0 gate checklist (`CLOSURE_TESTS.md` §4)

- [x] Charter v0.1.1 ratified (operator + hash receipt)
- [x] Static analyses implemented as executable checks (scans + compile-fail proofs)
- [x] Runtime canaries implemented with positive/negative controls
- [x] Green runs produce machine-checkable evidence (this receipt + test output)
- [~] `inspect` tier-map obligations — scheduled into the Phase 1 surface (no `inspect` yet)
- [x] GEN3-THESIS-001 registered (`claim-0000`, durable)

**Phase 0 gate: GREEN.** The remaining checklist item is Phase 1 build work.

## 6. Next (Phase 1, in build order)

Minimal field `e=(w,s,c,t)` → four operations (`remember · recall · think · inspect`) with
selection contracts → lifecycle (`transient → candidate → persistent → cold`) → harness
(with the violation log) → **pre-registration freeze** (hash + receipt) → Phase 2 A/B.

This receipt is append-only; corrections create a new receipt referencing it.
