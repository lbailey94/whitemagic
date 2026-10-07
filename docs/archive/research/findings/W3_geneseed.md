# W3 — Geneseed / memetic lineage (wave-4 extraction)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md` / `PHASE4_WAVE2_FINDINGS.md` (format), `PHASE4_GEN1_TREE.md` §3
wave-4 bullet, `PHASE3_DECOMPOSITION.md` row "Memetic lineage / Geneseed" (E14 §§, EXPERIMENT,
Phase-4 gated), `SCAFFOLD_STRATEGY.md` §7–§8. Format: observed behavior · selection history ·
candidate Gen3 expression/manifest · adversarial cases · ablation · open questions.

**Counts (commands stated):** `rg -i -l 'geneseed' …/og_whitemagic/core --glob '!*/tags/*' | wc -l`
→ **20 files** (Gen1 v26); same pattern over `WMv9/crates --glob '!*/target/*'` → **13 files**
(Gen2). `memetic` in Gen1 core → 0 source hits outside the concept docs read here.

---

## Observed behavior — Gen1 v26: four distinct organs share one name

1. **Git-history miner (shipped, PyO3).** `core/whitemagic-rust/src/geneseed_miner.rs` (407 L),
   registered `lib.rs:97,282-285` as `mine_geneseed_patterns` / `get_geneseed_stats`. File header:
   *"Recovered from archive whitemagic0.2; adapted to drop chrono dependency."* A near-duplicate
   `memory/geneseed_miner.rs` (370 L) is **dead** (`memory/mod.rs:22`: `// pub mod
   geneseed_miner;`). Function: shell `git log --numstat`, classify commits by message
   **substring** (perf/optim/speed/faster/cache→0.8 · refactor/cleanup/simplify→0.6 ·
   fix/bug/issue→0.5 · feat/add/implement→0.4), confidence = (base + longevity≤0.2) × size factor
   (0.8–1.1); returns structs, writes nothing. Python bridge
   `whitemagic/optimization/rust_mining.py:113-142` raises `RuntimeError` if the ext is absent.
2. **Code-template vault with name-string lineage (shipped).** `whitemagic/codegenome/vault.py`
   (`GeneseedVault` :44) + `engine.py` (`CodeTemplate.parent_id` :93, `fork()` :187,
   `fork_template()` :1725; Ed25519 content_hash/signature_key; deprecation via usage
   `success_rate`). Reads/writes `WM_ROOT/codegenome/usage_stats.json` (vault.py:404-433) and
   YAML templates under `WM_ROOT/codegenome/` (engine.py:1602-1616). Emits Gan Ying
   `geneseed.render`/`geneseed.fork` (vault.py:117,443). Wired to dispatch:
   `codegenome.generate/list/fork/status` → `dispatch_agents.py:107-110` →
   `handlers/codegenome.py` (fork handler :85-107). `generate_with_llm` optionally injects mined
   git patterns into the LLM prompt (vault.py:158-198). This is real parent→child forking, but
   `parent_id` is a template **name string**, not an edge on stored memories.
3. **Hollow test-crafter wearing the name.** `tests/unit/integration_adhoc/test_phylogenetics_geneseed.py`:
   every function is `assert True  # Geneseed Automated Mutation`. "Geneseed Automated Mutation"
   was a test-generation pass, not a mutation engine.
4. **Concept only.** The canon design (typed parent edges on derived memories, n-parent forks,
   selection events) has no v26 code (E14 §§; `LINEAGE_LEDGER` digital-genetics row). Adjacent
   unread: `genetic.run/status` tools (`registry_defs/unauthored_intelligence.py:47-55`,
   `dispatch_table.py:367-368`) — lineage-flavored name, engine not inspected (UNVERIFIED).

## Observed behavior — Gen2 WMv9: one miner, two undeclared routes

