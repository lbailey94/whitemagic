# RECEIPT — Docs sweep batch 2 (constitutional/design core walk) — 2026-09-19

**Status: landed.** Docs-only sweep over `CHARTER.md`, `NUCLEUS.md`, `DESIGN_CANON.md`,
`THEORY_MECHANISM_MAP.md`, `ARCHITECTURE_CONSOLIDATION.md` (plus one live `HANDOFF.md` cross-fix).
Operator authorization (in-session): *"Docs fixes + errata log"*, *"Commit + receipt per update"*,
*"let's continue on with batches 2 and 3."* No verdict, claim, gate, or threshold movement; no
hash-pinned artifact edited.

---

## 1. Changes

| Artifact | Change | sha256 (before → after) |
|---|---|---|
| `HANDOFF.md` | §4 rule 8: "Phase 3 blocked" → closed-state note (R1 remains paused/rejected) | `733a0fcc…` → `936c8888…` |
| `docs/THEORY_MECHANISM_MAP.md` | Brier conflation fixed (#25); GATED-S-003 count criterion + ≥2 boundary in the lens rows; bet 3; entry-gate line; sources add gated3; status annotated | `28dc35a5…` → `04946375…` |
| `docs/ARCHITECTURE_CONSOLIDATION.md` | §6 "Phase 3 stays blocked" → closed-state note; §1 R1 cross-ref "open thread 8" → "HANDOFF §4 rule 8" | `9934a088…` → `87dc01ec…` |
| `docs/DESIGN_CANON.md` | header annotation (design-time tags); §3.6 galaxy-container precision; §4 the declared 300 s decay never ticks (#14) + dormancy caveats | `d563fd44…` → `9464dfa9…` |
| `docs/PHASE4_ERRATA.md` | batch J (#43–47) added; title (batches A–J) | `4cf835cf…` → `a648d1f3…` |

## 2. Review performed (read in full)

- `docs/CHARTER.md` (v0.1.1) and `docs/NUCLEUS.md` — both hash-pinned; on-disk hashes re-verified
  against their pins (`957320d9…`, `73c5a9cf…`): match. **No edits** (pins would break).
- `docs/DESIGN_CANON.md`, `docs/THEORY_MECHANISM_MAP.md`, `docs/ARCHITECTURE_CONSOLIDATION.md` —
  full read against the current record (`NUCLEUS.md`, `PHASE3_*`, gated reports, wave findings,
  `PHASE4_ERRATA.md`).
- `ARCHITECTURE_CONSOLIDATION.md` matched its `PHASE3_ENTRY_DECISION` pin (`9934a088…`) before
  this sweep; its post-sweep drift is this item's corrections only (errata #46).

## 3. Disclosures / limits

- `CHARTER.md` and `NUCLEUS.md` were **not edited** (hash-pinned). Their surface-age items
  ("Draft … FOR RATIFICATION" header with unsigned signature line; NUCLEUS §9 steps 4–5 unchecked
  though ratified) are documented in errata #43 — receipts are canonical.
- Contemporaneous "Phase 3 blocked" statements inside `HANDOFF.md`'s retained historical openers
  are preserved unedited as the record (errata #46).
- The 300 s-decay and galaxy-container corrections in `DESIGN_CANON.md` restate already-landed
  errata (#14; `findings/W1_galaxies_compartments.md`) — no new findings.
- The Brier-identity correction in `THEORY_MECHANISM_MAP.md` restates errata #25, which had not
  yet reached the map.
- No frozen file touched; no thresholds/weights changed; nothing re-run.

## 4. Attestation

AI session (WMgen3 docs sweep, 2026-09-19) prepared this receipt; operator present and authorizing
in-session. This receipt is append-only; corrections create a new receipt referencing it.
