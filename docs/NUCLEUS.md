# WMgen3 — NUCLEUS snapshot (four-part)

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per
`docs/NUCLEUS_FREEZE_CRITERIA.md` §4.1 by opencode session
`f46d94c5-f8bb-4697-a53f-5e944c913540` at WMgen3 tip `7ff9181` (tree clean). This draft performs
no freeze: it names the snapshot's contents and pins, records the verification and canary results
(§5–§6), and leaves ratification to the operator (§9). The freeze takes effect only at operator
ratification + `receipts/` entry. Docs-only: no code, no gates changed.

**Authority.** `CHARTER.md` (v0.1.1) governs the constitutional core; the ratified
`PHASE3_DECOMPOSITION.md` and its receipts govern the dispositions recorded beside the snapshot
(§7). Where this file and a source diverge, the source governs and the divergence is a finding.

**Reading rules (criteria §1).** The four parts are pinned together but are not the same kind of
law. Tier 1 amends only via Charter §4. Tier 2 is versioned and externally amendable. The
reproducibility pins are anchors, not capabilities — regenerated whenever a constituent changes;
a mismatch is a finding, not a re-pin.

```
FROZEN GEN3 NUCLEUS SNAPSHOT (proposed)
│
├── 1. Constitutional core            ← Tier 1 (Charter §3; ten invariants)
├── 2. Earned cognitive nucleus       ← admission §2a of the criteria (empirical)
├── 3. Statutory baseline             ← Tier 2 (versioned, externally amendable)
└── 4. Reproducibility pins           ← historical anchors, not cognition
```

---

## 1. Part 1 — Constitutional core (Tier 1)

The ten invariants, verbatim from `CHARTER.md` v0.1.1 §3 (pinned: §4). No adaptive **write** path
reaches this part; reads flow only through an immutable typed interface (invariant 7); amendment
only via Charter §4 (proposal → canary demonstration → operator ratification → receipt). Ten is
the set — new invariants are discovered by experiments that break these.

1. **Bounded effects & resources.** Budgets are enforced fail-closed at every adaptive boundary;
   adaptive execution cannot knowingly exceed them without externally authorized policy change.
   Runaway behavior is prevented by enforcement and refusal, not asserted impossible.
2. **No silent destructive action.** Adaptive replacement of memory is rotation, not deletion;
   suspicious structure is quarantined, not destroyed. Destructive deletion requires explicitly
   authorized intent and an auditable receipt. **Authorized erasure** (privacy, consent
   withdrawal, legal requirement, ordinary ownership) always overrides rotation and quarantine —
   the operator retains the right to delete.
3. **Provenance on every durable record.** Origin, history, and supersession chains are retained;
   nothing enters durability unattributed.
4. **Recoverability.** Snapshot before mutation; restore must actually work; backups are verified,
   not assumed.
5. **Governed egress.** Every boundary crossing is inspectable and consent-governed; local-first
   defaults; no silent transmission of memory, prompts, or usage data.
6. **Truthful surfaces.** Advertise only probed capabilities; disclose uncertainty; abstention over
   silent success. Material failures, limitations, and counterevidence are durably recorded and
   disclosed wherever relevant to claims; sensitive details may remain access-controlled.
7. **Closure 1 — Law.** No adaptive write path reaches constitutional state; constitutional state
   may be read only through an immutable typed interface. Enforced by static write-unreachability
   analysis + runtime canaries + `inspect` + receipts.
8. **Closure 2 — Evidence.** Inference alone cannot create world-evidence, and **no existing
   evidence record's domain may ever change.** Domains (`world`, `system`, `simulated`,
   `reported`) are immutable: testimony remains `reported`; simulations remain `simulated`; system
   logs remain `system`. World-evidence enters only as **new records** through a ratified
   world-intake channel (trusted sensor, authenticated source, recorded action consequence) with
   provenance.
9. **Epistemic separation.** Evidence, belief, and speculation remain distinct and inspectable;
   durability ≠ truth ("graduates into persistence, not truth").
10. **Symbolic neutrality.** Symbols may render; symbols may never dispatch. No symbolic system
    (Tree of Life, Suares, Tarot, Yijing, Ganas, Gardens, alchemy, biology, astronomy) may create
    a runtime branch because the symbolism says one ought to exist.

**Motto of the experimental era: let Gen3 lose if it loses.**

