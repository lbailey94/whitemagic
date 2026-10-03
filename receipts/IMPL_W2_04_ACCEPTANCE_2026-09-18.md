# RECEIPT — W2_04 dream / consolidation acceptance demonstrated (2026-09-18)

**Status: evidence — acceptance demonstrated; row exit criteria met.** AI session
`221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) executed and attests. Spec
`docs/specs/W2_04_dream_consolidation.md` frozen at `71f66725…` (batch-freeze receipt
`receipts/W2_SPEC_BATCH_FREEZE_2026-09-17.md`). Append-only; corrections create a new receipt
referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Bundle | `receipts/impl_w2_04_2026-09-18/` |
| **SHA256SUMS** | `7b2b426b8f1a25574ab30e54938f8cff348ccefa1a96d1b67dfbb986d81d6fa4` |
| Binary | `target/release/wm-gen3` (sha256 `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`) |
| Driver | `driver_w2_04_consolidation.py` |
| Results log | `receipts/impl_w2_04_2026-09-18/consolidation.results.txt` |
| Stores | `store_a_active/`, `store_b_control/` |
| Journals | `store_a.journal.jsonl`, `store_b.journal.jsonl` |

## 2. Acceptance (spec §5 & prep §W2_04)

| # | Item | Result |
|---|---|---|
| 1 | **Pass-effect measurement (teeth test)** | **PASS**: Matched A/B control experiment demonstrates causal attribution. Store A (consolidation pass active) demotes un-used relation to `Cold` $\rightarrow$ subsequent recall excludes cold relation from active supersession $\rightarrow$ earlier record is un-penalized. Store B (control, pass inactive) retains live supersession $\rightarrow$ earlier record remains penalized by 0.6x supersede multiplier. |
| 2 | **Journal attestation** | **PASS**: Every lifecycle transition is attested in the journal (`relation.proposed`, `relation.state_change` `candidate→persistent` reason `survived+sweep+used`, `persistent→cold` reason `unused-k-sweeps`, `think.sweep` with full execution stats). |
| 3 | **Semantic object preservation** | **PASS**: Records intact and identical (2/2); relation preserved in LMDB store (`Cold` state, not deleted); zero deletion or purge events in journal. |
| 4 | **Promotion persistence across restart** | **PASS**: Relation state (`Cold` and `Persistent`) verified in a fresh process invocation opening the store on disk. |
| 5 | **Phase-agnostic & field-smuggling scan** | **PASS**: Static scan confirms absence of 12/13 phase enums, `DreamPhase`, CITTA counters, and unintegrated priming/decay symbols (`tick_decay`, `apply_priming`). |

## 3. Adversarial cases (spec §3)

1. **Destructive triage** (§3.1) — PASS: no deletion path reachable; records and relations preserved.
2. **In-memory "ran"** (§3.2) — PASS: passes without journal events are rejected; all transitions attested.
3. **Report-as-capability** (§3.3) — PASS: no decorative alchemical counters; execution verified through measured ordering effect.
4. **Label artifact** (§3.4) — PASS: no CITTA counts quoted as capability.
5. **Phase inheritance** (§3.5) — PASS: neither Gen1's 13 nor Gen2's 12 phases inherited.
6. **Field smuggling** (§3.6) — PASS: priming and decay remain gated; wave-4 boundary respected.
7. **Teeth test** (§3.7) — PASS: consolidation pass demonstrably changes measured recall behavior between matched stores.

## 4. Disclosures

- Consolidation in Gen3 is compiled as a journaled selection and lifecycle pass over evidence relations (`think_sweep`), not as a phase-loop daemon.
- The teeth of consolidation are verified: relation lifecycle state determines active supersession status during recall, directly shifting strata and rank keys.
- No core code changes were required; existing structural arbitration and sweep mechanics fulfilled all acceptance gates.
- No verdict, claim, gate, or threshold movement; WEAK stays WEAK.

## 5. Attestation

AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` executed `driver_w2_04_consolidation.py`, conducted the
matched A/B experiment, verified restart persistence and object preservation, pinned bundle `SHA256SUMS`,
and records this receipt.
