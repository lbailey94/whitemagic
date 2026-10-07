<!-- Extracted from Antigravity CLI session 221fbb57-905f-4e7d-a4d3-3c11810ea0b7
     message b7eb609f-7456-4d77-8693-8dc44e174dea | sender 2a1da743-b3a7-4fec-89b7-e1eb4c872556 | 2026-09-19T01:37:53.363280086Z
     Original title: Message from Geneseed and Phylogenetics Scout (research)
     Extracted 2026-09-21 by opencode; content unmodified. -->

# Research Report: Codegenome, Geneseed Vault, and Digital Phylogenetics (Gen1 → Gen2 → Gen3)

**Recipient**: parent (`221fbb57-905f-4e7d-a4d3-3c11810ea0b7`)  
**Investigator**: Research Subagent  
**Scope**: Evolutionary archaeology and design analysis across Gen1 (v26), Gen2 (WMv9), and Gen3 (`WMgen3`).

---

## 1. Gen1's Codegenome Vault and Engine

### 1.1 Architecture & Component Division
In Gen1 (`v26.0.3`), code templating, mutation, and evaluation were partitioned into two layers:
- **`CodeGenomeEngine`** (`og_whitemagic/.../codegenome/engine.py`, 1,776 lines): Core template catalog, YAML persistence loader, variable substitutor, and forking manager.
- **`GeneseedVault`** (`og_whitemagic/.../codegenome/vault.py`, 502 lines): High-level lifecycle interface wrapping the engine. Managed natural-language vibe prompts (`vibe_parser.py`), coordinated stochastic polymorphism, executed AST/security validation (`validator.py`), tracked usage analytics, and emitted Gan Ying resonance audit events (`geneseed.render`, `geneseed.fork`, `geneseed.deprecated`, `geneseed.signed`).
- **Dispatch Seam**: Exposed via tools `codegenome.generate`, `codegenome.list`, `codegenome.fork`, and `codegenome.status` through `handlers/codegenome.py`.

### 1.2 Template Representation (`CodeTemplate`)
Templates were represented by the `CodeTemplate` dataclass (`engine.py:80-101`) loaded from built-ins (`_BUILTIN_TEMPLATES`) or YAML files in `$WM_STATE_ROOT/codegenome/`:
- `name: str`: Unique template identifier.
- `version: int`: Incremented monotonically upon forking (starts at 1).
- `default: str`: Primary code template with Jinja-style `{{var}}` variable slots and recursive `{{include:template,var=val}}` directives (nested up to 10 levels with cycle detection).
- `tier_variants: dict[str, str]`: Tactical variants mapped to martial/elemental tiers:
  - `xianfeng` (Scout / Vanguard): Minimal, fast, lightweight implementation.
  - `wei_wuzu` (Infantry / Standard): Intermediate implementation with TODO scaffolding.
  - `huben` (Imperial Guard / Heavy): Full production-grade, async, dependency-injected implementation.
- `variables: list[str]`, `dependencies: list[str]`, `signature: str`, `tags: list[str]`.
- `parent_id: str`: **Lineage anchor** — stores the name string of the ancestor template.
- `success_rate: float`: Rolling empirical success score (default `1.0`).
- `deprecated: bool`: Auto-flagged when success rate dropped below threshold (default `False`).
- `content_hash: str` & `signature_key: str`: SHA-256 hash of template content signed via Ed25519 (`AuditSigner`).
- `files: list[dict[str, Any]]`: Multi-file manifest for composite project generation.

### 1.3 Forking Mechanism (`parent_id`)
Forking was implemented in `CodeTemplate.fork(new_name, body_delta)` (`engine.py:187-206`):
```python
child = CodeTemplate(
    name=new_name,
    description=f"Forked from {self.name}: {self.description}",
    version=self.version + 1,
    default=body_delta or self.default,
    tier_variants=dict(self.tier_variants),
    variables=list(self.variables),
    dependencies=list(self.dependencies),
    signature=self.signature,
    tags=list(self.tags),
    parent_id=self.name,     # Lineage: parent name string
    success_rate=1.0,        # Reset fitness for the child
    source="forked",
    files=list(self.files) if self.files else [],
)
child = _sign_template(child)  # Ed25519 signature
```
`GeneseedVault.fork(parent_name, new_name, body_delta)` (`vault.py:430-454`) invoked `engine.fork_template()`, stored the child in memory, and emitted a Gan Ying resonance event:
```python
_emit_gan_ying("geneseed.fork", {"parent": parent_name, "child": new_name, "version": child.version})
```
*Crucial archaeological finding*: Lineage in Gen1 was tracked purely as a string name (`parent_id: str`), not as a relational graph edge in a durable knowledge base.