## 2. Part 2 — Earned cognitive nucleus (admission: criteria §2a)

Admission requires all six criteria §2a conditions (earned by evidence · reproducible ·
ablatable with behavioral teeth · minimal · audited · inspected). Evidence pointers below; counts
are regenerated from artifacts, never authored. No `IRREDUCIBLE` row exists: no family showed a
general failure of the basis (compile-pass receipt §2).

### 2.1 Admitted mechanisms

**N1 — Durable records + provenance chains.** (Admitted on cross-ecology standing + closure
canaries.)
- *Evidence:* H4 = 100 % provenance completeness at result granularity and H6 = zero
  constitutional violations on every scored run, across eight corpora (matrix rows H4/H6;
  consolidation §1, §4); both closures machine-tested green before any adaptive cognition existed
  (`receipts/PHASE1_CLOSURES_GREEN_2026-09-16.md`).
- *Ablative teeth:* removing provenance fields makes H4/H6 uncomputable and breaks
  result-granularity disclosure (canary C4, §6).
- *Minimal:* one record type + chain at result granularity subsumes disclosure, claims, and
  retention provenance (decomposition §3.2); no family carries its own provenance mechanism.
- *Audited:* audit protocols v1.2/v1.3 on every corpus (20/20 + 40/40 + 60/60).
- *Inspected:* tier-map / selection-explanation obligations (Charter §5; run journal §5).

**N2 — Supersedes relation + currentness ordering (R + structural strata).** (Admitted on
cross-ecology evidence.)
- *Evidence:* R positive on all five corpora (matrix; consolidation §4 — the one cross-ecology
  survivor, §5); TBII state resolution 54/60 adjudicated vs control 34/60 (c11; consolidation
  §2); P2D B1 best-ever cell 32/40 with M2 85 % (ordering evidence; the P2D *claim* itself stays
  WEAK — footnote S3).
- *Ablative teeth:* A1 (`WM_GEN3_SWEEP=0`) changes ordering/behavior (canary C2, §6);
  direction-aware H3 proposal scoring.
- *Minimal:* one relation kind + deterministic strata (0/1/2, current/unresolved/superseded);
  no dedicated engine.
- *Parameters are statutory, not constitutional:* candidacy rule v1, divisor/floor/budget,
  strata setting (§3).
- *Scope:* admits currentness **ordering**; does not promote the arbitration claim (claim-0003
  stays pending/WEAK).

**N3 — Selection explanations (population → rule → choice).**
- *Evidence:* journal `selection.decision` per recall (`considered`/`selected`/`abstained`/
  `reason`) — H1/H2/H4 computable from artifacts (run journal §3); zero-violation standing.
- *Ablative teeth:* with the fields removed, H4 chain completeness is uncomputable and
  rank/score divergence is no longer auditable.
- *Inspected:* the same events back `inspect` (run journal §5).

**N4 — Journal-as-evidence.**
- *Evidence:* schema pinned in the pre-reg freeze (`PREREG_FREEZE_2026-09-16.md` §2); per-run
  manifest `journal_ok` + `WM_GEN3_JOURNAL_HASH_OUT` linkage; **a broken journal makes a run
  invalid, not silently unmeasured** (run journal, rules 1–2).
- *Ablative teeth:* without the manifest/hash linkage, runs are no longer evidence-joinable; the
  invalidation rule is what keeps the record honest.

**N5 — Audit discipline (wrapper-side ground truth; flags published, never deleted; raw +
adjudicated reporting).**
- *Evidence:* caught a pseudo-gain that raw numbers would have scored as success (HANDOFF §6.3);
  audit flags across corpora; TBII 20/20 + 40/40 and 60/60.
- *Ablative teeth:* without adjudication, known stale-label flags would count as wins (LABEL 16
  on c11; LABEL 6 and LEX_TAU 18 in Phase 2).
- *Protocol versions are statutory* (§3); the discipline (publish flags, never delete; report raw
  and adjudicated) is the earned part.

### 2.2 Conditional lens slot (admitted only as a declared slot)

**C1 — S (semantic projection) as an optional lens.** Entered only under criteria §3.2: a *slot*,
never a mandatory pipeline stage; its activation policy is not general.
- *Pin:* `Qdrant/bge-small-en-v1.5-onnx-Q` snapshot `523982788…`; CLS / L2 / 384-d; brute-force
  cosine; τ = 0.694 (battery-derived; statutory — §3).
