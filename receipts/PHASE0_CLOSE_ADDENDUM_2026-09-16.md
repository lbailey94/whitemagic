# RECEIPT — Phase 0 close addendum (2026-09-16)

**Status: recorded.** References: `PHASE0_RATIFICATION_v0.1.1_2026-09-16.md`,
`PHASE0_VERIFICATION_2026-09-16.md`, `PHASE0_CONTROL_FREEZE_v9.1.7_2026-09-16.md`.

---

## 1. Claim durability verified

`GEN3-THESIS-001` was registered via Gen2 `claims.add` (wmv9 scope) on 2026-09-16 as
`claim-0000`. Because the ledger persists on graceful shutdown, the `wm-serve@wmv9` unit was
restarted deliberately and the on-disk ledger re-inspected:

- `~/Desktop/WHITEmagic/data/WMdata/projects/wmv9/claims_ledger.json` now contains the claim
  (`id: claim-0000`, `status: pending`, `confidence: 0.55`, `next_id: 1`).
- **Registration is durable across restart.** The A/B experiment's claims baseline is intact.

## 2. Parallel-session work acknowledged (additive)

A separate session produced, while the ratification ceremony was in flight (15:17–15:20):

| Artifact | Role |
|---|---|
| `docs/CODE_ARCHAEOLOGY.md` | Verified Gen1↔Gen2 code survey + discrepancy ledger (Phase 3 seed) |
| `docs/DESIGN_CANON.md` | Working design record (not binding; Charter binds), status-tagged IMPL/PARTIAL/DESIGN/DEFERRED/CAND-LAW |
| `receipts/PHASE0_VERIFICATION_2026-09-16.md` | Independent re-verification of the control, corpus, and the six frozen document hashes |
| README pointer edits | Additive |

**Independent verification result: no drift.** Control binary hash, tag commit, corpus
hashes, and all six document hashes matched (`PHASE0_VERIFICATION` §1–2). No conflicts with
the ratified set; per project culture, the doc carries the claim, not the persona.

## 3. Errata disposition (from `PHASE0_VERIFICATION` §3)

| Errata | Disposition |
|---|---|
| #1 Relative path in pre-registration §1 (`../docs/` → `../../docs/`) | **Applied** to the draft under the documented revision window |
| #2 T6 labeling (T6 = Memory Budget; T1-derived questions) | **Applied** (pre-reg §3; no metric or count change) |
| #3 Staging semantics for the pre-reg draft hash | **Adopted**: the hash in the ratification receipt §2 is the *draft-at-receipt* hash; the corrected draft hash is below; final freeze remains at the Phase 1 gate |
| #4 `iceoryx2` note for the dependency manifest | **Deferred** to the manifest's next revision window (open note; Gen1 precedent recorded in `CODE_ARCHAEOLOGY` §1.4) |

**Corrected pre-registration draft hash (new):**
`experiments/contradiction/PRE_REGISTRATION.md` =
`d506219318e3e29d8466070b9addb8ce2538a94e1b75edb71e715793de6345fd`
(supersedes the draft hash in the ratification receipt §2).

Charter re-hash at this receipt: `957320d9d65dea9fbda9355c43bc8238efc10c9721e3a45239cbe7014a37fa5d`
— **unchanged** (matches the ratified hash; the frozen set was not touched).

## 4. Archaeology consequences adopted into Phase 1 planning

1. **Closure tests must be live.** Gen2's canary subsystem is implemented but *not wired*
   (`CODE_ARCHAEOLOGY` §12) — an unwired guard is worth nothing. The Phase 0/1 gate requires a
   *demonstrated refusal*, not a module's existence (`CLOSURE_TESTS.md` canaries).
2. **Counts must be generated, not authored.** Every WMgen3 count cites its generating
   command/file (`wm contract` precedent).
3. **Control citations use release facts** (302 routes / 70 declared / 232 undeclared), not
   WMv9 HEAD (302/85/217 — post-release growth).
4. **Transport re-adoption is a decision, not novelty:** Gen1 compiled `arrow` + `iceoryx2` in
   its Rust bridge; Gen2 dropped iceoryx2. Any Phase-3 adoption gets its own manifest receipt.

## 5. Remaining Phase-0-gate items (scheduled as the first Phase 1 tasks, before adaptive code)

- [ ] Implement both closure static analyses + both runtime canaries (per `CLOSURE_TESTS.md`) and produce green receipts
- [ ] `git init` WMgen3 + first commit (pending operator; recommended before the pre-reg freeze so receipts can cite commits — `PHASE0_VERIFICATION` §4)
- [ ] Phase 1 scaffold per `SCAFFOLD_STRATEGY.md` §9 build order

## 6. Status

**Phase 0 CLOSED.** This receipt is append-only; corrections create a new receipt
referencing this one.
