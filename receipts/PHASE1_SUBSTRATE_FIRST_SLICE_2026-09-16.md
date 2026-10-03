# RECEIPT — Phase 1 substrate first slice + pre-flight smoke (2026-09-16)

**Status:** recorded · **Commits:** code + smoke artifacts in this commit · **Non-evidence
smoke results:** `experiments/contradiction/PREFLIGHT_FINDINGS_2026-09-16.md`.

---

## 1. What was built

| Piece | Contents |
|---|---|
| `wm-gen3-core::field` | relations `e=(w,s,c,t)` + kind/state/class; generic tokenizer (no vocabulary tables); the pre-declared candidacy rule + genericity property test + negative controls |
| `wm-gen3-core::store` | LMDB durable store (records/relations/postings/counters); records reconstructed only through `EvidenceRecord::from_wire` (crate-internal) |
| `wm-gen3-core::journal` | append-only JSONL journal (hash-only content default; sha256 helper) |
| `wm-gen3-core::ops` | `Substrate`: `remember · recall · think · inspect`, per-op selection contracts, current-preferred ranking, budget (fail-closed), canary probe, usage-based promotion owned by `think` |
| `wm-gen3-harness` (`wm-gen3` bin) | stdio JSON-RPC adapter: `serve --store/--profile/--max-requests/--rate-limit`; maps `memory.batch_create → remember`, `memory.episodic_search → recall`, `sandbox.set_limits → statutes`; triggers the post-ingest sweep; `WM_GEN3_JOURNAL` |
| `scripts/check_closures.sh` | scan scope extended to all plastic modules + the adapter (as announced in `PHASE1_CLOSURES_GREEN` §4.3) |
| `evidence.rs` | + `Class`, `RecordStatus`, `confidence`, `created_at`; construction discipline and compile-fail proofs unchanged |

## 2. Evidence

- `cargo test` → 16 unit + 5 compile-fail doctests, 0 failed. Includes the genericity property
  test (frozen out-of-corpus examples) and negative controls.
- `scripts/check_closures.sh` → PASS (dependency rule; mutation-surface rule, now covering
  `ops/field/store/journal` + harness).
- Canary: `gen3.canary` → `{refused: true, violations: 0}`; journal records
  `{"kind":"laundering","observed_domains":["Simulated"],"outcome":"refused"}`.
- Smoke (seed 1, non-evidence): control T8 100% / T1+T6 100%; Gen3 T8 0% (clean abstention),
  T1+T6 50% verified / R@5 75%. Full tables + commands + journals:
  `experiments/contradiction/`.

## 3. Honest boundaries

1. **In-crate reconstruction is privileged:** `from_wire` is `pub(crate)`; byte-level tampering
   with LMDB files is *not* covered (no integrity envelope). Phase-1 threat model is in-process;
   durable tamper-evidence is deferred with its own decision.
2. **Journal is not yet complete against `PHASE2_RUN_JOURNAL.md`:** no `run.end` event; journal
   file hash not in the run manifest yet; provenance.chain events are implicit in the selection
   events rather than emitted per result (H4 completeness pending).
3. **Promotion bookkeeping is per-process** (usage counter); cross-restart promotion relies on
   journal/history and has not been exercised.
4. **Rule precision is unresolved:** ~11k proposals / 776 records in the smoke. H3 and the A1
   ablation are the arbiters; no pre-run tuning beyond the documented stopword bugfix (see
   findings §5).
5. **T8 expected loss:** the fixture is an enrichment test; Gen3 Phase 1 has no bridging by
   design (findings §3).

## 4. Phase-1 gate checklist (contracts §0 / interface)

- [x] Four operations against real data (smoke)
- [x] Every selection explainable (`selection.decision` journal + `inspect`)
- [~] Epistemic class/provenance preserved (class/domain fixed; H4 per-result chain pending)
- [x] Canary survival (probe refused, violation count zero)
- [x] No new user-facing capability (adapter is harness plumbing; no release surface)
- [ ] Pre-registration freeze + `receipts/BUDGET.md` + pinned invocation (next)

**Gate status: substantial, not yet formally passed** — freeze step outstanding.