- *Activation (scoped, declared, confirmed gate-scoped):* fire when lexical candidates `< 2`, for
  state-resolution questions only (gated3: O₁ recovery 10/10; single-record probes fired with
  zero degradation; CostEfficiency 0.381; ledger claim-0007 validated).
- *Disclosed falsifications carried:* the 0.01 `relevance_floor` as an activation policy
  (gated1 cost bar; gated2 discrimination 0/10) — permanently outside (criteria §3.1); solo
  projection null (P2B claim-0001 falsified; TBII Q2 inert).
- *Not general:* designed-mismatch-regime contribution only (gated2 adjudicated g2 53 vs g0 36).
- *Open boundary:* ≥2-candidate insufficiency (MissedOpportunity₊₂ = 1.000) — named gate,
  outside.
- *Ablative teeth:* count-gate ablation canary C3 (§6).

### 2.3 Compile targets, infrastructure, and contracts — dispositions recorded, not admitted

| Item | Why not a nucleus entry | Where it lives |
|---|---|---|
| Durable store (LMDB, JSONL) | Infrastructure; swappable without re-ratification | criteria §3.4; E1 |
| Retrieval & ranking (Gen2 planners) | Behavior under test; excluded | E2, E3; only the earned subset is N2 |
| Evidence disclosure / abstention machinery | Substrate contract + closure enforcement; constitutional items sit in Part 1; no behavioral ablation | E4; run journal |
| Galaxies / registry | Scope labels and views, not storage machinery | E8; infra |
| Ingestion gates | The `remember` contract; a contract, not a primitive | E9 |
| Continuity / digest | Composition of `recall` + `think` (anti-bloat: recipes, not classes) | E11; canon §7 |
| Claims / belief class + calibration | Compile target; calibration is a statutory statistic; no ablation evidence yet; live product surface remains Gen2 (`link`) | E18 |
| Effects/capability gate · canaries | Constitutional-shell enforcement — Part 1 territory; preserved seams stay Gen2-side | E22; Part 1 |
| PRESERVE→link (16) · EXPERIMENT (4) · RETIRE (4) | Dispositions per criteria §2b — a correct retirement does not become a primitive | §7; decomposition §2 |

### 2.4 Missing-primitive candidates (named, gated, NOT entries)

- **Activation/decay field** with an operational regime parameter — gate: *a task where
  propagation beats retrieval* (E15; theory map §3.3). No temperature parameter until then.
- **Operator vocabulary + recipe runtime** — the anti-bloat law attaches to every candidate;
  SkillForge metadata is not evidence (E16).

## 3. Part 3 — Statutory baseline (Tier 2)

Versioned settings; changeable by authorized external action (operator / release process) without
re-ratifying the constitution. Listed statutes and their recorded values:

| Statute | Value (as recorded) | Source |
|---|---|---|
| Score policy **D2** | idf-weighted query support (Option B); `score ∈ [0,1]`; `<0.01` = essentially no informative support; no per-query/corpus normalization; property-tested | `PHASE1_SCORE_POLICY.md` §5; PREREG §2 |
| Candidacy rule v1 | `candidacy.v1.shared-rare+value-diff+temporal`; rare divisor 20; floor 2; pair budget 200,000; supersede penalty 0.60; recency weight 0.05 | PREREG §2 |
| Projection threshold | τ = 0.694, battery-derived (not benchmark-tuned) | HANDOFF §2; dependency exception receipt |
| Audit protocols | v1.2 (Phase-2 corpora); v1.3 (validated on Testbed II) | HANDOFF §6.3 |
| Invocation pin | `--limit 10 --candidate-limit 100 --min-score 0 --min-coverage 0`; scored T8/T1+T6; guardrails T2/T9 | PREREG §2 |
| Budgets | Fail-closed enforcement at every adaptive boundary (Charter §3.1); thesis +2-session budget | Charter §3.1; PHASE0_RATIFICATION §5 |
| Horizons | Phase-1 import tier fixed `persistent` (replacement unearned); lifecycle rotation principles | E5; Charter §6 |
| Metabolism metric M | Monitor, never a target | METABOLISM_PLAN §3 |
| Dependencies | Dependency manifest; embedding exception as recorded (scope note in receipt) | `DEPENDENCY_MANIFEST.md`; exception receipt |

