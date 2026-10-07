# WMgen3 — Scaffold, Transfer & Contamination Strategy

**Discussion draft · 2026-09-16 · to be ratified with `docs/CHARTER.md` (Phase 0).**
This is the "how we build it without repeating either generation" document. It is
deliberately short. Anything that grows past three pages gets cut or deferred.

---

## 1. The shape being scaffolded

Four plastic layers inside one orthogonal constitutional shell:

| Layer | Purpose | Phase-1 implementation |
|---|---|---|
| Epistemic substrate | evidence / belief / speculation kept distinct | one store + `x=(content, class, source, provenance, confidence, horizon, domain)` — not three databases |
| Dynamic field | activation, relations, propagation, decay | `e=(w,s,c,t)` = weight, sign, cost, trust. Nothing else until an experiment demands it |
| Selection + lifecycle | what gets resources, persists, cools, dissolves | per-operation selection contracts; exploration budget; delayed credit; lifecycle `transient → candidate → persistent → cold` |
| Compiler surface | stable intent → changing internal organization | verb subset only: **remember · recall · think · inspect** |

The constitution is **not layer five** — it surrounds all four and is unreachable by
plastic runtime updates.

Two closures, same enforcement machinery (static write-path analysis + runtime canaries
+ receipts + `inspect`):

- **Closure 1 — Law:** no plastic write path reaches constitutional state.
- **Closure 2 — Evidence:** no inference-only path reaches world-evidence.
  Evidence objects carry an explicit `domain ∈ {world, system, simulated, reported}`;
  repetition can never silently promote `simulated → world`.

---

## 2. Freezing Gen2 as control — concretely

| Decision | Choice | Notes |
|---|---|---|
| Control artifact | **v9.1.7 released binary** (sha256 recorded in `receipts/`) | Already verified, already carries the conflict/supersession baseline. Do **not** couple experiment start to 9.1.8's in-flight release; 9.1.8 continues as production cadence |
| Gen2 source | `WMv9` untouched during Phases 0–2 | No merges from WMgen3. No "quick fixes" to Gen2 to help the control |
| Gen2 stores | Never touched | Experiment copies live in `data/control/` |
| Gen2 arm execution | Black-box: frozen binary via CLI/MCP on copied data | The control must be the shipped organism, not a library re-build |
| Reference pin | Record tag + commit + binary hash in a receipt at Phase 0 | Any drift voids the A/B |

---

## 3. Workspace pattern — sidecar organism, not a fork

**Chosen: Option A.**

| Option | Verdict |
|---|---|
| **A. New private workspace `WMgen3/` with fresh git history** | ✅ chosen |
| B. Fork WMv9 → strip organs in the fork | ❌ drags release machinery, CD workflows, public surface; blurs the freeze; tempts history rewrites |
| C. Sidecar crate inside the WMv9 workspace | ❌ contaminates Gen2's release surface; couples Gen3 to Gen2 APIs *before* Phase 3 decides what to compile |

Initial crates (created in Phase 1, not now):

- `crates/wm-gen3-core` — epistemic substrate, closures, minimal field, selection
  contracts, lifecycle.
- `crates/wm-gen3-harness` — experiment harness + thin four-verb surface. Harness code
  is allowed to be ugly; it exists to falsify, not to ship.

**Dependency direction is one-way forever:** Gen3 may wrap/call Gen2 (Phase 3+);
Gen2 must never import Gen3. The integration seam in Phase 3 is an adapter in Gen3 —
**zero modifications to Gen2** ("evolve, don't replace" applied to the ancestor).

No release machinery, no npm/Docker/registry surface, no public repo until Phase 2
passes. Version `0.x` for the experimental era; "Gen3" naming is earned, not dated.

---

## 4. Transfer & contamination policy (the experimental-integrity heart of this doc)

The Phase-2 A/B is only meaningful if the Gen3 arm is genuinely minimal. Two boundaries:

### Allowed — *infrastructure* (stock engines any implementation would use)
LMDB bindings, Tantivy (lexical only), serde/msgpack, tokio/rayon, error handling,
test tooling, and the frozen Gen2 **binary** as the control arm. Every allowed
dependency gets a line in `docs/DEPENDENCY_MANIFEST.md` with a one-line rationale.

