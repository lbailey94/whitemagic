# RECEIPT — Wave-1 spec B4 freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the spec is in effect as the
frozen behavioral contract for its row. AI session `c7ab9666-b4cc-4e87-a062-299467db4026`
(opencode) prepared, verified, and attests; it does not ratify. Append-only; corrections create a
new receipt referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_B4_claims_belief_class.md` — Wave-1 spec B4, **claims / belief class** |
| **SHA-256** | `a3f9df8fd3046e1e271e6a8d23ce97b62b2b87513bdfbc49fe9acaba0dea8695` |
| Compiled per | `docs/PHASE4_WAVE_PLAN.md` §7 + §9 batch B, under the frozen nucleus `73c5a9cf…` |
| Tip at compilation | `309e111` (tree clean at compile; freeze unit commits with this receipt) |
| Rule | Any edit after ratification is a new version with its own amendment receipt |

## 2. Operator act — RECORDED

Owner assignment and freeze authorization prompted in session, 2026-09-17; operator instruction
recorded verbatim: **"continue with all remaining batches, items, slices, and phases"**
(extending the batch-A standing authorization).

| Field | Value |
|---|---|
| Operator | Lucas Bailey |
| Act | In-session authorization of batch-B freeze + owner assignment + commit |
| Owner assigned | Lucas Bailey (operator) |
| AI attestation | Session `c7ab9666` compiled the spec, line-checked citations, verified pins — attestation only |

## 3. What was ratified

- **Belief-class records:** required fields (statement · domain · source_date · predicted_outcome ·
  confidence ∈ [0,1] fail-closed · falsification_criteria); absent fields refuse, never default.
- **Resolution events:** `validated + event + event_date`; **resolution-record completeness** —
  every resolved claim has its event + date + provenance; followed-guidance separable from outcome
  (no `action_taken` encoding); resolutions write-through durable.
- **Calibration = statutory statistic over one universe** (the claims-ledger resolved set):
  Brier, signed gap, Wilson 95, empirical-Bayes `w = n/(n+20)`; raw confidences never edited;
  expired handling pinned once; no post-hoc (`behavioral_confidence`) inputs.
- **Hygiene:** no destructive seed sync (independent rows never deleted); declared battery only;
  free-text `validation_ref` / NRS name-regex class excluded; points totals re-derivable
  (`floor(lead_weeks)`-style) or not reported; reads read-only.
- **Adversarial cases 1–9** (destructive sync, degenerate calibration, free-text validation,
  points, oracle confound, confidence bounds, durability kill -9, read-only, universe naming).
- **Ablation:** resolution events (completeness computable→not); expired-inclusion gap shift;
  destructive-sync fixture (deletion count 0); post-hoc null-input negative control.
- **Owner: Lucas Bailey (operator).**

## 4. Verification

Docs-only; no build/test run required. At compilation: spec sha256 recorded; nucleus and wave-plan
pins re-hashed and matched; citations line-checked against W1 claims findings (forecasting package
cites), W1 Gen2 source map §6 (`claims_tools.rs:34-100,289-315`; `claims.rs:91,157,190,230,305,
316,379`; `server.rs:1421,2563`), errata #25/G-25, and the WMv9 write-through commit `16198ea`.

## 5. Companion hashes (batch-B unit)

| Artifact | sha256 |
|---|---|
| `docs/specs/W1_B4_claims_belief_class.md` (frozen) | `a3f9df8fd3046e1e271e6a8d23ce97b62b2b87513bdfbc49fe9acaba0dea8695` |
| `docs/specs/W1_B1_retrieval_ranking.md` (frozen) | `9b293d0118cc19ca554b528f2e962d9bdd3a2f4732ecc6a1e6cee20961d89280` |
| `docs/specs/W1_B2_sessions_continuity.md` (frozen) | `68cce27aaf3ac1edd20bb1a8a095fa4a970f37eaeb171b3da4f4044ab8a5ebfb` |
| `docs/specs/W1_B3_coordination.md` (frozen) | `917c4bef94027d9c3967359d3a8ddadd4a27d98c476b7d4d5d74706b0b69a926` |
| `docs/specs/W1_B5_galaxies_compartments.md` (frozen) | `80a99e62d8b4a50a59ba5124c54eb3cb494df5777b343be70227ec749fd248c9` |
| `docs/PHASE4_WAVE_PLAN.md` | `60688d725d38c36f43e734904efae9bc9e160ffa2facffa69b1267c83a5b2fd0` |
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |

## 6. Consequences

- **Spec B4 is frozen.** Claim-0003 stays WEAK; the four calibration universes stay separated
  (0.078 = Gen2 live-store ledger, never the v26 runtime 0.2563/0.0731 or citta CRPS). No
  verdict/claim/gate movement; ledger stays at 8 claims.

## 7. Attestation

AI session `c7ab9666` compiled `docs/specs/W1_B4_claims_belief_class.md`, verified every pin and
citation above, and recorded the operator's authorizing act and owner assignment. Ratification is
an external operator act; this receipt records it — it does not itself ratify.