Runtime switch inventory and defaults:

| Switch | Default | Non-default modes | Status |
|---|---|---|---|
| `WM_GEN3_SWEEP` | on | `0` = A1 ablation (sweep disabled) | statutory ablation surface |
| `WM_GEN3_PROJECTION` | off | `1` = lens on (requires cache) | slot C1 |
| `WM_GEN3_PROJECTION_GATED` | off | `1` = floor gate (**falsified**); `count` = count<2 (**confirmed**) | slot C1 |
| `WM_GEN3_ARBITRATION` | PenaltyMultiplier | `structural` = P2D strata rule | statutory |
| `WM_GEN3_DISPERSION` | off | `1` = P2E dispersion (**falsified**) | rejected; default only |
| `WM_GEN3_EMBED_CACHE` | unset | path (read-only) | pin: §4 |
| `WM_GEN3_JOURNAL` | `<store>/journal.jsonl` (ephemeral) | explicit path | evidence surface N4 |
| `WM_GEN3_JOURNAL_HASH_OUT` | unset | path | manifest linkage N4 |
| `WM_GEN3_DIAG_PAIRS` | unset | test-only diagnostic corpus | not runtime behavior |

## 4. Part 4 — Reproducibility pins

### 4.1 Verified at compilation (byte-identical to their receipt pins, 2026-09-17)

| Artifact | sha256 | Receipt reference |
|---|---|---|
| `docs/CHARTER.md` (v0.1.1) | `957320d9d65dea9fbda9355c43bc8238efc10c9721e3a45239cbe7014a37fa5d` | PHASE0_RATIFICATION §1 |
| `docs/CLOSURE_TESTS.md` (v1.0) | `ad6e3152259b07b3b6f42989e975f84776c1d9bb14d114b3aeba308ee6ca775d` | PHASE0_RATIFICATION §2 |
| Control binary `~/.local/bin/wm` (9.1.7 musl) | `47b5c28e3228a0d5f3b8e733538018d2d40b70bd0beb8f134081335b679621ad` | PHASE0_CONTROL_FREEZE §1 |
| Control tag `v9.1.7` → commit | `94b6420ab982ec1fa8087d12c5824fc4f843869c` | PHASE0_CONTROL_FREEZE §1 |
| MemoraStrict `scenario_seed1–5.json` | `7bebea98924b4ec3e6511b94c0059469b6c625ba4b1aff5b621b6d2c9369621f` · `2da2e2472d76007ee966850af16662ac94ad85593ede67b5edee1b7ee1c334a1` · `3ab6bd9471ce2fe504ea6fe56cbd3c6a507837d251679965810dda6915eb82a3` · `7d140fc0dc53950ac8f68b7eceff36686691dccda26701b419ff34ee6949acdf` · `db84cf3ac6ec923ba03f161c9660f6d03c46ecb4b84b34c3a343207d36b115cc` | PHASE0_CONTROL_FREEZE §2 |
| MemoraStrict `bench_seed1–5.json` | `81c20ee75dbf6bf989f16d47d35171336b2787f32f6a964652b2d6415ed902d3` · `d7772fcbd0ca7e37500ab5ba6b2a86f6c5ec38baf581268a242cc0069d331f7a` · `54a641038bf7f7591a68a647919fe81173a450b9b1967077d5a3f39b873dee44` · `cd3ee051fd598b570715fd997bb0c6633d784ea11f9c8c120dc07580ca9c2b64` · `c026d4687e259ff8ff5aa8d40514a18f280c2ecfdd619d84d72166bc5ae4f450` | PHASE0_CONTROL_FREEZE §2 |
| MemoraStrict `manifest.json` | `051372ab30f99e0e526c8afa17bc08edbe04f9a0779e0d14078f5a67c87384c3` | PHASE0_CONTROL_FREEZE §2 |
| Harness: `memorastrict_bench.py` | `df9d42c24a1005c102e8d99436e7cde37bccc3d8f2958ad4f6659d639c3dc597` | PHASE0_CONTROL_FREEZE §3 |
| Harness: `memorastrict_gen.py` | `17a9db2031bbe091a4282e5de3090182383cc2ef5d40ab76d4783de5209bdabd` | PHASE0_CONTROL_FREEZE §3 |
| Harness: `eval_protocol.py` | `bb3e70b55c38b24ad22e26b87e54d52a51c514c65d336e9194e96b05b9d3b6ff` | PHASE0_CONTROL_FREEZE §3 |
| Embedder snapshot ref | `52398278842ec682c6f32300af41344b1c0b0bb2` | exception receipt §1 |
| `model_optimized.onnx` | `51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431` | exception receipt §1 |
| `tokenizer.json` | `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66` | exception receipt §1 |
| `config.json` | `13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd` | exception receipt §1 |
| `tokenizer_config.json` | `0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53` | exception receipt §1 |
| `special_tokens_map.json` | `5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a` | exception receipt §1 |
| `holdout/MANIFEST.json` (seeds 6–10) | `f43e63921b176690ad2abd97dacf9606c220c087db1477ac626c9ca1407b946e` | P2C_FREEZE §1 |
| `holdout_p2d/MANIFEST.json` (seeds 11–15) | `3b0fecda0af3db9652d02b573973d26cc23b952a91d9fc8ee229dff64e9aad99` | P2D_FREEZE §1 |
| `holdout_p2e/MANIFEST.json` (seeds 16–20) | `1aabef0602e67c6fe737ffa13353a7b6a7f3fafe072c18a7ece8f36c13395b8b` | P2E_FREEZE §1 |
| Claims ledger (`…/wmv9/claims_ledger.json`) | `d94c0cb3d9ebb61ba25a96736931b594844a6a1959c315d0ff388aa380c0e4ed` — live check: `next_id: 8`, 8 claims | LEDGER_RECONSTRUCTION §3 |