### 1.4 Mutation Mechanisms
Gen1 employed two complementary mutation mechanisms:

1. **Stochastic Variation (`PolymorphismEngine` in `polymorphism.py`, 224 lines)**:
   Activated when `vibe_render(..., polymorph=True)` was called:
   - **Variable/Function Name Mangling**: Used a synonym lookup table (`_SYNONYMS`) targeting common verb prefixes (`get` → `fetch`/`retrieve`/`obtain`; `create` → `make`/`build`/`generate`; `delete` → `purge`/`drop`/`destroy`; `validate` → `check`/`verify`/`guard`).
   - **AST-Safe Import Shuffling**: Reordered non-`__future__` import statements to alter file layout without breaking execution.
   - **Control Flow Equivalence Transforms**: Regex transforms between ternary expressions and `if/else` blocks (`_ternary_to_if_else`, `_if_else_to_ternary`), and range-for loops to while loops (`_for_to_while`).
   - **Comment/Docstring Style Rotation**: Cycled docstring conventions across `google`, `numpy`, `sphinx`, and `rest`.
   - **Junk Code / No-Op Injection**: Inserted no-ops (`pass  # type: ignore`, `_ = None`, `T = type('T', (), {})`) for mutation testing and obfuscation.

2. **LLM-Guided Refinement (`vault.py:141-254`)**:
   `generate_with_llm(prompt, repo_path, write_output)`:
   - Rendered base template code.
   - Mined git patterns from `repo_path` via Rust accelerator `mine_geneseed_patterns(repo_path, 0.3, 50)`.
   - Injected mined patterns and base code into `LocalLLM` constrained by context-free grammar `PYTHON_CODE_GRAMMAR`.
   - Dispatched the resulting code to the parallel `CodeWritingClone` (`rust_code_writing.py`) to execute filesystem edits.

### 1.5 Evaluation & Selection (`success_rate`)
Fitness evaluation was tracked by `GeneseedVault.record_outcome` (`vault.py:298-354`):
- **Exponential Moving Average (EMA)**:
  $$\text{success\_rate}_{t} = (1 - \alpha) \cdot \text{success\_rate}_{t-1} + \alpha \cdot \text{obs}$$
  where $\alpha = 0.1$ (`_EMA_ALPHA`), and $\text{obs} = 1.0$ if `success` else $0.0$.
- **Automated Deprecation**:
  - `_DEPRECATION_THRESHOLD = 0.3`.
  - If $\text{success\_rate} < 0.3$: sets `template.deprecated = True` and emits `geneseed.deprecated` event.
  - If subsequent successful runs lift $\text{success\_rate} \ge 0.3$: auto-un-deprecates.
- **Persistence**: Serialized to `$WM_ROOT/codegenome/usage_stats.json`.
- **Selection Pressure on Retrieval**:
  - Ambiguous queries scored suggestions via:
    $$\text{Score} = \text{success\_rate} \times |\text{query\_keywords} \cap \text{template\_tags}|$$
  - Deprecated templates were excluded from suggestions and prompted runtime warnings if explicitly invoked.

---

## 2. Git Mining Heuristics in `geneseed_miner.rs`

### 2.1 Extraction Pipeline
In Gen1 (`og_whitemagic/core/whitemagic-rust/src/geneseed_miner.rs`, 408 lines), the PyO3 module executed:
```bash
git log --max-count={max_commits} --pretty=format:%H|%an|%at|%s --numstat
```
- Headers were extracted via `line.splitn(4, '|')` $\rightarrow$ `(commit_hash, author, unix_timestamp, message)`.
- Numerical diff stats were parsed from tab-delimited numstat lines $\rightarrow$ accumulated `lines_added`, `lines_removed`, and `files_changed`.

