# W1 — Gen2 9.1.8 capability-source map (wave-1 surfaces)

**Status:** findings · 2026-09-17 · read-only research; assigns no verdicts. Companion to
`PHASE4_WAVE1_FINDINGS.md` and `PHASE4_GEN2_DELTA.md`.

Pin: `WMv9` workspace `Cargo.toml:23` = `9.1.8` (capability-source reference; control stays 9.1.7 per the
delta; route surface 302 / 85 declared). Source reads only — no build/test run.

---

## 1. Store + ingestion

- Write path: `memory.create` = `wm-tools/src/lib.rs:367`; class/tier `lib.rs:513-517`; store via
  `RecallEngine::store_with_embedding` (`wm-memory/src/recall.rs:505`) or `MemoryStore::put`
  (`wm-memory/src/store.rs:726`); episodic mirror `lib.rs:584-597`.
- Content identity: SHA-256 `content_hash` (`wm-memory/src/memory.rs:645`), O(1) lookup `store.rs:1144`,
  dedup wrapper `put_dedup` `store.rs:1173`.
- Write gate: `wm-dispatch/src/write_gate.rs:103` — junk → dedup → plausibility (`:1-35`); wired
  `pipeline.rs:292` / `wm-mcp/src/server.rs:1215`; decisions disclose as `write_gate`.
- Idempotence: an exact content-hash hit does **not** insert — bumps `dup_count`, refreshes `accessed_at`,
  decays importance (`imp /= 1 + dup_count`), returns a short circuit (`write_gate.rs:184-211`); batch
  drops duplicate items (`write_gate.rs:8-13`).
- Ingest ledger: per-file SHA-256 `ingest_ledger.jsonl` (`wm-mcp/src/ingest.rs:9`, `:454-498`);
  unchanged skipped (`:1043-1048`); `wm ingest --dry-run/--redact` (`bin/wm.rs:377-407`); `wm grimoire load`.
- Contract: re-ingesting an unchanged corpus is a no-op; identical content writes are absorbed
  (disclosed), never duplicated. Status: **live**.

## 2. Retrieval

- Engine: `RecallEngine` `wm-memory/src/recall.rs:265`; hybrid fusion BM25 0.5 / vector 0.3 / importance
  0.2 (`recall.rs:86-137`), entry `hybrid_search` `:947/960`; post-fusion knobs (graph/trust/
  corroboration/conformal) default OFF (`:93-119`).
- Route: hybrid iff real embedder, else episodic deterministic lane, else FTS, else importance;
  `recall_mode` disclosed (`memory_ops.rs:1248-1260`, `1337-1400`, `1465-1508`). Episodic = deterministic
  scorer + session boost + optional rerank (`:2027`; default-route tests `:3052-3087`);
  `memory.episodic_search` is the raw experimental surface (`:1916-1947`). `conversational.rs`
  (`:63,312,481`) surfaces only via `memory.chat` (`wm-tools/src/lib.rs:1893`).
- Abstention: non-empty query + zero above floors → `insufficient_evidence` /
  `no_results_above_floors` (`memory_ops.rs:1783-1789`); fixture `wm-tools/tests/
  abstention_contract.rs:12-55`. Floors are declared args (`:1188-1191`); out-of-range = caller
  error (`:4865-4908`).
- Evidence bundle v0: `build_evidence_bundle` `memory_ops.rs:45-183`; entry fields `id · galaxy ·
  retrieval{route,score,matched_terms,via} · source_time{created_at,basis,event_time,basis} ·
  history{revision_count,superseded,chain_valid,current} · integrity · visibility{private,
  model_exclude} · coverage{representation,truncated,exact_read_available}`; bundle carries
  `conflicts{count,pairs}` (`:166-183`); cold-only ⇒ `unavailable_cold_record` (`:92-113`).
- Contract: retrieval never silently claims absence; empty-above-floors is explicit. Status: **live**
  (hybrid needs `WM_EMBEDDER_*`; stub degrades to episodic with disclosure).

## 3. Revisions / currentness

- Revision chain: `wm-memory/src/revision.rs:1-18`; entries `{seq,timestamp,old_hash,new_hash,actor_*}`
  (`:26-47`); append `store.rs:1575`, read `:1610`; `verify_chain` = seq + hash linkage + head match
  (`revision.rs:73-107`); route `memory.revisions` list|verify (`memory_ops.rs:684-724`).