### 4.2 First recorded at this compilation (no prior pin)

| Artifact | sha256 / value |
|---|---|
| `experiments/testbed_ii/a/corpus_a/MANIFEST.json` | `4002cb894bf25ca909c63a5cdd4f6460477b4bb6e9655fabd67d4a1a456584d2` |
| `experiments/testbed_ii/gated/corpus_gated/MANIFEST.json` | `1683ddd530378a06a6fd5d0bd6a10fddb92e33ab58f08cd6e98f82baaefd0576` |
| `experiments/testbed_ii/gated2/corpus_gated2/MANIFEST.json` | `fd24cfc7df58f757bf7e9ffcf61712c803a59dba3d6c2183103ee96b0aef05b1` |
| `experiments/testbed_ii/gated3/corpus_gated3/MANIFEST.json` | `f99f6261be6e94b1825333a0466912e2680a5bb9faa309ad3170592d905cd233` |
| `docs/NUCLEUS_FREEZE_CRITERIA.md` (current draft text) | `2d311e08ccb32aad0947163f26e6a33c369f4c7725fdc6f929e735fc41ed773a` |
| `docs/PHASE3_DECOMPOSITION.md` (current text) | `194f081c1e09440706aeb3463270b116947312e0a76f219f20a2d687597d8e79` |
| `HANDOFF.md` (at compilation) | `1e451320ba4bc3e1166635d66bd878f1eb6217728e070acd3172ec7fad702c62` |
| `wm-gen3` release build present at compilation | `b1c66fec53856007d8d42f038ab3a87227fe7a0da53dfa82140ba6621e1ac96d` |

### 4.3 Regenerate at verification (step 2 of the freeze)

1. **Candidate binary** — `cargo build --release --offline` at the freeze tip; hash recorded in
   the receipt; must be the binary every canary runs against.
2. **Counts** — `wm contract --json` from the control binary (302 routes / 70 declared at
   9.1.7; regenerated, never authored); claims ledger live check (8 claims, `next_id: 8`).
3. **Corpus manifests** — full local re-hash pass (the four Testbed II + three holdout
   manifests above; already recomputed once at compilation).

## 5. Verification record (compilation, 2026-09-17)

Findings raised at compilation — disclosed, none silently re-pinned:

- **F1 — Decomposition drift (explained).** The ratified text pin is
  `cb8235e9f8e70583cdc84a18da1efe4b75b216bac6c2b1b00b5b43b81846102a` (verified at commit
  `d59195e`); the current file hashes `194f081c…`. The drift is **additive errata only** —
  status-line pointer to the framing lens, the E4 ancestry inline errata, and the §6 errata
  register — each landed in later commits (`19170bf`, `5b3230d`, `a322cf8`); no verdict text
  changed (`git diff d59195e..HEAD` inspected). The receipt's ratified hash remains the
  reference; the freeze records both hashes.
