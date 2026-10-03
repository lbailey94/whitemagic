# RECEIPT — A1 acceptance fixtures demonstrated (2026-09-17)

**Status: evidence.** AI session `68c17d3b-757b-476e-9d74-d3c8366d9a5c` (opencode) executed and
attests; no operator act required (no freeze, no verdict). Implementation freezes:
exact-hash gate `8c5e32f`; noise class table `c12179d` (spec rev 2 `d437ffed`, ratified `d3e5c7d`).
Append-only.

---

## 1. Artifact

| Field | Value |
|---|---|
| Bundle | `receipts/impl_a1_fixtures_2026-09-17/` |
| **SHA256SUMS** | `699ea2ee19fb239e5c008185a6abda76faf1f2729bb655429dfa7e57ab74d5ad` |
| Binary under test | `target/release/wm-gen3`, sha256 `76083d050e94e707b480f431418ae155392ec126facfcd48c076fe25d9df5f82` (release, built at the implementation freeze) |
| Tip at run | `c12179d`, tree clean |
| Drivers | `driver_noise.py` · `driver_scope.py` · `driver_partial.py` · `driver_drift.py` (+ `*.results.txt`, journals, responses) |

## 2. What was demonstrated (spec W1_A1 rev 2 §3–§5)

| # | Case | Result | Evidence |
|---|---|---|---|
| 1 | **Noise §5.7 (findings item 8)** | 5 declared classes refused with `class` named (`traceback`, `error_line`, `json_blob`, `function_repr`, `too_short`); 2 controls admitted; noise items absent (0 hits by unique token); record count 3 → 5 (controls only); ordering before == after; zero `duplicate_exact`; zero violations. Ablation `WM_GEN3_NOISE=0`: all 5 admitted and recallable; no refusals journaled | `noise.journal.jsonl`, `noise_ablation.journal.jsonl`, `noise.results.txt` |
| 2 | **Scope law §5.3 (case 5)** | identical bytes admitted under two scopes (`corpus:alpha:scope-demo` / `corpus:beta:scope-demo`); per-scope re-ingest refused `duplicate_exact`; fresh store admits the same bytes (no global dedup); recall provenance carries both scope sources; ordering unchanged by the refusals | `scope_a.journal.jsonl`, `scope_b.journal.jsonl`, `scope.results.txt` |
| 3 | **Bare bytes §5.6 (case 4, 9.1.7 #1)** | a separate process re-ingests both scopes: refusals only; store `data.mdb` sha256 **byte-identical** before/after (`1dc29615a312afe7…`) | `scope_refusal.journal.jsonl` |
| 4 | **Partial §5.5 (case 2, 9.1.7 #6)** | 468,019-byte item: single-outcome success, recalled byte-exact; budget-forced partial: 121 items → 120 admitted + 1 typed `write budget exceeded (fail-closed)`; `ingest.batch` written 120 < items 121; all 120 admitted recallable; refused item absent | `partial_large.journal.jsonl`, `partial_budget.journal.jsonl`, `partial.results.txt` |
| 5 | **Drift §5.4 (case 1, 9.1.7 #5)** | SIGKILL mid-batch (494/3000 committed); probe: reopen OK, record count == replay duplicate refusals (494), samples 0/1 hits with exact content, first item present; replay converges 2506 + 494 = 3000; third pass refuses all 3000 (exactly N identities); replay/third journal hash-outs verified | `drift_*.journal.jsonl`, `drift.results.txt` |

Acceptance coverage after this bundle: items 3/4/5/6/7 wired as runnable assertions; item 1
(duplicate refusal, cross-process) demonstrated in `IMPL_A1_GATE_2026-09-17` and re-exercised here
(second-process refusals); item 2 (context non-collapse) is the same provenance-scoped identity
mechanism as scope — source variation is wrapper-demonstrated, **kind variation is covered by the
unit test** `duplicate_gate_is_provenance_scoped` (the harness hardcodes `kind = Reported`).

## 3. Disclosures

- **Class precedence** = declared table order (§1.3 numbering); the traceback fixture item also
  contains an `Error:` line and resolves as `traceback`.
- **Scope realization:** scope is the caller's declared provenance (`corpus:<galaxy>:<tags>`). The
  recall response's `galaxy` field is a pre-existing harness display artifact (hardcoded `codex`,
  `crates/wm-gen3-harness/src/main.rs:324`) — scope evidence is the provenance chain / refusal
  sources, not that label.
- **Drift killed-run journal contains 0 events** (`ingest.batch` is written after the batch loop;
  per-item refusals are journaled but none occurred): no torn-line case was produced, so journal
  integrity on restart is vacuous for this fixture — the store coherence checks carry the
  assertion.
- **Drift "explicit degraded" branch** (store open failure) was not demonstrated — no corruption
  injection is available; the coherent branch is demonstrated. An open failure is loud
  (stderr + exit 1), never silent zero.
- **Forced write failure** (LMDB error mid-item) is not injectable in this harness; the partial
  branch is demonstrated via the statutory budget refusal, the large item via the single-outcome
  success path.
- Sweep off for the partial + drift fixtures (focus); noise + scope fixtures ran with the default
  sweep. O1/F4 untouched. Counts generated, never narrated.

## 4. Consequences

No verdict, claim, gate, or threshold movement; the frozen spec (rev 2) is the contract these
fixtures assert against. A1's remaining row-exit item is operator review of the acceptance
coverage above.
