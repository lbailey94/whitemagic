# WhiteMagic Evolution Expedition: Gen1 → Gen2 → Gen3
**Living Research Document & Comparative Study**
*Created: 2026-09-17*

---

## Executive Summary & Narrative Arc

WhiteMagic's evolution is not a sequence of rewrites; it is an organism undergoing natural selection:
1. **Gen1 (v0.1.0-beta → v26.0.3, Nov 2025 – Aug 2026)**: The *Phenotype Explosion / Cambrian Era*. Explored an enormous capability space (875 dispatch entries, 47 galaxy databases, 31 garden directories, 28 canonical engines, autonomous background daemon). Failed its own load test across five catastrophes.
2. **Gen2 (v3 blueprint → v9.1.8 / v9.1.9, Aug 2026 – Present)**: The *Constitutional Era*. Transformed Gen1's catastrophes into enforceable laws of physics (write gates, canaries, Landlock LSM sandboxing, Firebreak, delete-confirm law, Yama budgets, contract-asserted route manifests). Rebuilt in Rust across 15 crates with an LMDB/Tantivy unified store.
3. **Gen3 (v0.1.0-alpha, Sep 2026 – Future)**: The *Generative Synthesis*. Emergence under mechanized selection inside constitutional constraints. Instead of hardcoding 28 Garden and 28 Engine classes, Gardens become *boundary conditions / prior basis states* and Engines become *compiled DAGs of general primitives* over a dynamic cognitive field. Governed by two inviolable closures: **Law Closure** and **Evidence Closure**.

---

## Part 1: Archaeology of Gen1 (v26.0.3 Baroque Monolith)

### 1.1 Structural Inventory
* **Codebase Scale**: 72 top-level Python packages in `core/whitemagic`, 2,420 `.py` files, ~618,000 LOC.
* **The Reachability Discrepancy**:
  * AST-verified dispatch table: **875 tool entries** (`whitemagic/tools/dispatch_table.py`).
  * Default reachable surface: Only **~156 tools** in Lite mode (128 core + 28 Gana meta-tools).
  * Extreme compression mode: Seed mode (1 single `wm` meta-tool).
* **Engine Consolidation in late Gen1**:
  * Manifest in `core/engines/registry.py` organized 28 Lunar Mansion engines.
  * Late Gen1 had already started consolidating its own sprawl: 28 canonical slots absorbed 44 older sub-engines (e.g. `ExportEngine` absorbed `CodeGenomeEngine`, `PromptEngine`, and `PolymorphismEngine`; `ConsolidationEngine` absorbed `ReconsolidationEngine`, `_PyReplayEngine`, and `RetentionEngine`).
* **The Gardens & The `GardenRouter`**:
  * 31 individual garden directories (`whitemagic/gardens/`), each inheriting from `BaseGarden` with 4D holographic coordinate biases (Logic $\leftrightarrow$ Emotion, Micro $\leftrightarrow$ Macro, Past $\leftrightarrow$ Future, Importance).
  * **The Hidden Gem (`core/evolution/garden_router.py`)**: A 5-regime improvement router with explicit Bayesian priors and Brier score calibration:
    * *Courage*: High-risk architectural changes (prior mean 0.5, variance 0.2, confidence threshold 0.7, $1.5\times$ Monte Carlo trials).
    * *Wisdom*: Reliable knowledge organization (prior mean 0.8, variance 0.05, low variance).
    * *Play*: High-novelty experimental features (prior mean 0.4, variance 0.25, $2.0\times$ trials).
    * *Grief*: Debt reduction, deprecation, cleanup (prior mean 0.7, variance 0.08).
    * *Mystery*: Unknown-unknown exploration (prior mean 0.3, variance 0.3, $2.5\times$ trials).
* **Storage Fragmentation**:
  * 46 separate SQLite database directories under `users/local/galaxies/` (e.g. `codex/whitemagic.db` is 2.6 GB; `sessions/whitemagic.db` is 716 MB). Each maintaining WAL/SHM files, leading to file descriptor exhaustion.