- **F2 — Freeze-criteria drift (expected).** Receipt-time pin `25573f44…`; current draft
  `2d311e08…` after commit `86ac838` added the two freeze canaries (round-trip; reachable-
  effectful). The file is a draft by its own status line; the current text is pinned here.
- **F3 — Candidate-binary supersession (disclosed).** The HANDOFF-written candidate pin
  `b51112e9…` predates the gated experiments; the build present at compilation is `b1c66fec…`
  (gated3 implementation freeze `bb25c1f`). The freeze pins a fresh rebuild at step 2 (§4.3).
- All other receipt pins recomputed at compilation and matched byte-identically (§4.1).
- **Charter / closure tests / control / corpus / harness / embedder / holdouts / ledger: no
  mismatches.**

**Step-2 verification record (2026-09-17, same session).** Pins regenerated per §4.3:
`cargo build --release --offline` reproduced the binary byte-identically (`b1c66fec…`,
fingerprint-fresh); `wm contract --json` from the control binary regenerated 302 routes /
70 declared; the live claims ledger returned 8 claims with the recorded mapping
(`…/wmv9/claims_ledger.json`, `d94c0cb3…`, `next_id: 8`); the full corpus/manifest/harness
re-hash pass matched §4.1–§4.2. No mismatches.

- **F4 — Duplicate proposals within one sweep (observation, disclosed; not a blocker).**
  `existing` is snapshotted before the pair loop (`crates/wm-gen3-core/src/ops.rs:751`), so one
  endpoint pair is re-proposed once per shared rare token passing the rule — the canary fixture
  produced 5 relations (ids 0–4) on the same `(src=1, dst=0)`; recall applies the last. Direction
  and ordering are unaffected; relation counts are inflated. Flagged for a future registration
  (within-sweep refresh of `existing`, or relation-identity dedup); no verdict, gate, or claim
  changes. Evidence: `receipts/canary_2026-09-17/` (observation O1).

## 6. Canary results (criteria §4.3) — status: ALL PASS (step 3 complete)

| # | Canary | Protects | Result |
|---|---|---|---|
| C1 | Closure canaries (Law + Evidence) | Part 1 enforcement; N1 | **PASS** — static scans pass (`check_closures.sh`); 28/28 tests + 5 doc compile-fail tests; runtime `canary.probe` refused (domains `[Simulated]`), `boundary.refusal` = 1, `closure.violation` = 0 (A1) |
| C2 | R ablation changes ordering | N2 | **PASS** — sweep on: order `[1 stratum 0, 0 stratum 2 superseded_by 4]`; sweep off, fresh store: order `[0 stratum 1, 1 stratum 1]`, zero proposals (A1 vs A2) |
| C3 | Count-gate ablation reverts to declared behaviour | C1 | **PASS** — fired sets by lexical candidates: count `[2→false, 1→true, 0→true]`; floor `[2→false, 1→false, 0→true]`; always-on: no gate events; S-off: projection absent (B cells) |
| C4 | Provenance completeness at result granularity | N1, N3, N4 | **PASS** — `provenance.chain` complete 100 % in all seven runs; zero `closure.violation` |
| C5 | Round-trip relation kinds/endpoints | N2 | **PASS** — fresh process on the same store: `inspect` relations byte-identical (`kind: Supersedes`, `src: 1`, `dst: 0`, `state: Candidate`); recall still applies `superseded_by: 4` (A3) |
| C6 | Reachable-effectful acceptance | all admitted entries | **PASS** — verb → journal-visible effect inventory complete (remember → `ingest.batch`; think → `think.sweep`/`relation.proposed`; recall → `selection.decision`/`provenance.chain`; inspect → tier map; canary → `boundary.refusal`; lens → `projection.gate`) |

**Evidence bundle:** `receipts/canary_2026-09-17/` — `SUMMARY.md` (results, observations O1–O3,
reproduction commands), journals + responses + fixtures + drivers, `ENVIRONMENT.txt`, and
`SHA256SUMS` (sha256 `941abc8076ab504568b879a914aafc95975471c7f94f8d13a38b8553cf160790`); every
journal's hash-out file matches its recomputed sha256. All six canaries passed on the frozen
binary; no canary failed, so nothing blocks the freeze on §6 grounds. Observations O1–O3 are
disclosed in the bundle and §5 (F4); none changes a verdict, gate, or claim.

