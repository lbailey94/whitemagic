# WMgen3 — Reference Index (read-only)

Everything here is a pointer. No copies, no forks — the sources stay authoritative
where they live.

## Symlinks in this directory

| Link | Target |
|---|---|
| `gen2-wmv9` | `/home/lucas/Desktop/WHITEMAGIC/WMv9` (Gen2 source; frozen as control during Phases 0–2) |
| `gen1-v26` | `/home/lucas/Desktop/WHITEMAGIC_GEN1_v26.0.3` (Gen1 terminal tree; phenotype/capability archive) |

## Key artifacts (absolute paths)

| Artifact | Path | Why it matters |
|---|---|---|
| Capability Matrix (Gen1↔Gen2) | `~/Desktop/WHITEMAGIC_GEN1_VS_GEN2_CAPABILITY_MATRIX_2026-09-16.md` | Verdict vocabulary + per-capability evidence; feeds the Phase 3 decomposition |
| Narrative & Development Arcs | `~/Desktop/WHITEMAGIC_NARRATIVE_AND_DEVELOPMENT_ARCS_2026-09-16.md` | The two-generation story; Part V holds the Gen3 questions |
| Lineage Ledger | `~/Desktop/WHITEMAGIC/WMv9/docs/LINEAGE_LEDGER.md` | Every v26 system adjudicated with citations — the ancestor map |
| Capability Ledger | `~/Desktop/WHITEMAGIC/WMv9/docs/CAPABILITY_LEDGER.md` | intended → implemented → wired → tested rows; DEMO-unknown list |
| Honest Gaps | `~/Desktop/WHITEMAGIC/WMv9/docs/HONEST_GAPS_2026-09-14.md` | The debts Gen3 inherits (AHIMSA truth-up is fixed in 9.1.8) |
| 3-day design transcript | `~/Desktop/WHITEMAGIC CHATGPT CONVERSATIONS.txt` | The full morning's convergence: selection, epistemic triple, genetics, X landscape |
| Gen1 core comparison (data) | `~/Desktop/WHITEMAGIC_GEN1_v26_CORE_COMPARISON_2026-09-15.md` | 99.97% overlap; dedup plan; orphan recovery |
| Gen1 memory core | `~/Desktop/WHITEMAGIC_GEN1_v26_MEMORY_CORE/` | 46 galaxy SQLite DBs — phenotype evidence |
| TECH_TREE / CHRONOLOGY | `~/Desktop/WHITEMAGIC-NOTEBOOK/` | Retroactive history v0.1→v9 |

## Workspace docs derived from these sources (in `docs/`)

