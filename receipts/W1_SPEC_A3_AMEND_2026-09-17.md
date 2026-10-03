# RECEIPT — Wave-1 spec A3 amendment rev 2 ratified (2026-09-17)

**Status: FROZEN rev 2 — 2026-09-17.** Operator ratified in session; rev 2 is in effect as the
frozen behavioral contract for its row, additive to rev 1. AI session
`68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) prepared, verified, and attests; it does not
ratify. Append-only; corrections create a new receipt referencing this one.

---

## 1. Amended artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_A3_revisions_supersession.md` — Wave-1 spec A3, **revisions/supersession** |
| **rev 2 SHA-256** | `bf4d3b53b17b34b486e052a225984e2ee020a22a800a7f95116e1f0cbc97d4e1` |
| Supersedes | rev 1, sha256 `3adedac0bd421c945854026ca50f17b1088c1489e3b73a965093ed007954fc69` (receipt `receipts/W1_SPEC_A3_FREEZE_2026-09-17.md`) |
| Rule | Any further edit is a new version with its own amendment receipt |

## 2. Operator act — RECORDED

Trigger: the A3 acceptance driver measured spec case 1 against frozen rule v1 — the lexical rule
**links** the predicate-sense pair (`"prefers Rust"` / `"wrote Rust"` → 1 proposal), conflicting
with the case's "R must not link them". Operator selection recorded verbatim:
**"Spec amendment + gated rule-v2 note (Recommended)"**. Operator: **Lucas Bailey**. Act: explicit
in-session disposition + ratification of the amendment approach + commit authorization.

## 3. What changed in rev 2

- **§1.1:** `value-diff` noted as implemented by *distinctive-rare-token presence* — a lexical
  reading (measured).
- **§3 case 1:** reworded from a prohibition to a **declared, measured property**: rule v1 is
  lexical; the collision class is disclosed, not excluded (edge applies penalty + `superseded_by`;
  both records still returned; audit flags visible). A stricter **rule v2
  (value-replacement requirement)** is registered as a **gated candidate** in
  `PHASE4_ERRATA.md`; no execution authorized.
- **§5/§5.1:** owner recorded; revision history added; header updated.

## 4. Verification

Docs-only artifact; no code, gates, thresholds, or verdicts changed. At ratification:

- rev 1 hash verified **before** editing: `3adedac0…` matched the freeze receipt.
- rev 2 hash recorded above; `docs/NUCLEUS.md` remains `73c5a9cf…` (unchanged; not re-hashed here —
  docs-only edit, no nucleus dependency).
- Acceptance evidence for the amended case: `IMPL_A3_ACCEPTANCE_2026-09-17` (driver output
  `a3.results.txt`, finding evidence `a3_c.journal.jsonl`).

## 5. Consequences

- **A3 rev 2 is frozen.** The row's acceptance items are demonstrated except the (now declared)
  lexical-collision property; A3 may exit with the operator's packet signature.
- Rule v2 stays a **gated candidate**: re-entry requires its own registration + a full corpus
  re-baseline (P2B–P2E, gated3, TBII); the cross-ecology R result must not be risked silently.
- No verdict, claim, gate, or threshold changes; WEAK stays WEAK.

## 6. Attestation

AI session `68c17d3b` measured the conflict, drafted rev 2, ran the operator disposition, and
recorded the ratifying act. Ratification is an external operator act; this receipt records it — it
does not itself ratify.