## 7. Beside the snapshot — frozen historical record (not nucleus)

Dispositions, errata, and findings live beside the snapshot (criteria §2b, §3.3). Their
correctness adds no nucleus entries.

| Artifact | sha256 |
|---|---|
| `receipts/PHASE3_COMPILE_PASS_2026-09-17.md` (ratified compile pass) | `9f295a0b45fe548065a9f53f7cc7be6e1bcaa17c85485bb6bff3863c2e0d20a8` |
| `receipts/PHASE3_ENTRY_DECISION_2026-09-17.md` | `0edd9793de8eae27dad68dca0e0eff2e51aa3d1ead7443ec29d9377104d0684e` |
| `receipts/LEDGER_RECONSTRUCTION_2026-09-17.md` | `303227ca417219f1d9bd9d56402d705583a73e965823d201f23e6a10a179c926` |
| `receipts/PREREG_FREEZE_2026-09-16.md` | `d92561a6008b113acbcd73a19d4b35816ad259b7772b13195f8a8d15e8ee0b08` |
| `receipts/PHASE0_CONTROL_FREEZE_v9.1.7_2026-09-16.md` | `c9dcfe3b86286f86963ec99a5d4aaff7af9193f464ce4066ac50b845e068d681` |
| `receipts/PHASE0_RATIFICATION_v0.1.1_2026-09-16.md` | `873400c441f43dd9b9b5df0604c131ff9bb08b69ae39f43d8e24c84e5e33aa8a` |
| `receipts/DEPENDENCY_EXCEPTION_EMBEDDINGS_2026-09-16.md` | `331f306ac03b39cb7e4b460558386b77381b41edca8e46f254ef8198de13d2f1` |

Also beside the snapshot (unhashed here; pinned in their own receipts): the Phase-3 decomposition
with errata (§6 register), `PHASE4_ERRATA.md` (30 items A–G), the wave findings W0–W3 + masters,
`WAVE_EXTRACTION_PROTOCOL.md`, and the experiment reports named in §4.

## 8. Scope footnotes — what this snapshot does NOT claim

- **S1 — No general semantic bridge.** T8 cross-vocabulary bridging is rejected as a primitive
  (claims 0000/0001 lineage); the control's T8 advantage is hand-authored enrichment.
- **S2 — No general activation policy.** The count gate is gate-scoped; the ≥2-candidate
  boundary is unresolved (MissedOpportunity₊₂ = 1.000); the 0.01 floor is permanently outside
  (criteria §3.1); S remains a slot, not a stage.
- **S3 — The arbitration claim stays WEAK.** claim-0003 is pending; nothing here promotes it.
- **S4 — Open boundaries stay outside:** TIE dynamics, projection-agreement ordering, multi-view
  selection, field dynamics, Gardens/Engines recipes, Geneseed/inheritance, the deferred
  representation stack — each has a named gate; none enter by proximity.
- **S5 — No new invariants.** Ten is the set; amendment only via Charter §4.
- **S6 — Statutes are not constitutional identity.** τ, D2, switches, protocol versions change
  by authorized external action.
- **S7 — Pins are anchors, not capabilities.** Regenerated when a constituent changes; a
  mismatch is a finding, not a re-pin.
- **S8 — The freeze certifies the snapshot only.** Dispositions/errata (§7) are history.
- **S9 — Nothing re-litigates falsified claims.** WEAK stays WEAK.
- **S10 — The ceremony is bounded.** Fail-closed budget rules apply to the freeze itself.

## 9. Freeze block (to complete)

- [x] **Step 2** — pins regenerated and recorded (binary rebuild `b1c66fec…`, counts 302/70,
      live ledger check 8/8) — §4.3; verification record in §5
- [x] **Step 3** — canaries C1–C6 run; all PASS; evidence bundle
      `receipts/canary_2026-09-17/` — §6
- [ ] **Step 4** — operator ratification (signature below)
- [ ] **Step 5** — receipt landed: `receipts/NUCLEUS_FREEZE_<date>.md` (artefact hash + verified
      pins + session attestation)

Operator signature: ______________________  Date: ____________

**Amendment rule** (criteria §5): proposal → canary demonstration → operator ratification →
receipt; additive history, no emergency suspension. The next amendment should come from an
experiment breaking a nucleus entry, not from design prose.
