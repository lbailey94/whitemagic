# RECEIPT — B5 acceptance demonstrated (Gen3 compile/link side) (2026-09-17)

**Status: evidence.** AI session `68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) executed and
attests. Spec W1_B5 frozen (batch B receipt). Append-only.

---

## 1. Artifact

| Field | Value |
|---|---|
| Bundle | `receipts/impl_b5_2026-09-17/` |
| **SHA256SUMS** | `eba1590b742635c76c4d64827ecee1da50e138cf2f634e43cd6dfe7179f742f0` |
| Binary | `target/release/wm-gen3`, sha256 `6583cc73…` |
| Driver | `driver_b5_scopes.py` |

## 2. Acceptance (§5)

| # | Item | Result |
|---|---|---|
| 1 | Scope-label behavior (labels are views; no per-name resources) | **driver**: 30 labels (over Gen2's dynamic cap of 20) → store file set stays `{data.mdb, lock.mdb}`; 30 records; no per-name resources; labels derived from provenance (`corpus:<label>:<tags>`) |
| 2 | Fail-closed unknowns; membership ≠ authz | **declared (link side)**: Gen3 has no compartment surface; `_meta.compartment`-style membership is never authorization — any authorization story needs an authenticated channel (out of scope; the disclosure is the contract) |
| 3 | Cross-class transfer | **declared (link side)**: Gen3 has no class markers; the transfer/class machinery stays Gen2-side |
| 4 | Cap + bypass | **closed by absence**: no dynamic registry exists, so the UNVERIFIED physical-registry bypass path cannot exist (disclosed) |
| 5 | Effective-grant reporting | **declared (link side)**: no tier labels in Gen3 to outrun enforcement |

**View filter (supporting):** a label view is reconstructible from the evidence surface — the
provenance-chain prefix selects exactly that label's records (wrapper-side filter, no new API);
30 distinct labels observed in one recall. **No registry surface:** inspect exposes no
galaxy/label/registry/compartment/capability keys (key scan).

## 3. Adversarial cases (§3)

1 unbounded scope names ✓ (no per-name resources) · 2 isolation asymmetry — N/A (no classes) ·
3 explicit-selection creep — N/A (no isolation filter exists to creep) · 4 capability typos — N/A
(no capability parameter) · 5 tier-degradation label — N/A (no tier labels) · 6 cap bypass —
closed by absence · 7 membership-vs-authz — declared · 8 fail-open-on-governance-error — N/A
(no governance path; Gen3's fail-closed is the budget/floor discipline — A1/A2 receipts) ·
9 narrative guard — cited (errata A#6: 47-galaxy figure is narrative-only; no Gen3 metric cites it).

## 4. Disclosures

- Gen3's scope mechanism is **provenance-based** (`source` strings; the A1 gate keys on them —
  scope law demonstrated in `IMPL_A1_FIXTURES`). Label *views* are wrapper-side filters over the
  evidence surface; no filtering API is added by this row.
- The compartment/authorization machinery is **link-side**; nothing in this receipt authorizes
  treating labels as security boundaries.
- No verdict, claim, gate, or threshold movement.
