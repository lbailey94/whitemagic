# RECEIPT — Docs sweep batch 6 (kernel-contract walk, step 5a) — 2026-09-19

**Status: landed.** Code-walk step 5a read in full: `contract.rs` (291 LOC) + `capability.rs`
(463 LOC) — the PEB-15 kernel contract and the affine-capability machinery. Operator authorization
(in-session): *"continue our walk, and continue updating our docs as we go"* / *"full and thorough
checklist to hand off in the morning."* No verdict, claim, gate, or threshold movement; no code
changed; no registered artifact edited.

---

## 1. Walk results (errata M.1 #59)

- **Evil Gana battery, row by row** (`contract.rs:192-290`): rows numbered Violation 1–7 — **V3 is
  a legal commit**; V1/V5/V7 are non-attempts (reads/field asserts); V2/V4/V6 are genuine runtime
  fail-closed checks. Prereg rows 3 (serde-deserialization) and 4 (background loop) remain
  unimplemented.
- **`AuthoritativeBackgroundLoopForbidden` is never constructed anywhere** — the background-loop
  defense has no enforcement path; `CommitCapability` remains auto-`Send + Sync`.
- **Affine-by-move confirmed:** non-`Clone`/`Copy`, `#[must_use]`, consumed by value;
  `VerifiedWarrant::mint_from_arbitration` is `pub(crate)` with Law 8 enforced (Affirmed ∧ margin
  ≥ 0.85 ∧ risk ≤ 0.10); replay check precedes mutation; failed mutation leaves the nullifier
  unregistered (tested).
- **New production consideration:** `NullifierSet` is **in-memory only** — replay protection does
  not survive restart (queued on the morning checklist, D3).
- Wall-clock `committed_at_ns` in receipts is informational only (no causal authority claim).

## 2. Changes

| Artifact | Change | sha256 (before → after) |
|---|---|---|
| `docs/PHASE4_ERRATA.md` | section M.1 (#59) added | `d4d6deb5…` → `327b3577…` |

Morning checklist regenerated at `/home/lucas/Desktop/WMgen3_MORNING_CHECKLIST_2026-09-20.md`
(snapshot bumped, step 5a marked done, D3 gains the nullifier-persistence item).

## 3. Disclosures / limits

- No code changed; nothing re-run; no store touched; registered artifacts untouched.
- The row-by-row mapping is a firsthand reading of the committed test body; it confirms and
  sharpens errata #52.2 rather than changing it.

## 4. Attestation

AI session `8996b333-5168-4eb2-9b2a-0e1724fbc749` (WMgen3 docs sweep) prepared this receipt;
operator present and authorizing in-session. Append-only; corrections create a new receipt.
