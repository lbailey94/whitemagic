# Wave extraction protocol (methods that earned their keep)

**Status:** method record · 2026-09-17 · derived from the Phase-3 compile pass and the three wave
extraction batches (19 findings files + 8 intermission files). Reusable for every future pass
(matrix v2, nucleus freeze, Wave-4 specs). No doctrine: every rule below caught real errors
during this program, and each cites the failure that earned it.

---

## 1. The phenotype ladder (implemented ≠ real)

```
NAMED → IMPLEMENTED → REACHABLE → EXECUTED → EFFECTFUL → PERSISTENT → RE-ENTERS → EXTERNAL
```

Per-rung evidence type (only the first three are statically attainable; the rest require runtime
instruments — Gen3's journal is the instrument for rungs 4–8):

| Rung | Evidence |
|---|---|
| NAMED | docs/registry/manifest |
| IMPLEMENTED | code at the declared location |
| REACHABLE | call path from a real entry point (static) |
| EXECUTED | journal/log/telemetry event (runtime) |
| EFFECTFUL | state actually changed (measured) |
| PERSISTENT | change survives restart (measured) |
| RE-ENTERS | selection/retrieval reads it (ablation) |
| EXTERNAL | consequence outside the system (measured) |

Set relation over *evidence classes*: `P_declared ⊇ P_implemented ⊇ P_reachable ⊇ P_executed ⊇
P_effectful ⊇ P_contributing`. Static absence of a caller supports **"not wired as shipped,"**
never **"never executed."** (Earned by: tours over 662 tools where half the organs were
unreachable; dream cycles that ran 284× with zero effect.)

## 2. The mechanical spiral (same ladder, dynamic view)

input → activation → transformation → **durable delta** → delta influences selection → changed
output → external consequence → changed state. Break any edge and you get a partial loop:
dormant Hebbian = transformation→learning broken; all-zero persistence "success" =
effect→durability broken; empty constellation boost = structure→retrieval broken; unmatched
skill traces = recipe→execution broken; never-ticking decay = time→state broken; self-verifying
RSI = proposal→independent-consequence broken.

## 3. Evidence levels for every inheritance claim (per claim, not per document)

`NAMED → SOURCE-IMPLEMENTED → STATICALLY-REACHABLE → RUNTIME-OBSERVED → MEASURED →
OUTCOME-VALIDATED`. A spec may mix levels; each statement carries its own. (Earned by: "static
archaeology is not runtime evidence" — the intermission promoted/demoted 6 findings.)

## 4. Timeline provenance rule

`created_at` in the recovered stores is a **source date**. Establish the provenance of the
timeline itself before making era claims: imported rows (Windsurf/opencode backfills ingested
Jul 30–31) carry original dates. (Earned by: "Gen1 = Jan→Aug" collapsing to a lived era of
≈ late May → Aug 2.)

## 5. Identity rules

- **Classify by function, never by name.** Names establish search leads, never identity;
  identity is established by dataflow, effects, persistence, and callers. (Earned by: `violet` =
  engagement tokens; `god.nodes` = graph analytics; `bagua` = symbolic router; `smarana` =
  retention tracker; "Geneseed" shipped twice as unrelated miners; "friction" is Gen2 vocabulary.)
- **Counts are generated, never narrated.** Every count cites its generating command. (Earned
  by: stale docstrings, 166→156 docs, 303-vs-302 live-vs-tag, CITTA 18,204 as a label artifact,
  Δ1,345 turns, "39 absorbed" vs 44, 0.078 Brier misattribution.)

## 6. Cross-batch verification (the part that must not be dropped)

Later batches audit earlier ones; the errata register never deletes. Batch 3 corrected batch 2
(field channel was live); the intermission corrected batches 1–3 (329 insights invisible at the
tool layer; CORRECT not never; Brier identity). A finding is only as good as the pass that tried
to falsify it.

## 7. The do-not-migrate taxonomy (both generations)

Reasons to exclude, each with its own disposition: **unwired** (no callers as shipped) ·
**inert persistence** (written but never read; all-zero "success") · **self-verifying** (maker =
checker) · **name collision** (label survived, function didn't) · **cosmetic ontology** (typed
structure erased at persistence) · **unsafe boundary** (unenforced mask, unsigned frames) ·
**timeline artifact** (imports, backfills, fixtures) · **Gen2-side zombies** (Gen2 is not a
wiring utopia: `forget()` uncalled, `tick_decay` uncalled, stub world-model, curated-excluded
RSI). Every Phase-4 exclusion names its reason from this list.

## 8. Extraction workflow discipline (what made subagent batches integrable)

One file per workstream; strict file format (observed behavior · selection history · candidate
expression/manifest · adversarial cases · ablation · open questions); compact return summaries;
read-only with `mode=ro` for all stores; every inference marked; no doctrine. Orchestrator
verifies hashes/counts independently before integration.

## 9. Regression against recorded cells (construction phase, earned 2026-09-17)

- **Three identities, never conflated.** *Source identity* = commit hash + tree state (+ toolchain
  pin): which source. *Artifact-instance identity* = binary sha256: which exact bytes were tested —
  an instance label, nothing more. *Behavioral equivalence* = a demonstrated condition: the same
  controlled source/toolchain/environment producing equivalent output **according to a stated
  criterion** (canaries, per-query ordering/metric diffs, journal event sets). Reproducibility is
  the third concept and must be *demonstrated*, never inferred from either of the first two. Builds
  on this host are not byte-reproducible (two fresh builds of frozen `7ff9181` differ; the nucleus
  binary `b1c66fec` was not reproduced; a test-only edit changed the release hash
  `76083d05`→`7046db3f`), so S7 toolchain bumps re-run the canaries and record a behavioral
  baseline under this vocabulary. (Earned by: `IMPL_B1_ACCEPTANCE_2026-09-17` §3; errata §H #32.)
- **Recorded all-off cells predate the A1 exact-hash gate.** Raw memorastrict corpora contain
  same-session repeated turns, so the current binary refuses them `duplicate_exact` by spec — a raw
  comparison measures an intake change, not the ranking path. The standard regression recipe is a
  **gate-neutralized corpus**: deduplicate by the gate identity (session, role, `has_answer`,
  content) with a scripted, hash-recorded derivation, then compare candidate vs a source-frozen
  reference (and/or recorded cells) with all switches off. Ordering/metrics must be exact; scores
  may differ by at most 1 ULP at f32 (codegen-level). (Earned by: `IMPL_B1_ACCEPTANCE_2026-09-17`
  §3; errata §H.)
- **Corpus transforms are first-class records.** A transform that conditions a source corpus for
  comparison carries: `transform_id` (`<kind>.v<version>.<date>`) · `kind` (declared class) ·
  `source_identity` (source MANIFEST hashes) · `operation` (the exact scripted derivation + driver
  reference) · `output_identity` (output hashes) · `lineage` (parent transforms; `none` for v1) ·
  `scope` (which regressions may cite it) · `disclosures` (what changed vs source). Any regression
  citing recorded cells on a transformed corpus cites its `transform_id`. First instance:
  `gate-neutralize.v1.2026-09-17` (`receipts/transforms/TRANSFORM_gate_neutralize_v1_2026-09-17.md`),
  used by `IMPL_B1_ACCEPTANCE_2026-09-17`.
- **Score equality across systems is never required.** Gen2 bundle scores, recorded-cell scores,
  and Gen3 D2 support are different scales; the join is field semantics, not value equality
  (`docs/BUNDLE_JOURNAL_PARITY.md`).
