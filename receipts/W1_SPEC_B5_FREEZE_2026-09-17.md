# RECEIPT — Wave-1 spec B5 freeze ratified (2026-09-17)

**Status: FROZEN — 2026-09-17.** Operator ratified in session; the spec is in effect as the
frozen behavioral contract for its row. AI session `c7ab9666-b4cc-4e87-a062-299467db4026`
(opencode) prepared, verified, and attests; it does not ratify. Append-only; corrections create a
new receipt referencing this one.

---

## 1. Frozen artifact

| Field | Value |
|---|---|
| File | `docs/specs/W1_B5_galaxies_compartments.md` — Wave-1 spec B5, **galaxies / compartments** |
| **SHA-256** | `80a99e62d8b4a50a59ba5124c54eb3cb494df5777b343be70227ec749fd248c9` |
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

- **Scope labels are views over one store** (no per-name resources; the v26 per-DB class
  excluded); bounded label set (16-value enum + dynamic cap 20, min cluster 10, prune 0.1);
  **cap bypass path closed or named** (physical registry UNVERIFIED item); labels carry
  provenance or transfers refuse.
- **Explicit selection stays explicit** — the default path stays filtered; explicit scope args
  cannot become the default.
- **Isolation classes:** cross-class transfer must **refuse or disclose** (v26 asymmetry
  excluded); federation over never-loaded labels must not fabricate results; bounded discovery.
- **Compartments:** access tier on a request, not storage machinery; **unknown values fail
  closed**; **`_meta.compartment` is membership, not authenticated authorization** (disclosure
  retained); **fail-open-on-engine-error named** — fail-closed is the law; tier labels never
  outrun enforcement (effective grants reported).
- **Capability typos refuse loudly** (v26 silent-drop excluded).
- **Adversarial cases 1–9** (unbounded names, isolation asymmetry, explicit creep, capability
  typos, tier degradation, cap bypass, membership-vs-authz, fail-open-on-error, narrative guard).
- **Ablation:** classification off (labels advisory); discovery pre-pass off (isolation holds);
  class-marker A/B (search vs transfer asymmetry isolated); tier-availability forcing (reporting
  honesty).
- **Owner: Lucas Bailey (operator).**

## 4. Verification

Docs-only; no build/test run required. At compilation: spec sha256 recorded; nucleus and wave-plan
pins re-hashed and matched; citations line-checked against W1 galaxies findings (v26 cites), W1
Gen2 source map §7 (`galaxy.rs:11-49,82-96`; `mutable.rs:266-321`; `galaxy_registry.rs:33`;
`mandala.rs:26-101,169-223`; `context.rs:132,167`), W1 divergences #4 (cap bypass; `_meta`
membership), and errata A#6 (sprawl narrative-only).

## 5. Companion hashes (batch-B unit)

| Artifact | sha256 |
|---|---|
| `docs/specs/W1_B5_galaxies_compartments.md` (frozen) | `80a99e62d8b4a50a59ba5124c54eb3cb494df5777b343be70227ec749fd248c9` |
| `docs/specs/W1_B1_retrieval_ranking.md` (frozen) | `9b293d0118cc19ca554b528f2e962d9bdd3a2f4732ecc6a1e6cee20961d89280` |
| `docs/specs/W1_B2_sessions_continuity.md` (frozen) | `68cce27aaf3ac1edd20bb1a8a095fa4a970f37eaeb171b3da4f4044ab8a5ebfb` |
| `docs/specs/W1_B3_coordination.md` (frozen) | `917c4bef94027d9c3967359d3a8ddadd4a27d98c476b7d4d5d74706b0b69a926` |
| `docs/specs/W1_B4_claims_belief_class.md` (frozen) | `a3f9df8fd3046e1e271e6a8d23ce97b62b2b87513bdfbc49fe9acaba0dea8695` |
| `docs/PHASE4_WAVE_PLAN.md` | `60688d725d38c36f43e734904efae9bc9e160ffa2facffa69b1267c83a5b2fd0` |
| `docs/NUCLEUS.md` (frozen) | `73c5a9cfb9af65e52f7cf1dbae60f250ae2c9180b8d3f554d108acc01eb83495` |

## 6. Consequences

- **Spec B5 is frozen.** No verdict/claim/gate movement; the 47-galaxy sprawl stays narrative-only
  (UNVERIFIED) and the cap-bypass/`_meta` items stay disclosed until closed by their own units.
  **Wave-1 is now fully specified:** all 8 table rows / 9 surfaces (durable store + ingestion
  gate, retrieval, disclosure, revisions, sessions, coordination, claims,
  galaxies/compartments).

## 7. Attestation

AI session `c7ab9666` compiled `docs/specs/W1_B5_galaxies_compartments.md`, verified every pin and
citation above, and recorded the operator's authorizing act and owner assignment. Ratification is
an external operator act; this receipt records it — it does not itself ratify.