- `wm-tools/src/expansion/geneseed.rs` (610 L) is a port of organ 1 (same classify heuristics;
  diff: hand-rolled approximate date `unix_ts_to_date` :51-70 — 28-day February, no leap years;
  `splitn(4)` :205; `is_ascii_digit` :189). `mine_geneseed_patterns` :146, `get_geneseed_stats`
  :251, `store_patterns_in_vault` :341. Vault write = plain memories (default `Galaxy::Codex`,
  opt `Galaxy::Research`) with tags `geneseed:pattern`, class Knowledge, tier Semantic,
  importance = confidence — **tags only; no parent edges, no commit-to-memory relations**.
- Routes `geneseed.mine` (:415), `geneseed.stats` (:495); registered `expansion/mod.rs:387-388`.
  Manifest `docs/contract/route-schema-manifest.json` (header: 303 routes / 86 declared /
  217 undeclared) lists both as `declared: false`, `properties: {}` (:983-994) — matches the
  decomposition's "2; 0 declared".
- Reachability: CLI `wm geneseed` prints results (wm.rs:1667-1699; no vault store); retired
  `bagua.dispatch` Li branch calls the tool with defaults, so `store_in_vault=false` and the
  result is discarded (bagua.rs:325-340); `army.deploy` reserves the name `geneseed_miner` and
  **rejects** it, redirecting to `geneseed.mine` (army.rs:71,141,976-981). No daemon/cycle calls
  it. `examples/transmute_geneseeds.rs` is a hard-coded store-to-store data migration (not a
  route) that tags records "geneseed".
- No memory lineage exists in Gen2: in-repo `docs/LINEAGE_LEDGER.md:51` — digital genetics /
  memetic lineage **missing** (zero `memetic|digital genetics` matches; V9.1 target = typed
  parent edges, n-parent forks, selection events; first live datum = wmv5 session `3a803124`
  seq 11, the track-ledger fork recorded as a selection event). `docs/V9_3_Q04_HERITAGE_DISPOSITIONS.md:30`
  (2026-09-14) disposes the heritage row: **"Retire (code); canonized docs."**
- Related-but-distinct: `archaeology.rs` memory-layer excavation + tag/keyword co-occurrence
  (`learning.pattern` :151-282); `wm-cognitive/miner.rs` keyword-overlap association proposals;
  `wm-cognitive/codegen.rs` RSI patch generation (unrelated). Typed relations *do* exist as a
  Gen2 mechanism (W2 associations findings) — Geneseed simply is not wired to them.

## Selection history

Gen1's miner was recovered from an older archive, duplicated (one copy commented out), bridged
to Python, and in Gen2 ported verbatim with hardening nits — a **duplicated organ, never
selected on outcome**: no attestation shows mined patterns changing retrieval, code generation,
or any downstream decision. The template vault has a feedback loop (usage stats → deprecation)
but was never retired or replaced; Gen2 dropped it. The memetic-lineage *design* was never
implemented in either generation, so it cannot have been selected out — hence EXPERIMENT, not
RETIRE, in the Gen3 verdict set. Gen2's own heritage pass (Q04) chose docs-only retirement for
its code, while `SCAFFOLD_STRATEGY.md` §8 holds Gen3 inheritance deferred **until selection is
demonstrated** ("inheritance is downstream of selection").

## Candidate Gen3 expression / manifest notes (no proposals; what exists vs owed)

- **Design target (V9.1/LINEAGE_LEDGER):** typed parent edges on derived memories, n-parent
  forks, selection events on lineage edges.
- **Substrate primitives already present:** typed relations store + `LinkType` (mechanism-live
  in Gen2 per W2); provenance chains / hash-chain revisions (wave-1 revisions row); journal
  event schema (`PHASE1_CONTRACTS`; `PHASE2_RUN_JOURNAL`). Owed: a **selection event** type and
  an acyclicity/ancestry rule — neither found.
