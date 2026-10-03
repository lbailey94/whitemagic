# RECEIPT — A3 acceptance demonstrated (2026-09-17)

**Status: evidence.** AI session `68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) executed and
attests. Spec: rev 2 `bf4d3b53…` (amendment receipt `W1_SPEC_A3_AMEND_2026-09-17`; case 1
disposition operator-ratified). Append-only.

---

## 1. Artifact

| Field | Value |
|---|---|
| Bundle | `receipts/impl_a3_2026-09-17/` |
| **SHA256SUMS** | `574b72f349a07a99d920beabbee7c7fb3e5b9308b4b6a844c0d1275b8a1eb9c9` |
| Binary | `target/release/wm-gen3`, sha256 `7046db3f…` |
| Driver | `driver_a3_acceptance.py` (fixtures: direction/flip, F4 metric, history, round-trip, window, case 1) |

## 2. Acceptance items (§5)

| # | Item | Result |
|---|---|---|
| 1 | Strata ordering ablation (C2 template) | **cited** `CANARY_RERUN_2026-09-17` (C2 PASS) + reproduced in `W2_03` scrubbed-env driver |
| 2 | Direction-aware proposal scoring (H3) | **driver**: A (old→new ingested) → `src=new, dst=old`; B (reverse order) → `src=later-ingested, dst=earlier` — direction follows temporal precedence, a flip registers |
| 3 | Round-trip (C5 template) | **driver**: relations byte-identical across processes (`kind/src/dst/rule_id/state/w/s/c/t`) + canary C5 |
| 4 | F4 guard | **driver**: raw proposals = **5**, deduped endpoint pairs = **1** — headline metric uses the deduped count, raw counter disclosed; + `W2_03` unit test (3 rows / 1 pair) |
| 5 | No score nudges | **cited** `IMPL_B1_ACCEPTANCE` (no-planner scan + single rank-key step + 0-diff) |
| 6 | History-lossless | **driver**: `include_historical` restores the superseded record (all stratum 1; both records present) |
| 7 | State-resolution wrapper (TBII template) | **cited** consolidation §2 (54/60 adjudicated vs control 34/60, MEASURED) — scored corpora are burned; the template remains the acceptance shape |

## 3. Adversarial cases (§3)

| # | Case | Disposition |
|---|---|---|
| 1 | Predicate-sense collision | **FINDING → rev 2 declared property**: rule v1 is lexical and links the pair (1 proposal, `a3_c.journal.jsonl`); spec case reworded (operator-ratified); rule v2 (value-replacement) registered as a **gated candidate** — no execution |
| 2 | Temporal absence | **declared N/A**: intake always stamps `created_at`; the rule uses intake time only (no content-time claim) |
| 3 | LABEL/state-conflict | **cited**: audit flags visible, no penalty tuning (N5) + no-planner scan |
| 4 | Window queries | **driver**: `relation.proposed` `ts` values are monotone and support a `changes_since`-style window (all 5 proposals in-window) — journal-as-evidence, no fact table |
| 5 | F4 carry | **item 4** (deduped metric + raw disclosed) |
| 6 | Atomic vs partial sweep | **cited**: relations commit per proposal; a killed sweep leaves **no** `think.sweep`/`run.end`/hash-out — the run is invalid, never "success" (A1 drift fixture: killed journal 0 events) |
| 7 | Drift disclosure | **cited** `IMPL_A1_FIXTURES` (drift fixture) |
| 8 | Read-only discipline | **cited** `IMPL_A2_DISCIPLINE`, `W2_07`, `OPS_FOLDIN_PARITY_AUDIT` (read-path audit) |
| 9 | Starvation-vs-refusal | **cited** `IMPL_A2_DISCIPLINE` |

## 4. Disclosures

- Case 1 is a **measured property**, not a passing prohibition (rev 2); the collision class has a
  real ordering effect (penalty + `superseded_by`), bounded by both records still being returned
  and audit flags staying visible.
- Case 6's partiality disclosure is **run-level** (missing `think.sweep`/`run.end`/hash-out marks
  truncation); there is no per-sweep "partial" event, and none is claimed.
- TBII (item 7) is cited, not re-run — its corpora are burned; re-running would be a new
  registration.
- No verdict, claim, gate, or threshold movement; WEAK stays WEAK; counts generated.
