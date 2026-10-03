# RECEIPT — W2_02 retention / lifecycle acceptance demonstrated (2026-09-18)

**Status: evidence — acceptance demonstrated; row exit criteria met.** AI session
`221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) executed and attests. Spec
`docs/specs/W2_02_retention_lifecycle.md` frozen at `c9a2f09f…` (batch-freeze receipt
`receipts/W2_SPEC_BATCH_FREEZE_2026-09-17.md`). Append-only; corrections create a new receipt
referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Bundle | `receipts/impl_w2_02_2026-09-18/` |
| **SHA256SUMS** | `e7c95b88734893abcf621c23ffc52cc8e0432f6baae6fda6de158a42d4235237` |
| Binary | `target/release/wm-gen3` (sha256 `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`) |
| Driver | `driver_w2_02_retention.py` |
| Results log | `receipts/impl_w2_02_2026-09-18/retention.results.txt` |
| Store | `receipts/impl_w2_02_2026-09-18/retention_store/` |
| Journal | `receipts/impl_w2_02_2026-09-18/retention.journal.jsonl` |

## 2. Acceptance (spec §5 & prep §W2_02)

| # | Item | Result |
|---|---|---|
| 1 | **Primary: record persistence ≠ relation lifecycle** | **PASS**: Fixture records survive multiple explicit `think_sweep` passes, including `candidate→persistent` and `persistent→cold` relation state transitions. Every memory record remains 100% present, content-identical, and retrievable (5/5 records initial ≡ 5/5 records final). |
| 2 | **Pure reads invariant (bare bytes)** | **PASS**: `data.mdb` sha256 (`9526908f…`) invariant across 10 sequential recall queries. Reads are side-effect free. |
| 3 | **All-zero success impossible** | **PASS**: Persist failure (e.g. `duplicate_exact`) raises loudly as a typed refusal (`status: error`, `errors: ["duplicate_exact"]`), with `remember.refusal` journaled. The v26 all-zero aggregate "success" class is excluded. |
| 4 | **Organ naming & symbol absence scan** | **PASS**: Static scan of `crates/` and release binary confirms absence of `RetentionEngine`, `LifecycleManager`, `Lifecycle::forget`, `store.delete`, `purge_record`, and `decay_strength`. |
| 5 | **Never-armed sweep (no scheduler)** | **PASS**: Sweeps run exclusively upon explicit invocation (`cognitive.think_sweep` / batch completion); no background thread, daemon, or timer exists. |
| 6 | **Fixed import tier** | **PASS**: Records are created `RecordStatus::Persistent` across every constructor in `evidence.rs:204,281,338,375`. |

## 3. Adversarial cases (spec §3)

1. **All-zero "success"** (§3.1) — PASS: persist failures raise typed refusals loudly.
2. **Never-armed sweep** (§3.2) — PASS: sweeps only execute on explicit caller request.
3. **Uniform object-type policy** (§3.3) — PASS: records never decay or delete; relations undergo state transitions (`Candidate→Persistent→Cold`), never deletion.
4. **Propose-only** (§3.4) — PASS: relations are proposed and transition states; no records are pruned.
5. **Threshold statutory** (§3.5) — PASS: statutory sweep policy values are Tier-2 constants, journaled per sweep.
6. **Cold integrity** (§3.6) — N/A: Gen3 has no cold record tier; relation `Cold` is a state excluding cold relations from live supersession.
7. **Starvation** (§3.7) — PASS: typed refusals under budget exhaustion.
8. **Delete-path exclusion** (§3.8) — PASS: `store.delete` does not exist; no record deletion path exists in Gen3.

## 4. Disclosures

- Gen3 implements rotation not deletion: relation lifecycle is exercised dynamically, while memory records are immutable and persistent.
- The link to Gen2's `RetentionEngine` is established by naming the organ and demonstrating that record survival is uncoupled from relation decay.
- No core code changes were required; Gen3's structural invariants already guarantee record persistence.
- No verdict, claim, gate, or threshold movement; WEAK stays WEAK.

## 5. Attestation

AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` executed `driver_w2_02_retention.py`, verified all
acceptance criteria and adversarial cases, generated the bundle with `SHA256SUMS`, and records this receipt.