### 1.2 The Five Catastrophes → Constitutional Laws

| # | Gen1 Catastrophe | Date | Root Cause in Gen1 Code | Resulting Constitutional Law (Gen2/Gen3) |
|---|---|---|---|---|
| 1 | **$O(N^2)$ Blackout** | Jan 15, 2026 | Ingestion hit 276,501 memories; unindexed all-pairs distance matrix ($3.8 \times 10^{10}$ ops) starved CPU and corrupted SQLite. | **Spatial Hashing & Write Gates**: Bounded complexity, ingestion rate floors, and bounded range queries. |
| 2 | **The No-Op Store** | Apr 21, 2026 | `MemoryManager.store()` was a literal `pass` for weeks while docs and marketing claimed full 5D coordinates and galactic mapping. | **Canary Testing & Verifiable Receipts**: Tests attached to invariants, golden suites, and runtime proof over documentation claims. |
| 3 | **The 54k Mass Deletion** | Jul 13, 2026 | Dual-backend routing bug leaked 54,192 session memories; an agent ran an unconfirmed bulk delete. | **Delete-Confirm Law & Bulk Scope**: Destructive routes strictly confirm-gated, audited with confirm tokens, and bounded by bulk-scope laws. |
| 4 | **The Runaway Daemon** | Aug 1, 2026 | `run_mcp_lean.py` ran headless: 2.4 GB RSS, 110% CPU, 4-tier consciousness loop (30s–1800s) with 15 feature flags defaulting to True, and 284 zombie dream loops generating `random.uniform(0.7, 0.98)` novelty. Deadlocked on SIGTERM. | **Firebreak, Yama Budgets, & Daemon Separation**: Separation of daemon loops from request paths; hard resource budgets; homeostatic kill switches. |
| 5 | **The `rm -rf` Wipe** | Aug 24, 2026 | Unsandboxed shell command destroyed legacy store; no verified backups existed. | **Landlock LSM Sandbox & Mandatory Backup Drills**: Kernel-level filesystem containment + automated nightly backup restoration verification. |

---

## Part 2: Gen2 (WMv9 v9.1.8 / v9.1.9) — The Constitutional Fortress

*(To be updated during Phase B review)*
## Part 2: Gen2 (WMv9 v9.1.8 / v9.1.9) — The Constitutional Fortress

### 2.1 The Architectural Paradigm Shift
Where Gen1 attempted to solve reliability by adding more Python classes, Gen2 converted failures into structural constraints built in Rust (15 native crates, 253k LOC):
* **Separation of Powers**: Autonomous daemon cycles are completely severed from the request dispatch path. A tool invocation never risks triggering a recursive background loop.
* **Unified Storage Substrate (`wm-memory`)**:
  * Replaced 46 per-galaxy SQLite databases with a single, highly performant **LMDB environment** (zero-copy memory-mapped transactions) and a parallel **Tantivy full-text index** (BM25 scoring).
  * Storage is partitioned logically via 16 `Galaxy` enums (11 active memory galaxies) rather than physically scattered across the filesystem.
  * Explicit **cold storage rotation**: two-phase, fail-closed rotation-not-deletion.
* **Kernel & Process Governance (`wm-governance` & `wm-dispatch`)**:
  * **Landlock LSM Sandbox**: Kernel-enforced filesystem sandboxing (v0 whole-process, v1 per-tool scoped threads) prevents unauthorized file touches or `rm -rf` disasters.
  * **Firebreak**: Armed by default in dispatch; inspects AST/patterns for 31 forbidden, 13 dangerous, and 8 caution commands.
  * **Delete-Confirm Law**: 10 destructive routes require explicit confirmation tokens and respect bulk-scope boundaries.
  * **Yama Budgets**: Dynamically allocates write, spawn, and network budgets scaled against host health.
  * **Karma Ledger**: SHA-256 hash chain with Merkle tree checkpoints for tamper-evident provenance.