### 2.2 Classification Heuristic (`classify_commit`, lines 335–373)
Case-insensitive substring search on commit messages determined the pattern category and `base_confidence`:
1. **`performance`** (contains `perf`, `optim`, `speed`, `faster`, or `cache`) $\rightarrow \text{base\_confidence} = 0.8$.
2. **`refactor`** (contains `refactor`, `cleanup`, or `simplify`) $\rightarrow \text{base\_confidence} = 0.6$.
3. **`bugfix`** (contains `fix`, `bug`, or `issue`) $\rightarrow \text{base\_confidence} = 0.5$.
4. **`feature`** (contains `feat`, `add`, or `implement`) $\rightarrow \text{base\_confidence} = 0.4$.
5. **Unmatched** $\rightarrow$ discarded (`return None`).

### 2.3 Longevity Calculation (lines 347, 375)
The age of the commit in days relative to current execution time:
$$\text{longevity\_days} = \left\lfloor \frac{\text{now\_timestamp} - \text{commit\_timestamp}}{86400} \right\rfloor$$
The longevity boost rewarded surviving code (code that had not been quickly reverted or replaced):
$$\text{longevity\_boost} = \min\left(0.2, \; \frac{\text{longevity\_days}}{365.0}\right)$$
*Commits aged 1 year or older received the maximum boost of $+0.20$.*

### 2.4 Diff Size Factor (lines 377–386)
Total churn $\text{total\_changes} = \text{lines\_added} + \text{lines\_removed}$:
- $\text{total\_changes} < 10$: `0.9` (trivial/noisy change penalty)
- $10 \le \text{total\_changes} < 100$: `1.1` (atomic, focused refactor/optimization bonus)
- $100 \le \text{total\_changes} < 500$: `1.0` (standard commit)
- $\text{total\_changes} \ge 500$: `0.8` (large churn / monolithic blast radius penalty)

### 2.5 Total Confidence Formula (line 388)
$$\text{confidence} = (\text{base\_confidence} + \text{longevity\_boost}) \times \text{size\_factor}$$
If $\text{confidence} < \text{min\_confidence}$, the commit was discarded.  
Mined patterns received an ID formatted as: `format!("{}_{}", pattern_type, &commit_hash[..8])`.

---

## 3. Why Gen2's Port Failed True Digital Phylogenetics

In Gen2 (`crates/wm-tools/src/expansion/geneseed.rs`, 611 lines), the Rust miner was ported to native Rust. However, as documented by codebase archaeology and Gen3 findings (`W3_geneseed.md`, `LINEAGE_LEDGER.md`):

1. **External Git Descent $\neq$ Internal Cognitive Phylogenetics**:
   - The tool merely parsed human git commits from an external filesystem repository. It did not track the evolutionary lineage of the agent’s internal memories, heuristics, prompt structures, or reasoning traces.
2. **Flat String Tags, Zero Graph Edges**:
   - `store_patterns_in_vault()` (`geneseed.rs:341-388`) ingested patterns into LMDB (`Galaxy::Codex` / `Galaxy::Research`) as plain `Memory` structs with string tags:
     `tags = ["geneseed:pattern", "pattern_type:performance", "commit:abcdef12", "longevity:90d"]`.
   - **No parent pointers, no DAG edges, and no typed relations** (`derived_from`, `supersedes`) were constructed between records.
3. **Absence of Selection Pressure & Fitness Testing**:
   - Mined patterns were static, write-once records. There was no feedback loop, no empirical validation, no Brier score calibration, and no mechanism for patterns to reproduce, mutate, compete, or go extinct based on operational utility.
4. **Abandonment of the Template Vault**:
   - Gen2 dropped Gen1’s `GeneseedVault` and `CodeTemplate` engine entirely. The string-based `parent_id` forking and the EMA deprecation loop were discarded.