- Currentness (episodic): `resolve_current` reorders only current-cue queries (`is_current_query`
  `episodic.rs:1001`, cues `:988-992`); anchors = UserStatement + change markers (`:1016-1041`);
  non-current keeps score order (test `:1571`).
- Contradictions preserved, never adjudicated: `detect_conflicts` `episodic.rs:1089` (markers `:1046-1056`),
  surfaced in the bundle's `conflicts` block (`memory_ops.rs:166-183`).
- Session-turn supersession: `session.record` `supersedes` (`session_ops.rs:357`), tags `superseded-by:`
  / `supersedes:` (`:446-459`); hidden by default, `include_superseded:true` restores (`:88-98`, `516`).
- Contract tests: `supersedes_hides_old_turn_until_requested` (`session_ops.rs:2104`), lossless
  visibility (`:2868`), `episodic.rs:1537`; "temp correction" naming UNVERIFIED.
- Contract: every content change leaves a hash-linked revision; current-value questions prefer the newest
  marked statement; corrections hide the old turn but history persists. Status: **live**.

## 4. Sessions / continuity

- `session.record` `session_ops.rs:341` — typed turns, role→provenance trust user 1.0 / agent 0.7
  (`:437-439`), sequence counts superseded turns (`:406-408`); `session.start` `session.rs:78`.
- `session.checkpoint` `session.rs:277` auto-captures git via `WM_PROJECT_ROOT`; 9.1.8 effect row
  declares FS reads + `spawns` (`:246-258`) and is refused under strict mode.
- `session.checkpoint_nodiscovery` `session.rs:376-492` stores exactly the supplied fields (commit,
  branch, tests_green, next_queue, open_flags, lease_id) with **no discovery, FS read, or subprocess**;
  one Sessions write (`:388-393`) — the only strict-admitted checkpoint shape (delta §2.1;
  `dharma_gate.rs:270-278`).
- Continuity `session_ops.rs:886-983` (newest prior session *with turns*, `created_at` ordering, scoped
  hint when empty); replay `:478-`; digest `:990-1043` groups typed turns + latest checkpoint (`:1063`,
  `:1128`); export/import `:1422`/`:1545` preserve ids/timestamps.
- Contract: under strict mode a handoff stores only caller-supplied fields; resolution is time-based,
  never UUID-scan based; digest derives from records. Status: **live**.

## 5. Coordination

- Lease ledger: `LeaseLedger` `wm-tools/src/expansion/coordination.rs:72`, file `<git-common-dir>/
  wm-leases.json` (`:70`, `:89-97`); discovery pure filesystem, no subprocess (`:81-88`); lock w/ 30 s
  stale steal (`:40`, `:116-150`); `Lease{scope,intent,owner_session,claimed_at,expires_at,ttl_secs}`
  (`:46-62`); `try_claim :262`, exact-owner release `:299`, `force_release_peer :316`.
- Routes `code.claim/check/release/list` (`:473-930`); `check`/`list` use `snapshot_readonly` — no lock,
  no temp file (`:225-236`, `678`, `902`); `code.release` binds the configured root and refuses an
  alternate/escaping one (`:750-800`).
- Strict effects: `Resource::CoordinationLease` / `CoordinationRelease` (`wm-core/src/effects.rs:38-42`),
  `acquires_coordination_lease :180`, release-only shape `:187-195`; strict refuses acquisition/renewal
  with typed `VIOLATION_AHIMSA` (`wm-governance/src/dharma_gate.rs:265-278`), exact-owner release admitted.
- Capability gate: `capability_gate.rs:1-45` (wm-dispatch); `_engagement` always verified when presented
  (Ed25519 → revocation → expiry → scope) and stripped before the tool body (`:20-21`); advisory default,
  strict via `WM_REQUIRE_CAPABILITIES=1` (`:60-76`); issuer key rides the token — no authority anchor
  (`:29-33`).
- Tokens: `EngagementToken` `engagement_tokens.rs:89`, issue/validate/revoke `:215/:251/:303`; scope→
  capability map `capabilities.rs:399-415`, full check `:421+` (both under `wm-governance/src/`).
- Contract: one writer per scope (mandatory intent + TTL); reads never lock; stress may refuse new claims
  but never release; capability enforcement opt-in and evidence-bound. Status: **live**.

## 6. Claims

- Tool `claims` + aliases add/resolve/status/list/calibration (`claims_tools.rs:34-100`, `:289-295`,
  `wm-tools/src/expansion/`); add/resolve are writes (`:308-314`); add needs statement/domain/
  source_date/predicted_outcome/confidence/falsification; resolve needs validated + event + date.