### Forbidden in Phase 1 — *behavioral machinery under test*
Importing or copying any Gen2 implementation of the behaviors being compared:
conflict detection, supersession resolution, episodic retrieval scoring, typology
write-gates' dedup/conflict logic, claims ledger, importance/recency scoring.
If Gen3 imports these, Phase 2 proves nothing.

### Borderline — decide explicitly, with a receipt
| Item | Provisional call |
|---|---|
| Embeddings / vector search | **Defer.** Lexical-only reduces variables; add only if the experiment's kill-criteria demand it |
| Tantivy scoring functions | Allowed as stock engine; Gen3 must not port Gen2's query planners or filters |
| Session/continuity machinery | Not needed for the contradiction experiment; keep out |
| Data types copied from Gen2 | Allowed only if re-expressed as Gen3 primitives with their own tests — no verbatim porting |

**Copy now (Phase 0/1):** control binary hash manifest, experiment corpora (with
provenance), reference pointers. **Copy later (Phase 3):** nothing is "copied" — the
compile pass issues per-capability verdicts:

`COMPOSES CLEANLY · COMPOSES AWKWARDLY · IRREDUCIBLE · PRESERVE IMPLEMENTATION · RETIRE · EXPERIMENT`

Gardens → field conditions/profiles; Engines → reusable transformations/compositions;
Galaxies → views/partitions/clusters. Proven optimized implementations stay **callable
behind the compiler** until — and unless — the general substrate earns their
replacement.

---

## 5. Modifications necessary to Gen2

**Phases 0–2: none.** Gen2 is frozen. Any change to Gen2 is out of scope by definition.

**Phase 3: still none in Gen2.** The integration runs one-way through a Gen3 adapter:
- Preferred: Gen3 calls the Gen2 binary/process (black-box, versioned, replaceable).
- Optional: Gen3 links specific Gen2 crates where a library call is materially better.
- Both are Gen3-side adapters. If a Gen2 interface is too coarse to call, wrap the
  binary; do not reopen Gen2.

---

## 6. Data, stores, and the corpus

- `data/gen3/` — Gen3-owned stores. `data/control/` — copies used by the Gen2 arm.
- Contradiction corpus: sourced from Gen2's existing T8/MemoraStrict fixtures plus (if
  licensing allows) a frozen heritage subset. **The pre-registration pins exact files,
  counts, and hashes before either arm runs.**
- Production stores (`~/Desktop/WHITEMAGIC/data/…`) are never read directly by
  experiment code; any needed subset is exported, hashed, and frozen first.

---

## 7. Experiment governance conventions

- **Pre-register before building**: metrics, thresholds, equal-budget definition,
  kill criteria, and what counts as "useful emergent structure" (the six-condition
  test) — committed in `experiments/contradiction/PRE_REGISTRATION.md`.
- **Receipts** for: charter amendments, contamination-boundary exceptions, pre-reg
  edits, phase gates. Each receipt = committed file with date, rationale, hash.
- **Claims Ledger entry** for the thesis itself, with a falsification deadline.
- **Budget equality is defined operationally** in the pre-reg: equal wall-clock
  engineering sessions, identical data, identical hardware class, same restart
  points. Months of Gen2 tuning must not silently beat a prototype.

---

## 8. Explicitly not built yet (deferred by decree)

Digital phylogenetics · memetic recombination · Geneseed promotion · developmental
worlds · adapter distillation · MandalaOS embodiment · 3/7/12 dynamics · 22-path
clustering · Tree visualizations · valence systems · symbiogenesis. All become Phase 4
candidates only after selection is demonstrated in Phase 2. Inheritance is downstream
of selection, not parallel to it.

---

## 9. Next artifacts (in order)

1. `docs/CHARTER.md` — three-tier law, both closures, the symbolism rule, amendment
   procedure. Target: ≤3 pages.
2. `experiments/contradiction/PRE_REGISTRATION.md` — frozen baseline, metrics table,
   equal-budget definition, kill criteria, Claims Ledger entry text.
3. `docs/DEPENDENCY_MANIFEST.md` — the allowed list, one rationale per line.
4. Then (and only then) scaffold Phase 1.