5. **Dormant and Undeclared Organ**:
   - Registered as `geneseed.mine` and `geneseed.stats`, both tools were flagged `declared: false` in `route-schema-manifest.json` (0 daemon or cognitive cycle callers).
   - In `LINEAGE_LEDGER.md:51`, the digital genetics row was explicitly marked **"missing"** (*zero hits in v5*).
   - In `V9_3_Q04_HERITAGE_DISPOSITIONS.md:30`, Gen2 formally resolved the heritage row as: **"Retire (code); canonized docs."**
6. **Slot 23 in `alchemical_round.rs` Was an Empty Metadata Shell**:
   - `ENGINE_CATALOG` (`alchemical_round.rs:280-286`) defined slot 23 as `PhylogeneticTracker` (*"Evolutionary taxonomic lineage tracking across memory revisions and code mutations"*).
   - Codebase search confirms that **no implementation existed** behind `PhylogeneticTracker`—it was merely a name in a static definition array.

---

## 4. How Gen3 Implements True Causal Cladistics

Gen3 (`WMgen3`) replaces decorative biological metaphors with an empirically verified, constitutionally governed evolutionary architecture.

### 4.1 First-Class Relational Edges (`W2_01_relations_edges.md`, `DESIGN_CANON.md` §3.5)
Relations in Gen3 are first-class directed hypergraph edges:
$$e = (w, s, c, t)$$
where $w$ is learned weight/strength, $s \in \{-1, +1\}$ is sign/direction, $c$ is resource cost, and $t$ is trust/confidence. They carry explicit epistemic classification (`Speculation` vs `Evidence`) and immutable journal provenance:
- **`supersedes` (Temporal State Replacement)**:
  - Derived via candidacy rule `candidacy.v1.shared-rare+value-diff+temporal` (`ops.rs:745-756`, `field.rs:10-25`).
  - Governed by **Structural Strata** ($0 = \text{current}$, $1 = \text{unresolved/contradiction}$, $2 = \text{superseded}$).
  - *Non-destructive*: Old states are suppressed in standard recall but remain 100% accessible via `include_historical: true`.
- **`derived_from` (Acyclic Cladistic Descent)**:
  - Connects mutated beliefs, synthesized recipes, or refined strategies back to their direct ancestral node.
  - Carries full transformation provenance: `path → structures touched → mutation delta → outcome`.
- **`recombined_from` (Memetic Hyperedges / Multi-Parent Polyploidy)**:
  - Formulates hyperedges: $(A + B + C) \xrightarrow{\text{recombined\_from}} D$.
  - Allows hybrid innovations (cross-domain synthesis across multiple memory clusters) while preserving pointers down to original evidentiary grounding stars (`DESIGN_CANON.md` §3.5).

### 4.2 Selection Events Tied to the Claims Ledger (`W1_B4_claims_belief_class.md`, `BENCHMARK_AND_VERIFICATION_PROTOCOL.md` §3)
Gen3 enforces strict epistemic discipline to avoid self-deceptive "hallucinated evolution":
1. **Constitutional Invariant 9 & Closure 2**:
   - Inferences, mutations, and claims are *speculation/beliefs*, never world evidence.
   - A candidate mutation must register a formal claim: `{statement, domain, source_date, predicted_outcome, confidence, falsification_criteria}` with fail-closed confidence bounds $[0, 1]$.
2. **Immutable Resolution Events**:
   - When evaluated against external benchmarks, a durable resolution event is appended to the journal: `{validated: bool, event, event_date, actor}`.
   - Raw ex-ante confidence is strictly immutable.
3. **Statutory Brier Calibration & Empirical-Bayes Shrinkage**:
   - Calibration is computed as a statutory statistic over the resolved set:
     $$\text{Brier Score} = \frac{1}{N} \sum_{i=1}^{N} (f_i - o_i)^2$$
   - Empirical-Bayes prior shrinkage weights small sample sizes toward prior baselines:
     $$w = \frac{n}{n + 20}$$