- **Manifest (E14 §§, decomposition :160-163):** ancestor = v2-era memetic-lineage design
  (+ shipped miners/template forks as name-ancestors only); wire = typed parent edges +
  selection events on relations; **acceptance unset; owner unset**; gate = selection
  demonstrated (scaffold §8). A fair trial under standing rules would additionally require
  pre-registration (metrics, thresholds, equal-budget definition, kill criteria, receipts —
  `SCAFFOLD_STRATEGY.md` §7), a frozen behavioral spec, and a no-lineage control holdout. The
  only attested selection datum today is n=1 (the track-ledger fork).

## Adversarial cases

1. **Substring classifier overfires and is order-biased.** `fix` matches "prefix", `add`
   matches "address", `perf` matches "imperfect"; branch order (perf → refactor → bugfix →
   feature) makes "fix cache bug" a performance commit. Precision must be measured on a labeled
   commit set before any confidence leaves the tool.
2. **Longevity = proven is inverted.** Older one-off commits score higher monotonically (capped
   +0.2); `longevity_days` is computed at call time, so stored patterns change value across
   calls; Gen2's date conversion is approximate (no leap years/28-day Feb), so stored
   `timestamp` strings are wrong for most years.
3. **Parser fragility / window mismatch.** Commit headers detected by `contains('|')` +
   digit-prefix test (binary numstat `-` silently 0; messages containing `|`; merge commits).
   `stats` classifies messages with `--max-count=1000` but reports `rev-list --count HEAD` as
   `total_commits`, so rates never sum to 1; `mine` caps at `max_commits` (default 250) —
   three different windows.
4. **Self-ingestion cycles.** `store_in_vault=true` re-runs write duplicate rows (no exact-hash
   gate — see wave-1 dedup row); in a future parent-edge wire, mining the store's own repo can
   create a derived memory whose ancestor is itself derived. Needs a declared acyclicity rule.
5. **Descent ≠ selection.** Git history is descent of code, not of memory use; a retained patch
   and a used template are different signals. Neither generation records "this derived record
   was selected" except the one track-ledger datum.
6. **Vault deprecation is a swept threshold.** v26 auto-sets `deprecated` when usage
   `success_rate < _DEPRECATION_THRESHOLD` loaded from JSON (vault.py:404-420) — a tuned
   trigger on stored artifacts; any re-entry needs the wave-1 threshold rules, not import.

## Ablation ideas

- Miner-only (exists today): toggle longevity boost / size factor and compare the admitted
  commit set at fixed `min_confidence`; replace the keyword classifier with a constant to test
  whether downstream consumers (only the LLM prompt at vault.py:170-188 in v26) change output.
- `store_in_vault` off vs on in Gen2: expect **no retrieval change** (tags only, no edges) and
  measurable duplicate growth — a clean falsifier of "vault = lineage".
- For any future parent-edge wire: drop selection-event edges from recall; if ordering/behavior
  is unchanged, the edges were decorative; if changed, the selection signal is load-bearing.

## Open questions

- Were v26 `codegenome.*` handlers reachable in any shipped profile (`dispatch_agents.py` is a
  separate table from `dispatch_table.py`)? **UNVERIFIED.**
- Live state: no `geneseed`/`codegenome` state dir was confirmed under `/home/lucas/.whitemagic`
  in this pass; whether `WM_ROOT/codegenome/usage_stats.json` ever existed is **UNVERIFIED**
  (no v26 DB on host per wave-1).
- Was `examples/transmute_geneseeds.rs` ever run against the hard-coded live paths?
  **UNVERIFIED** (example-only, not registry).
- Are `geneseed.mine/stats` reachable in the running gateway's effective profile (manifest says
  registered-undedeclared)? Profile membership not checked here.
- What counts as "selection demonstrated" for a lineage row specifically (scaffold §8)? No
  operational definition found in the read set; E14 leaves acceptance/owner unset.
- Is `genetic.run` (dispatch_table.py:367 → `v24_3_handlers`) a fourth Geneseed-adjacent organ
  (mutation loop)? **UNVERIFIED** — not read.