* **The Epistemic Interface**:
  * **Explicit Abstention**: When retrieval confidence falls below trust floors, the engine returns `status: insufficient_evidence` and `reason: no_results_above_floors` instead of hallucinating answers.
  * **Evidence Bundles**: Results carry provenance metadata (representation, truncation state, exact-read availability, revision state, integrity hash, source-time basis).
* **The Capability Funnel ($303 \rightarrow 61 \rightarrow 9 \rightarrow 1$)**:
  * 303 registered routes in machine manifest (`route-schema-manifest.json`).
  * Curated down to 61 routes in the default profile.
  * Exposed to standard MCP clients as **9 tools/list handles** (`wm`, `memory.create`, `memory.search`, `memory.read`, `memory.list`, `memory.hybrid_recall`, `session.record`, `session.continuity`, `session.start`).
  * 1 single adaptive `wm` meta-router with TF-IDF, embedding-based, and OATS routing.

### 2.2 Recent Hardening & The 9.1.9 Invariants (Frozen Tonight)
The commit log leading to the morning v9.1.9 release demonstrates intense operational discipline:
* **F3 (Coordination Truth)**: `code.*` resolves git common directory via pure filesystem traversal rather than spawning `git rev-parse`, avoiding undeclared spawn effects and Yama budget deductions.
* **F4 (Release Tooling)**: Orchestrates and verifies all 5 release channels (GitHub assets, crates.io, npm, Docker, MCP registry) through `release-health` reconciliation.
* **F5 (Continuity Handoff)**: `session.continuity` surfaces the checkpoint handoff (`next_queue`, `open_flags`, `tests_green`, `lease_id`), ensuring handoff state is not write-only.
* **F6 (CLI Parity)**: CLI session commands auto-initialize explicit stores and attach the Tantivy index at write time, eliminating the phantom index drift warning on fresh runs.
* **F7 (First-Run Polish)**: `wm grimoire` release network probe timeout cut from 5.0 s to 1.2 s; aggregate readiness renamed to `environment_ok`.
* **F8 (Help Surface)**: `wm --help` displays clean product commands by default; research/lab tools moved to `wm help --all`.
* **F9 (Recovery Hardening)**:
  * `wm restore` non-blocking writer-lock check guarantees `--force` can never overwrite a live server's active store.
  * Broken or unopenable Tantivy indexes are quarantined to `<index>.corrupt.<ts>` and automatically rebuilt from canonical LMDB via `wm reindex` / `wm doctor --repair`.
* **F10 (Onboarding Truth)**: `wm connect` performs entry-level reconciliation (repairing stale `--readonly` flags without duplicate backups); `wm setup <client> --remove` cleanly de-provisions WhiteMagic entries.
* **F11 (Content Admission Gates)**: Refuses empty, whitespace, NUL, and control-character debris; requires non-blank session titles; detects and skips binary payloads during ingest.
* **F12 (Calm Surfaces)**: Fresh installs report `state: "not_initialized"` instead of `DEGRADED`; `wm config --sample` defaults to minimal product configuration.

---

## Part 3: Gen3 — The Generative Synthesis

## Part 3: Gen3 — The Generative Synthesis (Discernment)

### 3.1 The Thesis & The Triad
The evolutionary journey across the three generations has crystallized into a single progression:
$$\text{Gen1 Discovery} \longrightarrow \text{Gen2 Selection/Consolidation} \longrightarrow \text{Gen3 Discernment}$$

The governing mnemonic remains:
> *Law constrains. Evidence grounds. Metabolism opens. Selection shapes. Provenance credits. Structure emerges.*

In Gen3, the system does not instantiate bespoke classes for every cognitive metaphor. Instead, it operates as a **constitutionally governed adaptive substrate** where:
* Evidence, belief, and speculation remain epistemically distinct.
* Cognition is expressed through a minimal basis of general operations (`remember`, `recall`, `think`, `inspect`) over a dynamic field.
* Higher-order structures (relations, constellations, emergent galaxies) form, compete, and dissolve through bounded exploration and outcome-anchored selection.

