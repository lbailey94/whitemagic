# RECEIPT — Wave-1 spec B1 freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the spec is in effect as the
frozen behavioral contract for its row. AI session `c7ab9666-b4cc-4e87-a062-299467db4026`
(opencode) prepared, verified, and attests; it does not ratify. Append-only; corrections create a
new receipt referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_B1_retrieval_ranking.md` — Wave-1 spec B1, **retrieval & ranking** |
| **SHA-256** | `9b293d0118cc19ca554b528f2e962d9bdd3a2f4732ecc6a1e6cee20961d89280` |
| Compiled per | `docs/PHASE4_WAVE_PLAN.md` §7 + §9 batch B, under the frozen nucleus `73c5a9cf…` |
| Tip at compilation | `309e111` (tree clean at compile; freeze unit commits with this receipt) |
| Rule | Any edit after ratification is a new version with its own amendment receipt |

## 2. Operator act — RECORDED

Owner assignment and freeze authorization prompted in session, 2026-09-17; operator instruction
recorded verbatim: **"continue with all remaining batches, items, slices, and phases"**
(extending the batch-A standing authorization "we can take care of everything now in this
session; no other work is being done on gen3 currently").

| Field | Value |
|---|---|
| Operator | Lucas Bailey |
| Act | In-session authorization of batch-B freeze + owner assignment + commit |
| Owner assigned | Lucas Bailey (operator) |
| AI attestation | Session `c7ab9666` compiled the spec, line-checked citations, verified pins — attestation only |

## 3. What was ratified

- **Scoring contract (D2 Option B):** idf-weighted query support; `support = max(lex, sem)`;
  no per-query/corpus normalization; floors fail-closed (A2 cross-ref); limit/candidate-limit
  semantics; journal rank fields (`selection.decision`, `provenance.chain`).
- **Earned subset only:** R + strata + D2 + the C1 slot; **no planner imports** (RRF k=60,
  multiplicative rerank, cross-encoder, conversation bonuses, tag-Jaccard, qFHRR all excluded;
  absence is the frozen behavior) — lexically–semantically measured design, no re-tuning.
- **Ordering keys:** `key = support × (1 + 0.05·recency)`, superseded ×(1 − 0.60) unless
  historical; `PenaltyMultiplier` default (key desc, id desc); `Structural` = stratum asc, then
  lexical desc → semantic desc → recency desc → id desc.
- **Read discipline:** recall read-only over durable state; in-process usage counters are not
  durable evidence.
- **Adversarial cases 1–8** (optional-stage reordering, no implicit filtering, no warm-up
  nondeterminism, no score nudges, floor bounds, drift honesty, read-only, starvation).
- **Ablation:** sweep (C2) / projection (C3) / planner negative control (0-diff or registration).
- **Owner: Lucas Bailey (operator).**

## 4. Verification

Docs-only; no build/test run required. At compilation: spec sha256 recorded; `NUCLEUS.md`
`73c5a9cf…` and `PHASE4_WAVE_PLAN.md` `60688d72…` re-hashed and matched; citations line-checked
against `crates/wm-gen3-core/src/ops.rs` (467-479, 555-581, 600-652, 638-648, 619-624, 661-676,
454, 664) and the frozen corpus/ablation records (C2/C3, gated3).

## 5. Companion hashes (batch-B unit)

| Artifact | sha256 |
|---|---|
| `docs/specs/W1_B1_retrieval_ranking.md` (frozen) | `9b293d0118cc19ca554b528f2e962d9bdd3a2f4732ecc6a1e6cee20961d89280` |
| `docs/specs/W1_B2_sessions_continuity.md` (frozen) | `68cce27aaf3ac1edd20bb1a8a095fa4a970f37eaeb171b3da4f4044ab8a5ebfb` |
| `docs/specs/W1_B3_coordination.md` (frozen) | `917c4bef94027d9c3967359d3a8ddadd4a27d98c476b7d4d5d74706b0b69a926` |
| `docs/specs/W1_B4_claims_belief_class.md` (frozen) | `a3f9df8fd3046e1e271e6a8d23ce97b62b2b87513bdfbc49fe9acaba0dea8695` |
| `docs/specs/W1_B5_galaxies_compartments.md` (frozen) | `80a99e62d8b4a50a59ba5124c54eb3cb494df5777b343be70227ec749fd248c9` |
| `docs/PHASE4_WAVE_PLAN.md` | `60688d725d38c36f43e734904efae9bc9e160ffa2facffa69b1267c83a5b2fd0` |
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |

## 6. Consequences

- **Spec B1 is frozen**; implementation/demonstration obligations run under the row's gate;
  adversarial cases must be wired before row exit; no verdict/claim/gate movement; WEAK stays
  WEAK; ledger 8 claims.
- Any planner/organ import is a new registration with a fresh holdout — the frozen-corpus 0-diff
  check is the enforcement.

## 7. Attestation

AI session `c7ab9666` compiled `docs/specs/W1_B1_retrieval_ranking.md`, verified every pin and
citation above, and recorded the operator's authorizing act and owner assignment. Ratification is
an external operator act; this receipt records it — it does not itself ratify.
