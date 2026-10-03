# RECEIPT — wmv9 claims-ledger loss + reconstruction (2026-09-17)

**Status: recorded.** Session `0f72a7a6-bec9-4d36-b516-501b655f05e2` (opencode, WMgen3 Phase-3
entry track). Operator disposals approved in-session: reconstruct the full chronological claim
sequence + land this incident receipt.

---

## 1. What happened (timeline, from journal + file evidence)

| When (ET) | Event | Ledger consequence |
|---|---|---|
| 2026-09-16 15:35:45 | `wm-serve@wmv9` graceful stop/start; ledger flushed | On disk: `claim-0000` (pending), `next_id: 1` — the last durable state |
| 2026-09-16 17:17–19:09 | P2B→`claim-0001`, P2C→`claim-0002`, P2D arbitration→`claim-0003`, P2E→`claim-0004` registered in the running instance | In-memory only |
| 2026-09-16 20:09:22 | Service instance replaced **without a stop record** (journal shows `Started` with no `Stopping`) | The P2 registrations were lost; file untouched since 15:35 |
| 2026-09-16 20:40–2026-09-17 00:39 | Testbed II + GATED-S-001/002/003 sessions; the three gated claims registered fresh (ids re-used as in-memory `0001/0002/0003`) and resolved | In-memory only |
| 2026-09-17 09:28:09 | User-systemd-manager restart; instance killed ungracefully before any flush (journal shows `Started`/`Stopping`/`Stopped` within the same second) | Remaining in-memory claims lost; disk = `claim-0000` pending, `next_id: 1` |

**Mechanism:** the JSON-side stores (`claims_ledger.json`, `self_model.json`,
`calibration_store.json`, …) persist **on graceful shutdown only** — the mechanism the
`PHASE0_CLOSE_ADDENDUM_2026-09-16.md` demonstrated for durability. An ungraceful kill loses
everything written since the last flush.

**Discovery:** 2026-09-17 ~09:40, at the Phase-3 entry session open (`claims.list` returned one
pending claim; the file check confirmed `next_id: 1` while receipts and reports recorded
resolved claims).

## 2. Disposition (operator-approved)

**Full chronological reconstruction** — the no-loss counterfactual mapping, which is also the
mapping most contemporaneous documents use:

| id | Claim | Registered | Outcome | Resolution event date | Source |
|---|---|---|---|---|---|
| `claim-0000` | GEN3-THESIS-001 (Phase 2) | 2026-09-16 (durable) | **falsified** | 2026-09-16 | `receipts/PHASE2_AB_RESULTS_2026-09-16.md` |
| `claim-0001` | GEN3-P2B-PROJECTION-001 | 2026-09-16 17:17 | **falsified** | 2026-09-16 | `PRE_REGISTRATION.md` §1; `receipts/PHASE2B_RESULTS…` |
| `claim-0002` | GEN3-P2C-INTERACTION-001 | 2026-09-16 17:59 | **falsified** | 2026-09-16 | `PRE_REGISTRATION_P2C.md` §1; `receipts/PHASE2C_RESULTS…` |
| `claim-0003` | GEN3-P2D-ARBITRATION-001 | 2026-09-16 18:32 | **pending (WEAK — deliberately unresolved)** | — | `PRE_REGISTRATION_P2D.md` §1; `receipts/PHASE2D_RESULTS…` |
| `claim-0004` | GEN3-P2E-DISPERSION-001 | 2026-09-16 19:01 | **falsified** | 2026-09-16 | `PRE_REGISTRATION_P2E.md` §1; `receipts/PHASE2E_RESULTS…` |
| `claim-0005` | GEN3-GATED-S-001 | 2026-09-16 22:41 | **falsified (gate-scoped)** | 2026-09-16 | `testbed_ii/a/PRE_REGISTRATION_GATED_S.md` §0; `REPORT_GATED.md` |
| `claim-0006` | GEN3-GATED-S-002 | 2026-09-16 23:57 | **falsified (gate-scoped)** | 2026-09-17 | `gated2/PRE_REGISTRATION_GATED_S_002.md` §0; `REPORT_GATED2.md` |
| `claim-0007` | GEN3-GATED-S-003 (count criterion) | 2026-09-17 00:20 | **validated (gate-scoped)** | 2026-09-17 | `gated3/PRE_REGISTRATION_GATED_S_003.md` §0; `REPORT_GATED3.md` |

Rules applied:

1. Statements, predicted outcomes, and falsification criteria are transcribed from the
   pre-registrations; no wording was strengthened or weakened.
2. Confidences were not recoverable for the reconstructed entries; the tool default (0.5) is
   recorded and is **not authoritative** (claim-0000's original 0.55 is preserved).
3. Every reconstructed entry carries an in-line reconstruction note (statement or resolution
   event) citing this receipt.
4. The arbitration claim was registered pre-loss (P2D freeze receipt; commit `910e68d`) and is
   reconstructed as `claim-0003` pending. Result: the earlier post-loss conclusion that it
   "was never tool-registered" is **corrected as a loss artifact**.
5. Nothing was resolved by reconstruction that the receipts did not already resolve; no WEAK
   was narrated upward.

## 3. Verification

- Post-reconstruction ledger written by graceful restart at **2026-09-17 09:45:57**; file:
  `/home/lucas/Desktop/WHITEMAGIC/data/WMdata/projects/wmv9/claims_ledger.json`,
  sha256 `d94c0cb3d9ebb61ba25a96736931b594844a6a1959c315d0ff388aa380c0e4ed`
  (`next_id: 8`, 8 claims); confirmed again through the live `claims.list` route after reload.
- The flush-then-verify procedure (write → graceful restart → inspect disk → query live) is the
  one demonstrated in `PHASE0_CLOSE_ADDENDUM_2026-09-16.md`; it passed.

## 4. Errata landed with this receipt

- `docs/ARCHITECTURE_CONSOLIDATION.md`: id-mapping note corrected; "claim-0007 validated"
  replaces the post-loss references; §6 claims-ledger line corrected.
- `HANDOFF.md`: 2026-09-17 update block records the incident + mapping; current-state line
  updated.
- Historical session blocks in `HANDOFF.md` (gated closes) are preserved unedited as the record
  of what the session believed at the time; their id references are superseded by this mapping.

## 5. Standing risk + ops note

- Until the persistence behavior changes, **any** wmv9 JSON-side write lives in memory until a
  graceful shutdown. WMv9 ops backlog (not a WMgen3 change): either eager-write the ledger on
  mutation or add a SIGTERM flush path; the deliberate graceful restart is the interim
  procedure.
- This incident is exactly the class Gen3's constitutional invariant 4 (recoverability:
  snapshot before mutation; backups verified) exists to prevent in the successor — recorded
  here as lineage evidence, not as new design.

## 6. Attestation

AI session `0f72a7a6` prepared and verified this receipt; operator approved the disposition.
This receipt is append-only; corrections create a new receipt referencing it.
