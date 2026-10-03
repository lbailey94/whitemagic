# RECEIPT — Phase 0 Charter Ratification (v0.1.1)

**Status: RATIFIED — 2026-09-16. PHASE 0 CLOSED.**
Operator ratification recorded in §6; GEN3-THESIS-001 registered in the Gen2 Claims Ledger
(§5). Prepared and finalized 2026-09-16.

---

## 1. Reviewed artifact

| Field | Value |
|---|---|
| File | `docs/CHARTER.md` |
| Version | **v0.1.1** — six precision edits applied from the 2026-09-16 review: fail-closed budget wording; authorized-erasure carveout; Closure 1 read-interface correction; non-promotable domains + new-record intake; disclosure wording; AI attestation replaces witness signature |
| **SHA-256** | `957320d9d65dea9fbda9355c43bc8238efc10c9721e3a45239cbe7014a37fa5d` |
| Rule | Any edit after ratification is a new version with its own amendment receipt; the ten-invariant set is frozen (next change must come from an experiment breaking them) |

## 2. Phase 0 document freeze (hashes at this receipt)

| Document | SHA-256 |
|---|---|
| `docs/CHARTER.md` (v0.1.1) | `957320d9d65dea9fbda9355c43bc8238efc10c9721e3a45239cbe7014a37fa5d` |
| `docs/CLOSURE_TESTS.md` (v1.0) | `ad6e3152259b07b3b6f42989e975f84776c1d9bb14d114b3aeba308ee6ca775d` |
| `docs/SCAFFOLD_STRATEGY.md` | `433dfebd88f607b4bd4a1910021bba40cb241dbb7431a2506d217f07c252ac3e` |
| `docs/DEPENDENCY_MANIFEST.md` | `f3be84490160c74ac8cca379def7c5a0ba9f8d52b6543d797f55e9c6aee1b0eb` |
| `experiments/contradiction/PRE_REGISTRATION.md` | `d5efd6fe71f38af60f3254a0158ba97c5a081a1b15eca23fca5627b62b785915` |
| `receipts/PHASE0_CONTROL_FREEZE_v9.1.7_2026-09-16.md` | `c9dcfe3b86286f86963ec99a5d4aaff7af9193f464ce4066ac50b845e068d681` |

## 3. AI review attestation (attests — does not ratify)

| Field | Value |
|---|---|
| Reviewer | opencode strategic-review session, 2026-09-16 |
| Reviewed | `CHARTER.md` v0.1.1 at the hash in §1 |
| Findings | Six edits applied as reviewed; ten-invariant set assessed coherent enough to freeze; no further invariants recommended — the next discovery should come from breaking these, not writing more |
| Store attestation | wmv9 / codex memory id `3532cc28-b94b-402e-8470-d820cbe27780` |

## 4. Closure tests encoded

`docs/CLOSURE_TESTS.md` (hash in §2): static analyses A–D for both closures, runtime canaries
with positive and negative controls, violation-event schema, `inspect` tier-map obligations,
and the Phase 0 gate checklist.

## 5. GEN3-THESIS-001 — REGISTERED

| Field | Value |
|---|---|
| statement | A minimal Gen3 substrate — four general operations, three epistemic classes, a minimal field `e=(w,s,c,t)`, per-operation selection, no dedicated contradiction engine, no Gen2 behavioral imports — will match or exceed frozen Gen2 v9.1.7 contradiction handling on MemoraStrict T8 under equal budget, with zero epistemic laundering and zero constitutional violations |
| domain | architecture |
| source_date | 2026-09-16 |
| predicted_outcome | Match or exceed control on T8 (15 q pooled); resolution (T1+T6) non-inferior; zero violations; within +2 session budget |
| confidence | 0.55 |
| falsification_criteria | T8 pooled shortfall ≥ 2 questions; OR any epistemic laundering event; OR any constitutional violation; OR budget overrun beyond +2 sessions; OR inconclusive 30 days after the Phase 1 gate |
| **Registered** | **2026-09-16 · `claim_id: claim-0000` · status `pending`** · ledger: wmv9 store (first claim in this store's ledger) · deadline: 30 days after the Phase 1 gate |

## 6. Operator ratification — RECORDED

> I ratify **Charter v0.1.1** at SHA-256
> `957320d9d65dea9fbda9355c43bc8238efc10c9721e3a45239cbe7014a37fa5d`.

| Field | Value |
|---|---|
| Operator act | Explicit operator statement received 2026-09-16: *"I ratify it; sign it LUCAS."* |
| Operator | Lucas Bailey |
| Signature | **LUCAS** |
| Date | 2026-09-16 |
| Counter-signature | opencode strategic-review session, 2026-09-16 (recorded the act; attests, does not ratify) |

**Phase 0 closed at this receipt.** Next: the deep Gen1+Gen2 study session (capability
decomposition table + Phase 1 reimplementation notes — copy nothing behavioral), then the
Phase 1 scaffold per the build order in `docs/SCAFFOLD_STRATEGY.md`.
