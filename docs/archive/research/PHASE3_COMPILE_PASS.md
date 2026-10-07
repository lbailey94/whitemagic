# Phase 3 — Compile-pass method (pre-decision)

**Status:** methodology draft · 2026-09-17 · **for operator review.** Docs-only: assigns **no
verdicts**, changes no gate, authorizes no code. The table lives in `PHASE3_DECOMPOSITION.md`;
this file records *how* the pass will be run when its entry gate opens, and how the theory map
(`THEORY_MECHANISM_MAP.md`) constrains it.

Phase-3 entry rule stands (unchanged): no verdict may be assigned before the Phase-3 gate —
currently closed (`HANDOFF.md`; upstream experiments and their dispositions are the gate's
preconditions, not this file's).

---

## 1. The compile-pass frame

The design sessions converged on a compiler metaphor (CONV L2323–2366, L2515–2550), and it is
the right operational frame for Phase 3:

```
Gen1 survivors + Gen2 route families        ← source
        ↓  compile expression attempt
minimal substrate (records · relations · selection · lifecycle · statutes · journal)
        ↓  compiler diagnostics
COMPOSES CLEANLY · COMPOSES AWKWARDLY · IRREDUCIBLE · PRESERVE IMPLEMENTATION ·
RETIRE · EXPERIMENT                          (CONV L4174–4182)
```

Readings that matter:

- **PRESERVE IMPLEMENTATION = link, not rewrite.** The existing implementation is called behind
  the surface (Gen1's retention sweep, Gen2's revision verify, the firebreak seam, the karma
  chain). "Over time it can be replaced only if the general substrate earns that replacement"
  (CONV L4196–4206).
- **IRREDUCIBLE requires a demonstrated failed compile** — the missing primitive must be shown to
  be general, not convenient (CONV L4154–4158; Phase-2's own rule).
- **RETIRE requires a lineage citation**, never a taste judgment (`LINEAGE_LEDGER.md` is the
  precedent: economy family obsolete-by-design with a revisit condition).
- **EXPERIMENT = a never-fairly-tried ancestor** entering only with the manifest rule:
  ancestor · wire · acceptance · owner, plus a receipt (`PHASE3_DECOMPOSITION.md` §4).

## 2. Preconditions (when the pass may run)

1. **Gate open** — the Phase-3 entry rule satisfied and operator-approved
   (`PHASE3_ENTRY_DECISION.md`, ratified 2026-09-17: the literal "Phase 2 passes" gate was not
   satisfied and is superseded by completion of the Phase-2 program); this is a decision, not a
   default.
2. **Upstream dispositions recorded** — as of 2026-09-17: Phase 2 closed LOSS; P2B/P2C/P2E
   falsified; P2D WEAK (claim-0003 pending); gated-S-001 and -002 both closed **falsified**
   (cost; discrimination) with the conditional-lens result kept; TIE parked; projection-agreement
   dormant. Nothing here reopens them; they enter as priors.
3. **Pinned sources regenerated at run time** (counts are generated, never authored):
   `wm contract --json` from the pinned control binary; `LINEAGE_LEDGER.md`; `CODE_ARCHAEOLOGY.md`;
   the Gen1↔Gen2 matrix; this repo's experiment reports.
4. **Statutes visible**: selection weights, lifecycles, budgets that verdicts may lean on are
   statutes (Charter §2), so the pass must cite them, not invent them.

## 3. Procedure (per family — the loop)

1. **Read the row** from `PHASE3_DECOMPOSITION.md` §2 (family · Gen2 surface · Gen1 ancestry ·
   expression hypothesis · A/B stance).
2. **Write the compile expression**: the smallest configuration of substrate primitives
   (record types, relation kinds, selection contract, lifecycle, statute, journal events) that
   would produce the family's *observable behavior*.
3. **Diagnose**: does it express cleanly (→ CLEANLY), only with contortions (→ AWKWARDLY; name
   the missing primitive as a *candidate*, not a feature), or not at all with the current basis
   (→ IRREDUCIBLE *only if* the failure is general)?
4. **Assign the verdict** — gate open only — with an evidence pointer: experiment, lineage
   ruling, or the compile expression itself for CLEANLY rows.
5. **Destination**: `compile` (substrate), `link` (preserved implementation), `retire` (docs +
   lineage), `experiment` (manifest + receipt), `render-only` (never dispatches).
6. **Audit the anti-bloat law**: no new Garden/Engine implementation unless the behavior cannot
   be expressed as a profile, operator, or composition (canon §7, CAND-LAW). The pass is where
   that law is enforced or amended.

## 4. Illustrations (echoes of the existing table's hypotheses — **not verdicts**)

| Family (as listed in `PHASE3_DECOMPOSITION.md`) | Compile reading (illustrative) | Why it illustrates |
|---|---|---|
| Retention/lifecycle (Gen1 5-signal) | likely **link/preserve** | The most coherent Gen1 code; fixed persistent tier in Phase 1; no need to re-derive |
| Revisions/supersession verify | likely **link/preserve** | Infrastructure; already the substrate's strongest earned relation |
| Firebreak / karma-as-credit | likely **link/preserve** (seam) + statutes | Governance is statute + journal, not cognition |
| Gardens (29 profiles) | **compose as conditions** hypothesis; no new class | Canon §7: gardens say *how to think*; mixtures deferred |
| T8 cross-vocabulary bridge | **do not re-add without a new registration** | Falsified as a primitive; the control's gain was hand-authored enrichment |
| Economy remnant / symbolic families | **retire-bias** | Obsolete-by-design ruling + Charter §3.10 render-only; verify shipped-vs-dormant first |

These illustrate method only. They are deliberately consistent with rows already present in the
decomposition table and add no new claims.

## 5. Output and acceptance

- **Deliverable:** the §2 table filled — verdict + evidence pointer + destination per family —
  becoming the Phase-3 ledger. Counts regenerated from the pinned binary at run time.
- **Acceptance of the pass itself:** every route family has a row; every non-trivial verdict
  cites evidence or a lineage ruling; nothing retires without a citation; every EXPERIMENT row
  carries the manifest rule; the operator ratifies; a receipt lands in `receipts/`.
- **Failure of the pass:** any row that cannot name its evidence is `pending`, not guessed.

## 6. Explicit non-goals

No code, no primitive additions, no verb-basis expansion, no inheritance/Geneseed work, no
re-litigation of falsified claims, no new symbolic runtime branches. The pass produces verdicts
and preserved-implementation links — nothing executes differently because this file exists.