| Doc | What it carries |
|---|---|
| `docs/DESIGN_CANON.md` | Converged Gen3 design vocabulary from the three-day transcript, each element tagged IMPL-G2 / PARTIAL-G2 / DESIGN / DEFERRED / CAND-LAW, cross-checked against code |
| `docs/CODE_ARCHAEOLOGY.md` | Verified Gen1↔Gen2 survey (paths + line evidence), Gen3-relevant presence/absence table, and the claim-vs-measured discrepancy ledger |
| `docs/PHASE1_EXPERIMENT_INTERFACE.md` | How the A/B harness drives each arm (wire protocol, routes, ids round-trip, scoring map), required Gen3 instrumentation, pinned configuration + open decisions |
| `docs/PHASE1_CONTRACTS.md` | Field `e=(w,s,c,t)` / record schema, four operation contracts (six-question template), pre-declared supersession candidacy rule, ablation-debt ledger, open decisions D1–D5 |
| `docs/METABOLISM_PLAN.md` | One-pager: externally grounded intake table, two-gate boundary, M health metric, consent rules, next artifacts |
| `docs/PHASE2_RUN_JOURNAL.md` | Run-journal schema (event types, metric joins for H3–H8, smoke marking) — the instrumentation carrier for Phase 2 |
| `docs/PHASE3_DECOMPOSITION.md` | Study seed: capability families from the generated 302-route inventory × Gen1 ancestry, verdicts pending Phase 2; Phase-1 expression notes |
| `docs/PHASE1_SCORE_POLICY.md` | D2 detail: idf-weighted query-support score (recommended) vs saturating BM25; boundaries and sign-off request |
| `receipts/PHASE0_VERIFICATION_2026-09-16.md` | Independent re-check: control binary, tag commit, corpus hashes, and the ratified Phase-0 document hash set |
| `experiments/contradiction/PREFLIGHT_FINDINGS_2026-09-16.md` | Non-evidence smoke results (control vs Gen3, seed 1), T8-is-bridging discovery, rule sensitivity, pre-freeze decisions |
| `experiments/contradiction/RESULTS_2026-09-16.md` | Phase-2 A/B scored outcome (LOSS branch), H1–H8 tables, named findings F1–F3; raw artifacts under `results/` |
| `experiments/semantic_projection/PRE_REGISTRATION.md` | Successor pre-registration (2×2 S×R factorial: projection × supersedes; numeric materiality pins; frozen embedding config + genericity battery) — plan frozen, `claim-0001` registered (now **falsified**; results below) |
| `experiments/semantic_projection/RESULTS_2026-09-16.md` | P2B factorial results: projection rejected per pre-reg (M1 solo, M3 recall, M4); key observation — primitives are *dependent* (C10 ≡ C00; C11 composes); artifacts under `results/` |
| `experiments/semantic_projection/PRE_REGISTRATION_P2C.md` + `holdout/` | **FROZEN** interaction claim (`claim-0002`) on unseen holdout seeds 6–10 — now **falsified**; results below |
| `experiments/semantic_projection/RESULTS_P2C_2026-09-16.md` | P2C holdout results: reach interaction replicated (I_top5 +8), verified/ordering did not (I_verified −4, I_M2 −27.5pp) → claim-0002 falsified; arbitration = leading candidate primitive; artifacts under `results_p2c/` |
| `experiments/semantic_projection/PRE_REGISTRATION_P2D.md` + `holdout_p2d/` | **FROZEN** arbitration claim (`claim-0003`, pending): structural-precedence selector, B0/B1/B2 cells, fresh holdout seeds 11–15; results below |
| `experiments/semantic_projection/RESULTS_P2D_2026-09-16.md` | P2D results: B2 best-ever (34/40 verified, M2 85 %); ΔOrdering +16.6 pp PASS; ΔReach +2 FAIL (headroom artifact) → WEAK, claim-0003 pending; artifacts under `results_p2d/` |
| `experiments/semantic_projection/ANOMALY_STUDY.md` | Exploratory read-only forensics on seed-2/14 rank-1 failures: template-token overweighting (A1), within-stratum ordering ignores projection agreement (A2), strict τ blocks signal (A3), corpus ground-truth conflicts (B); headroom-aware metric formalized for claim-0004 |
| `docs/GROUND_TRUTH_AUDIT_PROTOCOL.md` + `ground_truth_audit.py` | **FROZEN v1.2** label/chronology conflict audit (6 flags across seeds 1–15); raw + adjudicated reporting; applies to P2E |
| `experiments/semantic_projection/PRE_REGISTRATION_P2E.md` + `holdout_p2e/` | **FROZEN** contextual-dispersion claim (`claim-0004`) on fresh holdout seeds 16–20 — now **falsified**; results below |
| `experiments/semantic_projection/RESULTS_P2E_2026-09-16.md` | P2E results: dispersion unblocks 4/6 blocked questions but net redistribution (raw unchanged; adjudicated worse) → claim-0004 falsified; audit protocol caught the seed-18 pseudo-gain |
| `experiments/semantic_projection/FAILURE_TAXONOMY.md` | **FROZEN** read-only failure taxonomy (42 failures, 4 datasets): LEX_TAU dominant/recurring (18), LEX 8, LABEL 6, TIE 4, STRAT/STATE2/REACH uniques; ungated cosines 10/12 in favour of the correct turn |
| `docs/RESEARCH_NOTES_MULTI_VIEW_SELECTION.md` | Research note: selection among imperfect signals is the hard part; candidate directions (evidence bundles, Pareto, context arbitration, projection-agreement diagnostic) — not implemented |
| `docs/TESTBED_II_REQUIREMENTS.md` | Requirements/options for a different-distribution audited testbed (fresh generator recommended); frozen mechanisms only; audit mandatory; A3 carried as diagnostic |
| `experiments/contradiction/smoke/` | Raw smoke artifacts: result JSONs + run manifests + Gen3 journals |

## Ground rules reminder

- Symbols may render; symbols may never dispatch.
- Gen2 remains production; this root owns no production stores.
- Every exception to the contamination boundary gets a receipt in `receipts/`.
