# RECEIPT — Wave-1 spec B2 freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the spec is in effect as the
frozen behavioral contract for its row. AI session `c7ab9666-b4cc-4e87-a062-299467db4026`
(opencode) prepared, verified, and attests; it does not ratify. Append-only; corrections create a
new receipt referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_B2_sessions_continuity.md` — Wave-1 spec B2, **sessions & continuity** |
| **SHA-256** | `68cce27aaf3ac1edd20bb1a8a095fa4a970f37eaeb171b3da4f4044ab8a5ebfb` |
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

- **The split:** storage/lifecycle = **link** (Gen2 `session.*`; `session.rs` not
  `session_ops.rs` — divergence #2); continuity/digest = **compile** (recall + think over the
  record layer; no module; anti-bloat).
- **Record contract:** typed turns; provenance trust user 1.0 / agent 0.7; sequence counts
  superseded; **time-based resolution** (newest prior session with turns; scoped hint when none;
  never UUID-scan); lossless replay shape (export/import preserve ids/timestamps/tags; superseded
  hidden by default, restored on request); **no payload-less shells** (W0 class); turn-supersession
  precedence rule required vs R (A3 frontier).
- **Checkpoint contract:** adopt **`session.checkpoint_nodiscovery`** (exact supplied fields; no
  discovery/FS read/subprocess; strict-admitted) — ends the WMv9-HEAD capture quirk; git-capturing
  `session.checkpoint` declared and deprecated for this rhythm.
- **Invariants:** single-writer per session; boundedness enforced at the generic path (no
  `update()` bypass); no ambient valence; one declared capture default; secrets excluded.
- **Adversarial cases 1–10** (sequence race, valence, previous-session selection, cap bypass,
  capture hygiene, **phrase routing #2**, write-time indexing, nodiscovery semantics, shells,
  starvation).
- **Owner: Lucas Bailey (operator).**

## 4. Verification

Docs-only; no build/test run required. At compilation: spec sha256 recorded; nucleus and wave-plan
pins re-hashed and matched; citations line-checked against the W1 sessions findings (v26 cites),
the W1 Gen2 source map §4 (`session.rs:277,376-492`; `session_ops.rs:341,886-983`;
`session.rs:78`), and 9.1.7 Tier-1 #2 / 9.1.8 delta §2.1.

## 5. Companion hashes (batch-B unit)

| Artifact | sha256 |
|---|---|
| `docs/specs/W1_B2_sessions_continuity.md` (frozen) | `68cce27aaf3ac1edd20bb1a8a095fa4a970f37eaeb171b3da4f4044ab8a5ebfb` |
| `docs/specs/W1_B1_retrieval_ranking.md` (frozen) | `9b293d0118cc19ca554b528f2e962d9bdd3a2f4732ecc6a1e6cee20961d89280` |
| `docs/specs/W1_B3_coordination.md` (frozen) | `917c4bef94027d9c3967359d3a8ddadd4a27d98c476b7d4d5d74706b0b69a926` |
| `docs/specs/W1_B4_claims_belief_class.md` (frozen) | `a3f9df8fd3046e1e271e6a8d23ce97b62b2b87513bdfbc49fe9acaba0dea8695` |
| `docs/specs/W1_B5_galaxies_compartments.md` (frozen) | `80a99e62d8b4a50a59ba5124c54eb3cb494df5777b343be70227ec749fd248c9` |
| `docs/PHASE4_WAVE_PLAN.md` | `60688d725d38c36f43e734904efae9bc9e160ffa2facffa69b1267c83a5b2fd0` |
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |

## 6. Consequences

- **Spec B2 is frozen.** The WMgen3 session rhythm may switch to `checkpoint_nodiscovery` now
  (client-side call shape); the 9.1.8 server deploy remains a separate ops item. No
  verdict/claim/gate movement; Δ1,345 and other unverified counts are not citable as measured.

## 7. Attestation

AI session `c7ab9666` compiled `docs/specs/W1_B2_sessions_continuity.md`, verified every pin and
citation above, and recorded the operator's authorizing act and owner assignment. Ratification is
an external operator act; this receipt records it — it does not itself ratify.
