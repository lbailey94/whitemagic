# RECEIPT — W2_01 acceptance demonstrated (2026-09-17)

**Status: evidence.** AI session `68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) executed and
attests. Spec W2_01 frozen (`W2_SPEC_BATCH_FREEZE_2026-09-17`). Append-only.

---

## 1. Artifact

| Field | Value |
|---|---|
| Bundle | `receipts/impl_w2_01_2026-09-17/` |
| **SHA256SUMS** | `add54402bf58933035ef432eb81c24d323909b5a681e6fe8517aaba48ad463a6` |
| Binary | `target/release/wm-gen3`, sha256 `6583cc73…` |
| Driver | `driver_w2_01_edges.py` |

## 2. Acceptance (§5)

| # | Item | Result |
|---|---|---|
| 1 | C5 extension — kind/direction/provenance round-trip | **driver**: relations byte-identical across processes incl. `rule_id` (edge provenance), `state`, `w/s/c/t`; + `IMPL_A3_ACCEPTANCE` |
| 2 | Direction registration | **driver** + `IMPL_A3_ACCEPTANCE`: later→earlier; flip fixture registers |
| 3 | No hidden coupling | **cited** `IMPL_B1_ACCEPTANCE` (rank-field audit + no-planner scan + 0-diff) |
| 4 | Counts are edges, not attempts | **driver**: admitted rows = raw proposals = 5; deduped endpoint metric = 1; sweep attempt stats (`pairs_*`) stay separate |
| 5 | Manifest gate (dynamics) | **driver scan**: no `hebbian`/`decay`/`strengthen`/`weaken`/`edge-prune` symbol in the serving path — dynamics parked; any import would need its own registration |

## 3. Adversarial cases (§3)

| # | Case | Disposition |
|---|---|---|
| 1 | Round-trip erasure | **driver** (round-trip incl. provenance) |
| 2 | Target-side symmetry | **driver**: both endpoints listed on the edge row; direction is stored (asymmetry is direction, not visibility) |
| 3 | Extraction-dependent signal | **declared**: no graph/entity coupling exists in the ranking path (no-planner scan); no weight can be live without its signal because none is imported |
| 4 | Homogeneous-stream growth | **driver**: declared rate/quality gates — `pair_budget 200000`, `rare_df_divisor 20`, `rare_df_floor 2` (tier-2); no name blacklists |
| 5 | Causal from weak ordering | **declared**: the sweep orders by `created_at` and the rule requires strict later > earlier — Δt=0 yields no proposal; no inversion path exists |
| 6 | Attempts ≠ rows | **item 4** |
| 7 | Transfer asymmetry | **declared N/A**: Gen3 has no edge-transfer mechanism (nothing can silently revert) |
| 8 | Read discipline | **cited** `OPS_FOLDIN_PARITY_AUDIT` (read-path audit) + `W2_07` |

## 4. Disclosures

- Edge counts are reported raw **and** deduped (F4 guard); no metric uses the inflated raw count as
  a headline.
- Dynamics stay parked: the mechanism status is stated wherever cited (Hebbian live in Gen2's
  mechanism, absent from the Gen3 serving path).
- No verdict, claim, gate, or threshold movement.