- Ledger `wm-simulation/src/claims.rs:91`; record `:157`, resolve `:190`, status `:230`, list `:305`,
  calibration `:316`; Wilson 95 `:133`; empirical-Bayes recalibration (w = n/(n+20))
  `calibrated_confidence :379`; raw confidences never edited.
- Persistence `<store-root>/claims_ledger.json` (`wm-mcp/src/server.rs:1421`, loaded `:2563`); self-model
  Brier metric is separate (`wm-selfmodel/src/metrics.rs`).
- Contract: every claim is dated + falsifiable with raw confidence; calibration (Brier, signed gap,
  Wilson interval) runs over resolved claims only and is reported alongside. Status: **live**.

## 7. Galaxies + compartments

- Enum: `Galaxy` 16 variants `wm-core/src/galaxy.rs:11-45`; `COUNT = 16` `:49`; `memory_galaxies()` 11,
  Telemetry excluded as evidence (`:82-96`); `db_name` `:100-118`.
- Dynamic overlays: `DynamicGalaxyRegistry` `wm-core/src/mutable.rs:266-287` — min cluster 10, **max 20**,
  prune threshold 0.1; over-cap create prunes then refuses (`:304-321`); physical registry
  `wm-memory/src/galaxy_registry.rs:33` has no cap of its own (cap wiring UNVERIFIED).
- Mandala: 4 tiers research/sandbox/production/secure, 256MB/256MB/1GB/4GB maps, secure read-only by
  default (`wm-memory/src/mandala.rs:26-101`); `Compartment` `:169`, `MandalaManager` `:223` — one LMDB
  env per tier.
- Access law: `Context::can_access_galaxy` / `can_write_galaxy` (`wm-core/src/context.rs:132`, `167`);
  unknown compartments fail closed (`:158-172`).
- Contract: fixed taxonomy + capped dynamic registry (Gen1's sprawl class structurally prevented);
  compartment = access tier on a request, not storage machinery. Status: **live**.

## 8. Retention / lifecycle

- Lifecycle: `wm-memory/src/lifecycle.rs:15`; `consolidate :88`, `forget :156`, `run_full_cycle :181`,
  phagic digest `:214`/`:225`.
- Prune: `retention.prune` `wm-tools/src/expansion/autonomous.rs:306-390` runs `CycleType::Prune`, returns
  proposals with `requires_human_review: true`, writes only a Substrate cycle record.
- Cold rotation: `PhagicDigester` `wm-memory/src/cold_storage.rs:577`; `scan_outer_rim :607`,
  `digest_galaxy :821`, `digest_all :855`, `thaw :879`; PRAY `action:"cold_rotate"` (`pray.rs:346-377`)
  with de-index + association cleanup (`:159-166`); wrapper `wm-cognitive/src/phagic.rs:43-73`.
- Cold reads: unranked recovery only, `no_thaw: true`, integrity `verified`, floors
  `not_applicable_unscored_recovery` (`memory_ops.rs:1191`, `1715-1734`).
- Contract: forgetting is propose-and-review, never silent purge; cold records stay hash-verified and
  return only by explicit thaw or unranked navigation. Status: **live** (daemon scheduling UNVERIFIED).

## Gaps / unverified

1. "Temp correction contract" naming not found verbatim; closest tests §3 (`session_ops.rs:2104`,
   `episodic.rs:1537`).
2. Gen2 dedup is a short-circuit + `write_gate` disclosure, not a journaled `remember.refusal` /
   `duplicate_exact` event (that vocabulary is Gen3's).
3. Bundle version is the literal string `"v0"` (`memory_ops.rs:179`); "landed 9.1.6" comes from the delta,
   not git history.
4. Dynamic galaxy cap 20 applies to `DynamicGalaxyRegistry` only; direct physical `GalaxyRegistry::create`
   may bypass it (not traced).
5. Daemon scheduling of cold rotation / phagic digest not traced (PRAY manual action + cycle wrappers only).
6. Mandala access keys off client-supplied `_meta.compartment` (membership, not authenticated authz).
7. `memory.chat` / `conversational.rs` exposure under the curated profile not checked.
8. Lease visibility across worktrees rests on filesystem git-common-dir discovery; bare/odd layouts =
   documented v0 limitation (`coordination.rs:81-88`).
