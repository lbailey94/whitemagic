# PET Hardening Strategy

**Prepared:** 2026-08-13
**Status:** Phase A complete (A1–A3 shipped 2026-08-13); Phase B (v5.9) and
Phase C still planned

This plan addresses the three remaining gaps between WhiteMagic and the
"full PET functionality" ideal, on the lore test's own terms:

> Prevent what you can at the boundary, detect what you can't, and say
> honestly which is which.

## The Three Gaps

1. **Probabilistic alignment** — effect gates only catch what tools declare;
   a false declaration slips through silently.
2. **No root of trust** — identity is self-asserted (`_meta`), and store
   tampering is not detectable.
3. **Insider with the binary** — nothing detects or reverses silent history
   rewriting.

## Honest Ceilings (what we will not claim to fix)

- Deterministic jailbreak-proofing of natural-language routing is impossible;
  the destructive-tool hard gate plus abstention remain the answer, labeled
  as such.
- Authenticated multi-tenant operation is out of scope; the PET is a trusted
  single-user local process by design.
- A hostile user with OS-level access owns the machine; that is filesystem
  encryption and OS account territory, not ours.

## Phase A — Trustworthy Declarations (before release)

Closes the last open release blocker (effect inventory audit) and makes the
existing gates trustworthy.

### A1. Wire `ResourceRules` into the dispatch pipeline ✅

`wm-governance::ResourceRules` (budgets, novelty detection, purpose
requirements, human-review decisions) exists but is not evaluated on the
dispatch path.

- Add `ResourceRules` to `DispatchPipeline` and evaluate per dispatch. ✅
- Enforce write budgets and surface human-review flags. ✅
- Acceptance: a test proves a budget-exceeding write is refused and a
  novelty/review flag reaches the response. ✅
  (`pipeline_resource_rules_*` tests in `wm-dispatch/src/pipeline.rs`;
  budget violations, autonomous human-review/purpose violations block;
  novelty flags attach to the response as `resource_flags`.)

### A2. Effect inventory audit ✅

Verify every registered tool's `EffectRow` against actual behavior
(store writes, network, process, filesystem, actuator).

- Build the audit as tests, not prose: for each mutating tool, assert the
  store/index actually changed and the declaration covers it. ✅
- Acceptance: no tool mutates without declaring it; false declarations fail
  CI. ✅
  (`crates/wm-mcp/src/effect_audit.rs` — 16 tests: static registry checks,
  behavioral sweep over all store-local tools, mutator spot-checks through
  the real pipeline, and a harness meta-test. The audit found and fixed 13
  false declarations: `transaction.commit` (pure→journals write),
  `transaction.rollback`, `galaxy.purge/transfer/restore`,
  `memory.consolidate/deduplicate/decay/update/tag/delete` (runtime-galaxy
  understatements), `memory.create`, `system.flush`, and 8 autonomous-cycle
  tools writing Substrate. A runtime Satya check in the pipeline now refuses
  `galaxy=citta` writes without evidence.)

### A3. Write-audit trail ✅

The karma ledger already compares declared vs actual writes per dispatch;
extend it into an append-only store mutation journal.

- Journal entries: tool name, memory id, content hash, timestamp, declared
  vs actual writes. ✅
  (`wm-governance::WriteAuditJournal` — append-only LMDB journal in the
  Karma galaxy under a `waj:` key prefix; actual writes measured with a new
  `MemoryStore::mutation_count()` counter.)
- Surface in `wm doctor` / diagnostics: misdeclarations become visible. ✅
  (`wm doctor` reports entry count + undeclared-mutation entries with tool,
  entry id, store writes, and timestamp.)
- Acceptance: a deliberately misdeclaring test tool is detected by the
  journal check. ✅
  (`pipeline_write_audit_detects_misdeclaring_tool` in wm-dispatch +
  `audit_harness_detects_deliberately_misdeclaring_tool` in wm-mcp.)

## Phase B — PET Hardening (v5.9 theme)

### B4. Effect-based sandbox mode (`wm serve --sandbox`)

Block `Resource::Process`, `Resource::Network`, `Resource::Filesystem`, and
`Capability::Execute` at the dispatch pipeline.

- A real execution sandbox for the full profile with zero new taxonomy.
- Acceptance: sandbox mode refuses web/process/filesystem tools and allows
  memory/session tools; a negative test covers each blocked capability.

### B5. Store seal and verify (`wm seal` / `wm verify`) ✅ (HMAC, not a root of trust)

HMAC-SHA256 per-file manifest (`seal.json`) plus a per-install secret at
`<store>/.seal_key` (mode 0600). Detects accidental corruption and casual
tampering. An adversary with filesystem access can replace both key and
manifest.

- `wm seal` / `wm verify` CLI pair; verify exits 1 on mismatch/missing/extra.
- Unit tests cover pass, modification, missing, extra, key/manifest exclusion.
- Not Ed25519-signed; `wm doctor` does not yet surface the seal.
- Acceptance for this slice: tampering with a sealed store is detected.
  Full root-of-trust / doctor integration remains later.

### B6. Untrusted `_meta` by default

Ignore client-supplied `compartment`/`user_id` unless the operator passes an
explicit `--trust-meta`.

- Default identity becomes local single user; docs stop implying more.
- Acceptance: `_meta` compartments are ignored without the flag and honored
  with it.

### B7. Store permission hygiene

Create the store directory `0700` by default; `wm doctor` warns on looser
permissions.

## Phase C — Insider Accident Resistance (as usage grows)

### B8. Full-store backup (`wm backup`)

Wrap snapshot + off-store copy + verify in one command; document restore.

### B9. Integrity story

Karma chain + store seal + audit journal together give the
"history cannot be silently rewritten" property; document it in SECURITY.md
as the anti-tamper story.

## Execution Order

1. ~~Next session: A1–A3 (release-adjacent; A2 closes a release gate).~~
   ✅ Done 2026-08-13 — all three shipped with tests and CI coverage.
2. After release: B4–B7 as the v5.9 "PET hardening" theme.
3. On demand: B8–B9.

## Related

- `docs/RELEASE_READINESS.md` — release gates and public-claims discipline.
- `docs/PRE_RELEASE_LAUNCH_PLAN.md` — launch assets.
- `docs/ARCHIVE_CAPABILITY_MAP.md` — v6+ direction (storage abstraction,
  provenance, interchange format).