4. **Empirical Benchmark Delta Requirement**:
   - A candidate mutation cannot be selected based on internal self-assessment (prohibiting Gen1's self-scoring flaw).
   - Selection requires a positive empirical benchmark delta:
     $$\Delta(\text{Baseline } A, \text{Candidate } B) \Longrightarrow \{\Delta \text{Ranking}, \Delta \text{Strata}, \Delta \text{Brier}, \Delta \text{Resource Cost}\}$$
   - If Brier score degrades or resource slopes show superlinear growth, the mutation is rejected and rotated cold.

### 4.3 Parallel Shadow Clones in Isolated Lease Sandboxes under Phase 7 Replay
Recursive Self-Improvement (RSI / W2_06) and cladistic mutation exploration are operationalized via:
1. **Isolated Lease Sandboxes (`W1_B3_coordination.md`)**:
   - Sandboxes operate under atomic concurrency leases tracked at `<git-common-dir>/wm-leases.json`.
   - Leases require: `scope`, mandatory `intent`, `owner_session`, and `ttl_secs`.
   - **Typed Effect Asymmetry**: Lease acquisition can be refused (`VIOLATION_AHIMSA`) under system stress, but exact-owner release is always admitted (`Resource::CoordinationRelease`).
2. **Tokio / Rayon Concurrency**:
   - **Tokio Runtime**: Orchestrates parallel asynchronous execution of candidate Shadow Clones in isolated sandbox environments, enforcing timeout budgets and failure containment.
   - **Rayon & SIMD**: Parallelizes high-dimensional scoring, vector projection ($\tau$-gated cosine operations), and batch graph-walk verifications across candidate lineages using Apache Arrow `RecordBatch` representations.
3. **Phase 7 Counterfactual Replay Harness (Maker $\neq$ Checker for RSI)**:
   - Defined in `BENCHMARK_AND_VERIFICATION_PROTOCOL.md` §4.3 and §5:
     $$\Delta(\text{Baseline } A, \text{Candidate } B) \text{ over historical journal } \mathcal{J}$$
   - Takes immutable historical event journals containing thousands of past situations and simultaneously executes them through both Baseline $A$ and Shadow Clone Candidate $B$.
   - **Independent Witness Rule (`W2_06_rsi_over_journal.md` §1.2)**: The proposing organ cannot evaluate its own success. An independent witness checks for regression, stale-context intrusion ($R_{sed}$ ratio), and calibration drift.
   - Only mutations that achieve superior empirical performance across counterfactual replays without violating constitutional invariants earn ratification, merging into the durable germline (Geneseed promotion).

---

## Summary Comparison Table

| Dimension | Gen1 (v26) | Gen2 (WMv9) | Gen3 (`WMgen3`) |
|---|---|---|---|
| **Mining Substrate** | Git commit log (`git log --numstat`) | Git commit log (exact port of Gen1 miner) | Immutable operational journal $\mathcal{J}$ + external benchmarks |
| **Lineage Tracking** | Template name string (`parent_id: str`) | **Missing** (`LINEAGE_LEDGER.md`; tags only) | First-class DAG / Hyperedges (`derived_from`, `recombined_from`, `supersedes`) |
| **Mutation Engine** | `PolymorphismEngine` (regex/synonyms) + LLM grammar | Basic RSI patch generation (`codegen.rs`) | Parallel Shadow Clones exploring candidate mutations |
| **Execution Sandboxing** | None (direct filesystem writes) | Worktree leases (initial prototype) | Isolated lease sandboxes with typed effects (`Resource::CoordinationLease`) |
| **Concurrency Model** | Synchronous Python + PyO3 | Async Rust (tokio) + LMDB | Tokio task sandboxes + Rayon/SIMD over Arrow batches |
| **Fitness Evaluation** | Exponential Moving Average ($\alpha=0.1$) on usage | None (static confidence score) | Statutory Brier score + Empirical-Bayes shrinkage ($w = \frac{n}{n+20}$) |
| **Selection Validation** | Self-reported disappearance of errors | Caller-asserted resolution | **Maker $\neq$ Checker**: Phase 7 Counterfactual Replay against history |
| **Status / Disposition** | Shipped (vibe god-kit) | Retired (`V9_3_Q04` disposition: Retire code) | Ratified experimental architecture & nucleus protocol |
