# RECEIPT — Wave-1 spec A3 freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the spec is in effect as the
frozen behavioral contract for its row. AI session `c7ab9666-b4cc-4e87-a062-299467db4026`
(opencode) prepared, verified, and attests; it does not ratify. Append-only; corrections create a
new receipt referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_A3_revisions_supersession.md` — Wave-1 spec A3, **revisions/supersession** |
| **SHA-256** | `3adedac0bd421c945854026ca50f17b1088c1489e3b73a965093ed007954fc69` |
| Compiled per | `docs/PHASE4_WAVE_PLAN.md` §7 (cross-cutting spec template) + §9 batch A, under the frozen nucleus `docs/NUCLEUS.md` (`73c5a9cf…`) |
| Tip at compilation | `b7565ee` (tree clean at compile; freeze unit commits with this receipt) |
| Rule | Any edit after ratification is a new version with its own amendment receipt (wave plan §9; additive errata only) |

## 2. Operator act — RECORDED

Freeze path and owner assignment prompted in session, 2026-09-17; operator selections recorded
verbatim: **"Assign owners + ratify (Recommended)"** and **"I think we can take care of
everything now in this session; no other work is being done on gen3 currently."**

| Field | Value |
|---|---|
| Operator | Lucas Bailey |
| Act | Explicit in-session ratification + owner assignment + commit authorization |
| Owner assigned | Lucas Bailey (operator) — recorded in §3; no other gen3 work in flight at assignment |
| AI attestation | Session `c7ab9666` compiled the spec, line-checked every source citation, verified pins, and prepared this receipt — attestation only |

## 3. What was ratified

- **Frozen behavioral spec** — the `supersedes` relation contract (R; candidacy rule v1
  `shared-rare+value-diff+temporal`; statutory parameters divisor 20 / floor 2 / pair budget
  200k / supersede penalty 0.60 / recency 0.05); ordering contract (structural strata 0/1/2 =
  current/unresolved/superseded; within-stratum lexical → semantic → recency → id; current-value
  questions prefer the newest value-bearing statement; round-trip C5; history persists,
  contradictions never adjudicated); direction contract (directed edges, direction-aware
  proposal scoring H3); **boundary fixed** — Gen2 hash-chain revisions = link/history side, Gen3
  R + strata = compile side, **no Gen2 agreement claimed** (divergence #3); session-turn
  `supersedes` tags belong to the sessions row (batch B) with a precedence rule required before
  any double-apply; journal events `think.sweep`, `relation.proposed`, `selection.decision`
  strata fields, `provenance.chain`; acceptance metrics must dedupe identical endpoints
  (**F4 guard**, nucleus §5).
- **Selection history** — v26 `temporal_kg.py` ("Gap C") with extraction stage + separate fact DB
  + FAMA score nudges (none inherited); Gen2 revision chains/currentness as behavior; Gen3 R as
  derived relation with no extraction and no score nudges; per-statement evidence levels (R
  cross-ecology survivor, TBII 54/60 vs 34/60, P2D cell stays WEAK — S3).
- **Adversarial cases** — findings row-3 battery (predicate-sense collision, temporal absence,
  LABEL/state-conflict with flags visible and no tuning, window queries from the journal,
  F4 carry) + applicable 9.1.7 items (#6 atomic-vs-partial, #5 drift) + 9.1.8 additions
  (read-only discipline for verification, starvation-vs-refusal); non-applicable items declared,
  not padded.
- **Ablation** — `WM_GEN3_SWEEP=0` ordering flip (C2 template; `relation.proposed` >0→0;
  `superseded_by` applied→absent; round-trip C5), structural-vs-`PenaltyMultiplier` strata delta
  (inert = row fails teeth check), direction-flip registration; EXTERNAL not claimed; WEAK stays
  WEAK.
- **Acceptance** — seven wrapper-side assertions (C2 ablation, H3 direction, C5 round-trip, F4
  guard with raw counter disclosed, no score nudges, history-lossless, TBII-template wrapper) with
  counts generated, raw + adjudicated reporting; **no inert acceptance test**.
- **Owner: Lucas Bailey (operator)** — assigned at ratification.

## 4. Verification

Docs-only artifact: no code, gates, thresholds, or verdicts changed; no build/test run required
(nothing executable changed). At compilation:

- Spec sha256 recorded above; `docs/NUCLEUS.md` re-hashed `73c5a9cf…` and
  `docs/PHASE4_WAVE_PLAN.md` re-hashed `60688d72…` — both match the ratified pins.
- Citations line-checked against the frozen source: `crates/wm-gen3-core/src/ops.rs:642-648`
  (structural strata ordering), `:661-676` (applied relations + `superseded_by`), `:751`
  (`existing` snapshotted pre-loop — F4 site); canaries C2/C5.
- Adversarial sources read at their pinned texts: 9.1.7 scope Tier 1; delta §3.2; W1 row 3 +
  divergences #3. No live-data item is cited as measured (errata §E boundary respected).

## 5. Companion hashes (batch-A unit)

| Artifact | sha256 |
|---|---|
| `docs/specs/W1_A3_revisions_supersession.md` (frozen) | `3adedac0bd421c945854026ca50f17b1088c1489e3b73a965093ed007954fc69` |
| `docs/specs/W1_A1_durable_store_ingestion.md` (frozen) | `cf638395661e05b865d421af6392ec93d78902799e18260cb2b7d3ce747234a3` |
| `docs/specs/W1_A2_evidence_disclosure.md` (frozen) | `aa84a5acbec704204bc808c300ebde6d6ff0976b8ffc9b64c2cfaf99a2631fda` |
| `docs/PHASE4_WAVE_PLAN.md` | `60688d725d38c36f43e734904efae9bc9e160ffa2facffa69b1267c83a5b2fd0` |
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |

## 6. Consequences

- **Spec A3 is frozen.** Implementation of any successor hardening still requires its own unit
  under the row's gate with its own demonstration; adversarial cases must be wired as runnable
  acceptance assertions before the row can exit (wave plan §2 exit criteria).
- F4 remains flagged for a future registration (nucleus §5); the F4 guard binds this row's
  metrics now.
- No verdict, claim, gate, or threshold changes; the arbitration claim stays WEAK (S3); ledger
  stays at 8 claims.

## 7. Attestation

AI session `c7ab9666` compiled `docs/specs/W1_A3_revisions_supersession.md`, verified every pin
and citation listed above, and recorded the operator's ratifying act and owner assignment.
Ratification is an external operator act; this receipt records it — it does not itself ratify.
