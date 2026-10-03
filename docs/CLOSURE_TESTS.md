# Phase 0 — Closure Test Specifications

**Status: encoded 2026-09-16 (v1.0).** These specs define the Phase 0 gate tests for Chrome
1 and Closure 2. Implementation lands with the Phase 1 scaffold; the Phase 0 gate is passed
when both static analyses and both runtime canaries exist as executable tests producing
receipts. Specs are frozen with the Charter version they test.

Related: `CHARTER.md` §3 invariants 7–8, §5 enforcement table.

---

## 1. Closure 1 — Law

**Invariant under test:** No adaptive write path reaches constitutional state. Constitutional
state may be read only through an immutable typed interface.

### 1.1 Static analysis — write-unreachability

| Test | Method | Pass condition |
|---|---|---|
| A. Type isolation | Constitutional state lives in a dedicated module (`constitution`) behind a `ConstitutionView` read-only facade; mutation APIs are visibility-gated to the amendment module only | Compile-time: adaptive modules cannot name mutation APIs; no `&mut` accessor exists outside the amendment module |
| B. Source analysis | Parse the workspace (syn) and assert: no `&mut Constitution`, no write-method call, and no `Constitution::amend` reference reachable from adaptive modules | Zero findings; findings list offending file:line and path |
| C. Dependency check | Module/crate graph: adaptive crates have no dependency edge to the amendment module; `cargo tree` rules per `DEPENDENCY_MANIFEST.md` | Zero forbidden edges |
| D. Read-interface check (positive) | Assert the immutable typed view exposes exactly the fields the adaptive layer may read (budgets, limits, current statutes) and nothing mutable | View is complete for adaptive needs and has no mutators |

### 1.2 Runtime canary — Law

- **Sentinels:** constitutional state contains sentinel values (e.g. `canary_budget`, a
  sentinel invariant hash) known only to the test harness.
- **Attack surface:** the canary attempts mutation through *every* exposed adaptive
  interface: typed attempts, deserialization round-trips, store-level writes to the
  constitutional namespace, and tampered receipts.
- **Expected:** every attempt is refused; each refusal produces a structured violation
  event `{ts, path_attempted, mechanism, refused_by, receipt_id}`; sentinel values are
  byte-identical after the run.
- **Positive control:** the amendment module (external authority) successfully writes a
  *test* amendment and emits a signed amendment receipt. If the guard blocks this too, the
  guard is misconfigured and the test fails.
- **Negative control:** the same write attempted by the adaptive layer through the
  amendment module's public surface (if any) must fail.

---

## 2. Closure 2 — Evidence

**Invariant under test:** Domains are immutable and non-promotable; inference cannot create
world-evidence; world-evidence enters only as new records via ratified intake channels.

### 2.1 Static analysis — immutability and intake

| Test | Method | Pass condition |
|---|---|---|
| A. Construction-set domain | `Evidence { domain: Domain, .. }`: `Domain` fixed at construction; no setter anywhere in the workspace | Zero `domain =` assignments outside construction paths |
| B. Append-only records | Store write API accepts whole-record inserts for evidence; no field-mutation API on existing evidence records | No code path mutates a persisted evidence record in place |
| C. No re-label path | Source analysis: no write path maps an existing record id from `reported/simulated/system` to `world` | Zero re-label paths |
| D. Intake-channel gate | Creation of `domain = world` requires a provenance tag identifying a ratified intake channel | `world` creation without channel tag is impossible through public APIs |

### 2.2 Runtime canaries — Evidence

| Canary | Scenario | Expected |
|---|---|---|
| A. Laundering | Create `simulated` evidence; run all inference paths (think/remember) attempting to re-classify it as `world` | Zero promotions; any attempt logs a violation event |
| B. Testimony | Inject a communication record: "source X asserted Y" via the intake channel | The **communication event** may be recorded as `world` (it happened); **Y itself** remains `reported`/belief; no `world` record exists for Y's content |
| C. Unchannelled intake | Attempt to create `world` evidence with no ratified channel provenance | Refused; violation logged |
| D. Positive intake | Ratified stub sensor creates a new `world` record | New record created with channel provenance; all pre-existing records byte-identical; intake receipt emitted |

---

## 3. Violation handling

- **Zero tolerance in Phase 2:** any violation halts the experiment, produces a receipt, and
  counts against H6 (which requires zero).
- Violations are always logged with a stable schema; `inspect` must surface the violation
  log alongside the tier map.
- **Tier map requirement:** `inspect` answers for any state: tier owner · readers · writers
  · path · authority — and which closure would refuse an attempted write.

---

## 4. Phase 0 gate checklist

- [ ] Charter v0.1.1 ratified (operator signature + hash receipt)
- [ ] Static analysis A–D (Closure 1) and A–D (Closure 2) implemented as executable tests
- [ ] Runtime canaries (both closures) implemented with positive/negative controls
- [ ] Both closures produce machine-checkable receipts on green runs
- [ ] `inspect` tier-map/violation-log obligations scheduled into Phase 1 surface
- [ ] GEN3-THESIS-001 registered in the Claims Ledger