### 3.2 The Two Closures in Code (`crates/wm-gen3-core`)
Gen3 anchors its safety and integrity in two machine-verified closures tested via type-level `compile_fail` doctests and static scans:
1. **Law Closure (`constitution.rs`)**:
   * *Adaptive state cannot write constitutional state.*
   * The plastic layer receives only an owned, immutable [`ConstitutionView`](file:///home/lucas/Desktop/WMgen3/crates/wm-gen3-core/src/constitution.rs#L55-L86) with private fields and zero setters.
   * Mutation is restricted exclusively to `Constitution::apply(&mut self, amendment)`, requiring an external authority token. Every change emits a tamper-evident [`AmendmentReceipt`](file:///home/lucas/Desktop/WMgen3/crates/wm-gen3-core/src/constitution.rs#L95-L100).
2. **Evidence Closure (`evidence.rs`)**:
   * *Inference alone cannot create world-evidence.*
   * Every [`EvidenceRecord`](file:///home/lucas/Desktop/WMgen3/crates/wm-gen3-core/src/evidence.rs#L56-L109) has an immutable [`Domain`](file:///home/lucas/Desktop/WMgen3/crates/wm-gen3-core/src/evidence.rs#L16-L26) (`World`, `System`, `Simulated`, `Reported`) with zero setters or re-label paths.
   * `World` evidence can only be minted through a private `RatifiedChannel` capability token.
   * Communication events (testimony) can record the *act* as `World`, but the *content* remains `Reported`. Simulation and dreaming can *never* launder their outputs into world facts.

### 3.3 Dynamic Field & The Minimal Operations (`field.rs` & `ops.rs`)
* **Field Relations**: Minimal edges $e = (w, s, c, t)$ representing weight, sign, cost, and trust. All relations are classed as [`RelationEpistemic::Speculation`](file:///home/lucas/Desktop/WMgen3/crates/wm-gen3-core/src/field.rs#L29-L32) (claims *about* records, never world-evidence).
* **Four General Operations**:
  * `remember`: Ingests and persists evidence, beliefs, and speculations under strict admission gates (rejecting noise, duplicates, and unratified world claims).
  * `recall`: Retrieves candidate records with structural arbitration (current $\rightarrow$ unresolved $\rightarrow$ superseded strata) and scope label filtering.
  * `think`: Executes relation sweeps (candidacy, supersession, analogies) bounded by pair budgets.
  * `inspect`: Read-only introspection exposing constitutional views, active policies, and journaled selection records.
* **Scope Labels vs Physical Galaxies**: Rather than maintaining 46 open SQLite databases as in Gen1, Gen3 represents galaxies and compartments as **scope views over a single store** (`corpus:<label>:<tags>`), eliminating file descriptor exhaustion while maintaining clean namespace boundaries.

### 3.4 Scored Experimental Findings: The Practice of "Let Gen3 Lose"
Phase 2 put Gen3 through rigorous, pre-registered adversarial A/B experiments against the frozen Gen2 control:
* **GEN3-P2-CONTRADICTION-001 (Phase 2 A/B)**:
  * **Result**: **LOSS** (T8 0/15, T1/T6 20/40 vs Control 15/15 and 40/40).
  * In accordance with pre-registered criteria, `claim-0000` was immediately marked **falsified** in the ledger.
  * **Diagnoses**:
    * *F1 (Semantic Bridge)*: Control advantage was driven by hand-authored benchmark-relevant enrichment (`wm-memory/src/enrichment.rs`), not an innate contradiction primitive.
    * *F2 (Candidacy Precision)*: 89.7% recall, but 1.06% precision (~85 noise relations per true pair).
    * *Invariants Upheld*: H4 Provenance achieved **100% (3,221/3,221)**; H6 Violations achieved **0 closure violations**.
* **Successor Experiments (P2B, P2C, P2D, P2E)**:
  * Tested semantic projection vectors, structural arbitration, and entropy dispersion.
  * Claims `claim-0001`, `claim-0002`, and `claim-0004` were systematically scored against holdout seeds and resolved as **falsified** when falling short of pre-registered thresholds.
  * **Epistemic Discipline**: Parameters were never retuned post-hoc; goalposts were never moved. As noted in the receipts: *"WEAK stays WEAK."*

### 3.5 Phase 4 Synthesis Map & The Anti-Bloat Law (`PHASE4_SYNTHESIS_MAP.md`)
The recent synthesis map (`528047e`) mapped 25 function families across all three generations:
* **The "10-Line Replacement" Principle**: If a capability can be expressed as a short composition over verbs (`remember`, `recall`, `think`, `inspect`), records, relations, and the journal, **no new class or module is permitted**.
  * Examples: Continuity digests, checkpoint handoffs, recall scope views, retention decay, claims resolution, and inspect answers are all short compositions over the existing nucleus.
* **Only 4 Missing-Primitive Candidates Survive**:
  1. *Activation/decay field with an operational regime parameter* (gated on a task where propagation beats retrieval).
  2. *Operator vocabulary + recipe runtime* (gated on anti-bloat review).
  3. *Selection policy layer* (Pareto/statutory + exploration budget).
  4. *Credit assignment* (traceable participation, delayed statutory horizon; co-occurrence permanently ineligible).
* Everything else compiles directly into the existing Gen3 nucleus basis. No further primitive demand was identified across the entire extracted Gen1/Gen2 corpus.

---

## Part 4: Live Website Audit (whitemagic.dev) & Recommendations

### 4.1 Current Live State Assessment (Post-9.1.8)
The live website at `whitemagic.dev` already embodies the epistemic transformation outlined in the ChatGPT journals:
1. **Clear Hero & Immediate Utility**:
   * States the mission plainly: *"We study how AI agents remember, resume, coordinate and recover across long-running work. WhiteMagic is our open-source, local-first continuity substrate for AI agents."*
   * One-line install command placed immediately below the hero without an ideological manifesto preceding it.
2. **"The Simplest Proof"**:
   * Demonstrates the core value proposition: *"Monday's decision, recovered on Thursday."*
3. **Four Research Programs with Honest Standings**:
   * `OBSERVED`: Continuity in Shipped Software.
   * `EXPERIMENTAL`: Governed Agency.
   * `PROPOSED`: Multi-Agent Continuity.
   * `PROPOSED`: Evaluation Methodology.
4. **Epistemic Badges & Separation of Claims**:
   * The `/research` page explicitly defines its epistemic badges (**Measured**, **Observed**, **Hypothesis**, **Research goal**).
   * Working hypotheses (e.g. idle maintenance, adversarial review before dispatch, vocabulary compression) are segregated from product claims.
5. **Calm, Transparent Data Policy**:
   * Explicit disclosure: store under home directory, no remote memory transmission, local diagnostic telemetry display-only by default, update checks offline-tolerant.

### 4.2 High-Impact Recommendations for Upcoming Iterations
* **Synchronize Release Facts Automatically**:
  * With v9.1.9 launching in the morning, ensure CI release automation (`release.yml` / `version_truth.py`) updates website release badges (`v9.1.9`, release date, test counts) simultaneously across all pages (`/`, `/whitemagic`, `/about`, `llms.txt`).
* **Add Visual Code/Terminal Evidence Cards**:
  * On `/whitemagic`, consider adding collapsible or tabbed terminal snippets demonstrating:
    1. A `wm grimoire` output showing the 5 distinct readiness facts.
    2. A quick conversational example of `session.continuity` recovering a decision.
    3. An evidence bundle JSON snippet illustrating provenance and trust floors.
* **Bridge to Gen3 Research**:
  * Once the Phase 2 Contradiction Experiment results from Gen3 are finalized, feature a concise technical report under `/research` titled *"Evaluating Adaptive Field Cognition vs Hardened Constitutional Invariants"*, demonstrating the lab's willingness to publish both wins and losses.
