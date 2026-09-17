# Changelog

All notable changes to WhiteMagic are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [9.1.8] — 2026-09-17 (coordination truth-up, mesh ingest hardening, startup fixtures, onboarding)

### Onboarding — load your data
- **`wm grimoire` gains a `load` step:** reads the ingest ledger and either
  reports what is loaded (files, chunks, ledger path) or points at the
  load-your-data path — `wm ingest --source <folder> --dry-run`, then
  `--redact` to write. Loading stays optional and never gates readiness.
- **The same first-run path is surfaced at startup:** `wm quickstart`'s next
  steps, the fresh-install `wm status` block, the MCP server instructions,
  and `skill.md` all name the ingest route (dry-run first; local-only;
  idempotent via the per-file SHA-256 ledger).

### Security — coordination truth-up (AHIMSA Target A)
- **Dedicated coordination effects:** `Resource::CoordinationLease`
  (claim/renew) and `Resource::CoordinationRelease` (exact-owner cleanup)
  replace the generic filesystem declaration. Strict mode refuses lease
  acquisition/renewals with a typed `VIOLATION_AHIMSA` so system stress
  cannot trap new work; exact-owner release stays admitted so a held lease
  can always be freed. Nothing here is a filesystem or process exception.
- **`code.check`/`code.list` are genuinely read-only:** a
  `snapshot_readonly` path reads and filters the ledger without creating a
  lock or temporary file and without persisting expiry pruning (expired
  leases are logically absent and still reportable).
- **`code.release` root binding:** when a configured repository is known
  (`WM_PROJECT_ROOT`), an alternate/escaping `root` is refused — owner
  cleanup may act only on the configured repository's fixed ledger.
- **No-discovery checkpoint:** new `session.checkpoint_nodiscovery` stores
  exactly the supplied handoff fields (commit, branch, tests_green,
  next_queue, open_flags, lease_id) with no repository discovery, no
  filesystem reads, and no subprocesses — available under strict mode. The
  git-capturing `session.checkpoint` now truthfully declares its filesystem
  reads and subprocess spawns and is refused there.
- **Startup-under-stress fixtures:** a spawned-binary healthy-start fixture
  (fresh store under frozen settings creates + reads back), plus in-process
  fixtures that keep the governance refusal (`VIOLATION_AHIMSA`) and
  first-run starvation (typed homeostasis limit disclosing
  `WM_HOMEOSTASIS_FROZEN`) distinct and reads open under starvation.

### Security — mesh ingest hardening (phase 1)
- **Signed-only discovery:** `PeerAnnounce` beacons carry the signer's public
  key and bind it in the signed payload (`peer_id:tcp_addr:timestamp:key`).
  Ingest verifies signatures, enforces a `2 × interval` freshness window and a
  per-source rate limit, and records only signature-verified
  `(peer_id, timestamp)` observations in a bounded replay cache — a forged
  beacon can no longer consume the genuine beacon's replay slot. First sight
  TOFU-binds the announced key; a later key change for a bound peer is refused
  (address unchanged). Legacy keyless beacons remain address hints.
- **Key separation:** `WM_MESH_KEY` now derives purpose-scoped subkeys with
  HKDF-SHA256 — `wm/mesh-identity/v1` (mesh identity) and
  `wm/record-attestation/v1` (record attestations); `wm/release-signing/v1`
  is reserved. One-release dual-verify keeps the legacy XOR-fold identity and
  the legacy beacon payload accepted during migration.

## [9.1.7] — 2026-09-15 (trustworthiness: external-audit fixes, instrumentation, contract v0)

> Released 2026-09-15. Driven by an external 9.1.6 reliability audit of the
> musl artifact plus an independent review round of the slice; every Tier‑1
> finding has a black-box or unit acceptance test. No surface adds network
> egress: all new instrumentation is local and display-only.

### Reliability — externally audited (Tier 1)
- **Installer P0 fixed**: reinstall no longer truncates `~/.profile`. When the PATH line already existed, the old loop left `path_fixed=0` and the else-branch rewrote the file with `>`, destroying unrelated lines. The PATH check is now whole-line (`grep -xF`) and an existing profile is never overwritten; write failures warn. Black-box sentinel test (stub curl, no network) pins byte-preservation across a double install.
- **Advertised phrase routing fixed**: "where were we" is all-stopwords, so tokenization emptied before the phrase table ran and the router abstained at confidence 0.0. Phrase routes now run before tokenization; a table-driven test asserts every `PHRASE_ROUTES` entry bare and with trailing content.
- **Numeric floors fail closed**: `min_trust`, `min_importance`, `min_score`, `min_score_ratio` (and `memory.update` importance) reject out-of-range values as structured caller errors instead of silently disabling the floor (`min_trust: 2.0` used to turn the trust floor *off*). Boundary tests cover −ε/0/0.5/1/1+ε.
- **Importance range enforced end to end**: `write_gate::parse_importance_value` range-checks (was type-check only), the update path routes through it, class policy can no longer mask an out-of-range caller value, and galaxy import/restore plus typed telemetry clamp legacy payloads into 0.0–1.0.
- **Index health is measured, not inferred**: `wm status` classifies LMDB↔Tantivy drift against the sanitization-skip reserve instead of checking that the index directory exists. New fields `index_memories` / `index_drift` / `index_skip_reserve` / `index_detail` and a `DEGRADED` line name the galaxies that would change on rebuild. Session writes (start/checkpoint/end/record/handoff) are indexed at write time, so a live server no longer reports self-healing drift as degraded.
- **Hidden partial success disclosed**: an episodic-mirror failure after a successful legacy write (`MDB_BAD_VALSIZE` on large content) now appears as a `warnings` entry on `memory.create`/`memory.batch_create` and session responses instead of only a server log line.
- **npm launcher hardened**: download → temp → sha256 → chmod → atomic rename; the cached binary is re-hashed before exec and self-heals on mismatch; DNS/checksum/cache failures print one human line, never a raw Node stack.
- **Credential redaction**: JSON-style assignments (`"api_key": "…"`) are now detected and redacted alongside `key = value` forms.

### Instrumentation — local, display-only (Tier 2)
- **Cross-process `wm stats`**: reads the persisted `mutable_tool_stats.json` (a fresh process used to show zeroed counters); `--week` estimates per-tool activity from `stats_history.jsonl` daily rollups written on checkpoint. A corrupt snapshot is reported as corrupt, not as empty.
- **`wm telemetry schema` / `wm telemetry preview`**: publishes the record/retention/redaction contract (`docs/TELEMETRY.md`) and shows exactly what an opt-in transmission would carry from this store — display-only, no network I/O, redaction pass is fail-closed.
- **`wm report`**: sanitized support bundle (`report.json` + `README.txt`) with HOME collapsed to `~`, paths narrowed, and a content-free assertion test. (Correction, 2026-09-15: a `wm doctor --report` alias was described here but never landed; `wm doctor` has no `--report` flag. The alias is queued for the next patch.)

### Contract v0 (Tier 3)
- **`wm contract`**: machine-checked route/schema manifest built from the exact binary revision (`--json`, `--check`, `--out`); the curated unconditional-read check runs clean. Artifact: `docs/contract/route-schema-manifest.json` (302 routes, 70 declared, 232 undeclared — family-scoped remediation follows per `V9_1_7_FULL_PROFILE_CONTRACT_BACKLOG.md`, which lives outside this repo in the Codex workspace `~/Documents/ChatGPT/whitemagic v9.3 development/work/release-closure-phase-a/`; the in-repo artifact is the manifest). `kg.query` now declares its required `entity`.

### Error & terminology hygiene (Tier 1.5)
- **Breaker counts backend failures only**: caller validation and governance refusals no longer trip a tool's circuit breaker (`counts_as_breaker_failure`); the open-breaker error discloses remaining cooldown, and the per-tool rate-limit error names its governor instead of collapsing every limit into "rate limited". The homeostasis refusal is likewise named.
- **Expected contention reads like contention**: `main()` prints `Display` (no anyhow/`RUST_BACKTRACE` stack section on refusals); the second-writer lock message drops Tantivy's Debug-wrapped `Some("…")` payload.
- **`wm grimoire`**: the release probe runs on a side thread, so first-run wall time is `max(local, probe)` instead of the serial sum; memory step renders the measured index detail.
- **Naming**: `fully_activated` gains the honest alias `core_ready` (semantic recall stays optional and excluded); `wm seal`/`verify` help states the LMDB-core scope (use `wm backup` for whole-store recovery).
- **`wm ingest --include-credential-files`**: explicit override for prose whose *filename* looks secret (`secrets.txt`); requires `--redact`, so credential-named documents enter with credential-shaped content scrubbed — never raw.

### Release gates
- CI gains a **host-scripts job** (installer sentinel, version truth, release manifest Python tests + npm launcher suite) so those gates no longer depend on a release ceremony.
- Re-verified on this commit: fmt clean · clippy `--all-targets -D warnings` clean · workspace 4,552 passed / 0 failed · Python 22 OK · npm 8/8 · `wm contract --check` clean · curated smoke passed · zero-egress proof passed (network namespace with only a DOWN loopback) · all version surfaces agree.
- **Test-count note (2026-09-15):** the 4,552 above is the local pre-release gate run; the tagged-commit CI job (`cargo test --all-targets`, Linux) counted **4,542 passed / 0 failed / 2 ignored** — the figure `release-manifest.json` records. Quote the manifest figure for release claims.

## [9.1.6] — 2026-09-15

### Security
- **Credential redaction coverage**: `wm ingest --redact` now detects and redacts AWS secret access keys and compound assignment keys (`secret_access_key`, `aws_secret_access_key`, `secret_key`, `client_secret`, `private_key`, `auth_token`, `refresh_token`); detection and redaction share one key list and the redacted forms are idempotent.
- **Sandbox executor deadline (Landlock v1)**: the scoped-thread pathway now enforces `WM_DISPATCH_TIMEOUT_MS` inside the confined thread — a timed-out tool future is dropped and reported, mirroring the normal dispatch path; `with_timeout` overrides per executor and timeouts are counted.
- **`sandbox.set_limits` input validation**: all six fields are validated before any is applied; wrong-typed, negative, or out-of-range values are rejected with the field named (no silent `u32` truncation, no partial application). Behavior tests cover acceptance, atomic rejection, and effective write/spawn/network budget enforcement.

### Setup & onboarding
- **Split readiness states**: `wm grimoire --json` now reports `substrate_ready`, `agent_wired`, `continuity_verified`, `semantic_recall_available`, and `fully_activated` alongside the compatibility `ready` aggregate — a fresh machine with no client reports `ready: true, agent_wired: false, fully_activated: false` instead of a single coarse boolean. `wm connect --write` exits non-zero when any detected client fails to configure (partial connect is not activation).
- **Tested connections**: after `wm connect --write`, WhiteMagic now proves the wired command actually serves — it spawns the configured binary in a throwaway HOME and performs a real MCP handshake (`initialize` + `tools/list`), reporting the exposed tool count or exiting non-zero on failure. Config-parse checks remain necessary but are no longer sufficient.

### Telemetry
- **Unified evidence ceiling**: RSI auto-friction writes (`friction.auto_log` regression paths and anomalies) now clamp importance to the shared `IMPORTANCE_CEILING` (0.40) used by the typed telemetry path, instead of writing 0.5–0.95; severity remains visible in `rsi:severity:*` tags. Manual `friction.log` (Codex) is unchanged.

### Retrieval
- **Unfiltered-search round-trip**: `memory.search` / `memory.hybrid_recall` accept `galaxy: "all"` (case-insensitive) as an alias for the all-galaxies default their own responses emit, instead of failing with "Unknown galaxy: 'all'".
- **Telemetry is evidence, not cognition**: unfiltered `memory.search` / `memory.hybrid_recall` no longer surfaces telemetry-galaxy records — the exclusion is enforced in the hybrid, episodic, FTS, association, and cold phases — while an explicit `galaxy: "telemetry"` filter remains the only door. Regression: v9.1.5 default search returned RSI friction records when the query text matched.
- **Hot-path navigation disclosure**: hybrid, episodic, FTS, and association results now declare `content_representation: "scrubbed_navigation"`, the 8,192-character bound, whether the excerpt was truncated or scrubbed, and that a complete read is available (`exact_read_available`); the importance browse path declares `verbatim`. Cold discovery already carried this contract — the disclosure now shares one implementation.
- **Trust-floor closure and explicit abstention**: `min_trust` now fails closed (results without a stamped `trust` are excluded) and every phase stamps `trust` (association and importance included), verified by a two-verb matrix test; a query with no qualifying results returns `abstention: {status: "insufficient_evidence", scope: "retrieval"}` instead of a silent empty set.
- **Evidence bundle v0**: every retrieval response now carries `evidence_bundle` — per-result exact `id`/`galaxy`, retrieval reason (route/score/matched terms/via), source time (hot records bind `created_at` as `recorded_at`; cold-only records declare `unavailable_cold_record`), integrity, visibility, and coverage (representation/truncation/exact-read availability).
- **History and conflict disclosure**: bundle entries carry `history` (`revision_count`, `superseded`, `chain_valid`, `current`) and the bundle surfaces detected contradiction pairs (`conflicts.pairs` with marker and shared topic terms); `source_time` now states `event_time: null` with `event_time_basis: "not_tracked"` instead of implying event-time knowledge.

### Preservation & verification
- Readonly inspection is proven non-mutating at byte level: `wm doctor` on a live store leaves LMDB, the Tantivy index and every store file untouched (new bin test `doctor_readonly_inspection_preserves_store_and_index`), and a strict read-only open of a pre-cold store leaves `data.mdb` and the directory listing unchanged when it refuses (strengthened `ensure_schema_completes_a_pre_cold_store`).

### Governance & safety
- **Destructive ops now honor explicit operator intent:** `confirm: true` bypasses the eco-mode brain-wave availability restriction (Alpha/Theta/Delta) and the Dharma strict-mode brain-wave arm for destructive tools — a confirmed action is deliberate, not autonomous. The stressed-homeostasis arm (health < 0.3) stays absolute and is never bypassed. `confirm` is resolved at the top of the dispatch pipeline so every gate sees it; the delete-confirm audit is unchanged.
- **Yama write budgets:** healthy default `max_writes_per_minute` raised 60 → 120, and health-scaled budgets now have floors (writes ≥ 10, spawns ≥ 2, network ≥ 5) clamped to the configured maximum — batch workflows (ingest, session imports) are no longer starved on low-health stores, while explicitly stricter configs (Secure compartments) keep their tighter budgets.
- `claims.add` / `claims.resolve` declare the ledger write in their `EffectRow` — the tools/list `readOnlyHint` annotation and write-budget accounting now treat them as writes; read-only claims actions (status/list/calibration) stay read-only.

### Routing
- **Confidence-aware disclosure**: NLU abstentions now name the weak top candidate as `suggested_route` (with `suggested_confidence`), and dispatches below 0.30 confidence carry `low_confidence: true` plus the runner-up `alternative_route` — behavior is unchanged (no new abstentions), but a weak guess is confirmable instead of silently trusted.
- NLU routing gains `session.continuity` and `session.record` profiles, decisive phrase routes ("where were we", "what did we decide last", "continue from", "pick up where", "where did we leave off") and a `resume` prefix route — resume intentions now land on `session.continuity` instead of `gnosis`/`session.recall` (verified live at confidence 1.0; classifier regression tests cover 5 phrasings).

### Release gates
- **Capability accounting (one source)**: `wm doctor` now prints the canonical tier chain from the capability manifest (registry entries → full-profile routes → active-profile routes → MCP tools; +1 meta-router; the MCP count reads `handshake-time` before `initialize`) instead of a bare registry count; `wm selftest` labels its discovery count as tool-catalog routes; the server module doc no longer hardcodes a tool count.
- **Release-ceremony gate**: `scripts/version_truth.py` now also checks `CHANGELOG.md` — the target version must not still sit under `[Unreleased]` and must have a dated `## [x.y.z]` section (the v9.1.5 tag shipped with a draft heading) — and covers `PRIVACY_POLICY.md` as a version surface. The release workflow runs the gate as its first job and blocks the tag build on drift.
- `scripts/curated_smoke_test.py` extended: claims annotation truthfulness (add/resolve write-capable, reads read-only), `claims.add` write path, and NLU routing checks (resume/continuity phrases → `session.continuity`, "remember..." → `memory.create`) — the process-level gate now covers the 9.1.6 governance/routing changes end to end.

### Lock hygiene — no more hangs on live or wedged stores (9.1.6)
- **Inspection never touches the lock file**: `MemoryStore::open_inspection` (MDB_NOLOCK | MDB_RDONLY) powers `wm status`, `wm doctor`, and `wm grimoire`. Read-only env opens previously blocked forever in two real situations: a live writer holds the exclusive lock (lmdb-master falls back to a blocking shared-lock wait), and a crashed server leaves the lock file's in-file mutex wedged so *every* open hangs — `wm grimoire`/`wm status`/`wm doctor` against a served store hung until SIGKILL, and a crashed unit (observed: OOM under load) bricked the store for all opens until `lock.mdb` was manually removed. Inspection is now immune to both: pure mmap reads, no fcntl, no reader slots.
- **Write-intent paths fail fast instead of deadlocking**: `wm trust`, `wm backup`, `wm anchor` probe the writer lock with a non-blocking `fcntl(F_SETLK, F_WRLCK)` first and refuse with the documented "a server may be running" message (previously the same lmdb fallback made them hang forever; the error text was aspirational).
- **Network timeouts actually bound**: `fetch_manifest_text`/`download_to` set `timeout_connect` in addition to the global deadline — under network saturation the global timeout did not fire while the connect phase rotated candidate IPs (grimoire's release step hung past its 5s cap; now caps at 5s and degrades to the offline step).
- Recovery path documented in `AGENTS.md`: stop the store's `wm-serve` unit, remove `lmdb/lock.mdb`, restart (LMDB recreates it; safe when no process holds the store).
- Regression test: `status_live_store.rs` — a spawned `wm serve` holds the writer lock across processes; `status::collect` completes promptly, the probe reports the held lock, and the lock is free after the server exits.

## [9.1.5] — 2026-09-14 (agent-first onboarding, telemetry retention, signed releases)

> Released 2026-09-14. The canonical record is the signed
> `release-manifest.json` on the GitHub Release (artifact sizes, install
> gating, crate count); `wm grimoire`/`wm connect` are the new first-run
> doors, and tags are signed-and-Verified from this release onward.

### Telemetry & governance
- `telemetry.record` accepts `telemetry.observation` policy decision records (policy id/metric/state/action/value mandatory) and rollups validate via `harmony.avg` — the typed path behind the live step-0 observation policies.
- New **`telemetry.retention`** read-only planner: per-tier counts/bytes/ages/eligibility under the exact `telemetry.prune` horizons, plus a `managed: false` observation inventory. Declares no writes and is not destructive, so it is never confirm- or dharma-gated — pre-prune evidence is always available.
- Weekly `wm-telemetry-retention.timer` operator unit (planner first, then a confirmed prune; degrades gracefully on pre-9.1.5 fleets), complementing the hourly rollup timer.

### Setup & onboarding
- **`wm connect`** — one command detects installed MCP clients (config file or client config directory present) and wires WhiteMagic into each, dry-run by default; `--write` patches every detected client with timestamped backups through the same read-back-verified `wm setup` machinery.
- **`wm setup --write` now patches every supported client config**, not just `mcpServers` JSON: OpenCode `opencode.jsonc` is edited by a comment/string-aware structural editor (comments, siblings, and formatting preserved), and Codex `config.toml` via `toml_edit`. Every write is backup-first and re-parsed; malformed sections are refused, re-runs are idempotent.
- Patching an inline empty `mcp` object (`"mcp": {}`) now inserts the member with clean indentation, matching the structural editor's pretty behavior.
- Onboarding states the contract — explicit routes are the contract — in `wm setup` output and the client configuration guide.

### First-run & routing
- New **`wm grimoire`** — one guided pass for a fresh install: host inspection, substrate selftest, release check (offline-tolerant), agent-config detection, memory calibration, vocabulary teaching, and a restart-continuity demonstration on a throwaway store. Human `[OK]/[WARN]/[SKIP]/[FAIL]` lines plus a `--json` report; `--write` patches detected client configs. The MCP `initialize` instructions and `skill.md` now point at it.
- `wm status` on a fresh install no longer suggests `quickstart` as the way to create the real store (the demo store is isolated by design); it now points at `wm quickstart` for verification and `wm serve --profile curated` / `wm setup` for normal use.
- `wm selftest` is quiet by default (like `quickstart`); subsystem warnings require `--verbose`.
- Recall phrasing: `recall X` routes to `memory.search` (it previously chose `memory.read` and treated the phrase like an id), and multi-word intentions — "find X", "what do you remember about X", "what did we decide about X", "look up X" — route to search instead of falling through to gnosis. The routed thought now carries its query too: payload extraction strips the same curated phrases (shared tables, no drift), so the search actually runs — verified live at 5/5 phrasings plus classifier, payload, and E2E regression tests.
- `wm update check` (and `install`) treat an unreachable network as an ordinary local-first state: a calm message, exit code 2, structured detail under `--json`, no error chain or backtrace.
- The embedding-router NLU layer now carries the same curated phrase intent as the TF-IDF classifier (memory.search anchors plus phrase bonuses), so both layers agree on "find X", "what do you remember about X", "what did we decide about X", and "look up X".
- `wm grimoire`'s memory step probes a configured `WM_EMBEDDER_ENDPOINT` (reachable, or a loud warning plus lexical-fallback note when unreachable) and reports `WM_EMBEDDER_BACKEND=onnx` as in-process instead of a generic "configured".
- `wm status` reports `up to date (last checked …)` from the recorded install state instead of always pointing at `wm update check`.

### Distribution & release engineering
- New **release-health record + reconciliation**: `scripts/release_health.py` probes the GitHub release assets, every workspace crate on crates.io, npm, Docker Hub, and the official MCP registry; `release-health.yml` retries laggards on Release completion and daily, certifies the npm and Docker install paths with `wm selftest`, uploads `release-health.json` to the GitHub Release, and gates red while any surface lags.
- `wm selftest --json` now runs on all five build targets in the release matrix (the curated smoke test remains the deeper Linux check).
- **Version truth**: `scripts/version_truth.py --check/--set` covers all 15 version-bearing surfaces (Cargo pins, npm package/server/MCPB, Dockerfile labels, hosted server-card, CITATION, docs, install examples); `release.sh` preflight refuses drift and the bump stage uses the tool instead of the old three-file inline edit.
- Distribution fixes: MCPB bundle, reproducible Smithery publishes, sanitized tools snapshot.
- Curated catalog trimmed to the 9-tool lifecycle surface; tool annotations, `outputSchema`, and `structuredContent` on the server surface.
- **Signed release tags**: `release.sh` creates a signed tag (`git tag -s`) when a signing key is configured and falls back to an annotated tag with a loud warning otherwise — source provenance alongside the signed release manifest, which remains the binary trust anchor.
- Public-surface guard hardening: every private doc path is blocked at pre-push and by a dedicated `security.yml` CI job; the trust-tier pricing sketch is now private.
- Release smoke gate: the curated smoke test pins a frozen homeostasis (load-independent, so stress-scaled AHIMSA vetoes cannot flake the release gate), verifies rollback against the real result id fields, and asserts `wm grimoire --json` readiness; a teach-surface contract test binds the grimoire vocabulary, `skill.md`, and the MCP instructions together.

## [9.1.4] — 2026-09-13 (lossless continuation, cold discovery, first-run UX, signed updates)

### Continuation & recall
- **Lossless continuation contract** for `session.replay`: explicit session selection, byte-exact content, coherent-view cursors (unsigned placement hints, not authority), privacy/model-exclusion before output, explicit refusals instead of silent truncation, and independently bounded serialized output (`lossless_wire_ceiling_too_small`). 8 lossless + 6 replay tests including Unicode re-chunking and selection beyond 10,001 source records.
- **Opt-in cold discovery**: `memory.search(include_cold: true, cold_scan_limit)` hydrates candidates from the cold payload, verifies the id/galaxy/content-hash chain (tamper → refuse), skips private and non-current records, and appends verified hits with `source=cold`, `integrity=verified`, `model_visible`, plus a `cold_discovery` disclosure — no thaw, no mutation. New `MemoryStore::find_cold_matching`.
- Continuity skips the empty newest session; omitted replay defaults to the latest session; cold reads work without thawing; restricted sources are excluded from public digests; `importance` accepts numeric strings instead of silently defaulting to 0.5.
- Deterministic **Gan Ying cue-to-recall-path trace** (test-only): detector → Research hint → proposal receipt → maintenance indexing → retrieval boundary, with an identical-cue disabled control.

### First-run experience
- New **`wm selftest`** (8 end-to-end invariants on a throwaway store, `--json`, ~1s), **`wm status`**, **`wm setup <client>`** (detects OpenCode/Claude/Cursor/Windsurf/Codex; shows the exact change; patches standard JSON configs with a timestamped backup and re-parses; JSONC/TOML are print-only), and **`wm update check`**.
- Fresh-install `wm doctor` is neutral (exit 0) and points at `wm quickstart`; default doctor grades the supported surface only (optional subsystems move behind `--deep`).
- `wm quickstart` is quiet by default regardless of ambient `RUST_LOG`; `--verbose` opts in.
- Canonical tool aliases (`memory.find` / `memory_find` / `memory_search` → `memory.search`) and canonical discrete tool names; `memory.query` works with tags only; complete curated input-schema coverage (contract ratchet 18 → 0) with a documented-surface contract test suite.
- One canonical platform story across README/QUICKSTART/install.sh; everyday-commands section.

### Updates & release engineering
- Each release now publishes a **signed `release-manifest.json`** (Ed25519 over the manifest itself; public key pinned at build time) with per-target URLs, sha256 digests and cosign bundle names.
- **`wm update check`** (notify-only; anonymous static fetch; `--insecure-checksum` fallback that is loud; `install.json` state; package-manager-correct upgrade hints) and **transactional `wm update install` / `wm update rollback`**: sha256 check → candidate `wm selftest` gate → `wm.previous` backup → atomic swap → post-swap health check with automatic rollback. Package-manager installs are refused with their own command.
- crates.io publish order derived from `cargo metadata`; MCP-registry publish retries during npm propagation; advisory npm-propagation wait.

### Governance, sandbox & fleet
- Capability gate (PLAN_F F-1 dispatch half): `EffectRow.invokes` maps to governance capabilities; presented engagement credentials are always verified and stripped before execution; strict mode via `WM_REQUIRE_CAPABILITIES=1`.
- Subprocess sandbox runner (B2); daemon Landlock v0 + dharma decision counters (B1/B3); edge-galaxy policy (exclusions, `os_telemetry_threshold`, migrate mapping) and the `Telemetry` galaxy.
- Public-surface guard now runs nightly (device names / personal strings / forbidden paths); public files sanitized.
- Load-independent strict-mode test seam (`WM_HOMEOSTASIS_FROZEN`); workspace clippy clean.

## [9.1.3] — 2026-09-12 (persistent local embeddings, recall honesty, breaker ops, Ahimsa fix)

### Embeddings & recall (live fleet)
- Persistent local embedder: `wm-embed-server.service` (llama.cpp + bge-small-en-v1.5 Q8, model on disk, loopback) wired via `WM_EMBEDDER_*`; warm query embed ≈ 20 ms, fully offline, no volatile cache. Rolled out query-side to wmv9/planning/neon/site/heritage.
- Restart persistence fixed: `hybrid_search` rehydrates the in-memory vector index from the Embeddings galaxy on first use; live proof — a BM25-invisible canary returned `source=hybrid` after a forced restart (cold query 70 ms).
- New `memory.reembed` (dry-run default, bounded, cached/batched via `WM_REEMBED_BATCH`, skips empty content, refuses the stub embedder): backfilled wmv9 (1,026 vectors), planning (18), neon (1,727), site (2). Heritage deferred with a runbook.
- HTTP embedder hardening: cache namespace carries model+dim; oversized inputs truncate to the model window (fixes HTTP 400 on long memories).
- Degradation honesty: `memory.search`/`hybrid_recall` probe the embedder when hybrid yields nothing, fall through to the episodic lane on failure, and disclose `hybrid_degraded: <reason>`.

### Governance & operations
- Ahimsa fix: destruction is declared (`EffectRow::destructive`), not inferred from Filesystem writes — additive writes (lease ledgers, audit logs) are no longer blocked under stress; Process/Network/spawn remain destructive-by-class. Live: `code.claim`/`code.release` succeed under Delta strict mode.
- `breaker.status` (read-only) and `breaker.reset` (confirm-gated, non-destructive) operator surface; `WM_BREAKER_THRESHOLD/WINDOW_MS/COOLDOWN_MS` envs; half-open admits exactly one probe (stale-probe recovery included).
- `/status` discloses `breaker` and `embedder` (backend/namespace/dim + live vector/cache counts); `wm doctor` probes the configured embedder for real instead of grading env presence.

## [9.1.2] — 2026-09-11 (memory hardening, redaction retrofit, wmv9 rename)

### Memory system hardening (session 8b52f642)
- `wm ingest` / `wm migrate`: fail-fast store-busy preflight (Tantivy writer-lock + live `wm serve` detection via `/proc/locks`) with bounded `--wait N`; silent 18-minute hangs now error in <0.1s naming the lock holder.
- Credential hygiene: `wm ingest --redact` (PEM/token/assignment spans, `redactions=N` disclosed) and new `wm redact-content` store-wide retrofit (dry-run default, revision-chained, idempotent). Vault store-wide pass: 675 rows redacted, final `would_redact=0` of 199,035 clean rows; pre-redact safety snapshot retained off-store.
- `memory.search`: backslash escaping before quotes (trailing-`\` terms broke phrases) plus `parse_query_lenient` fallback.

### Infrastructure
- Dev store/unit/gateway scope renamed `wmv5` → `wmv9`; gateway scope set is now `wmv9` (writable home) + `planning` + `vault` + `default` (read-only) on port 18795.
- Gateway drops the pinned 9.0.0 `q03` runtime; the fleet runs the 9.1.2 release binary.
- Version-truth pass: workspace internal dependency pins, npm/Docker labels, README/QUICKSTART/llms/CITATION and related docs.

### Privacy
- Repository no longer embeds Valkyrie's personal transmissions (examples read from the local sanctuary or an env var); SharedWorkspace sync exclusions added for sanctuary/aria artifacts.
- Valkyrie's sanctuary store stays device-local by policy; it is not federated, meshed, or synced.

## [9.1.1] — 2026-09-10 (the 44-commit verified batch + release-cadence groundwork)

### Operational trust stack (Q36–Q40)
- Nightly trust manifest stamped by OpenTimestamps + RFC-3161 (Q36/Q40); monthly receipts generator + timer; `morning_check.sh` one-command grading of the nightly run.
- Q37 zero-egress proof wired into CI; Q38 cosign + CycloneDX SBOM on release (this tag is its first real end-to-end run).
- First non-empty external anchor stamp lands 2026-09-11 03:30 UTC.

### Daemon stability: incremental index-drift heal
- Root-caused and fixed the ACC daemon watchdog crash-loop: healing now applies `+N` deltas incrementally instead of 58k full rebuilds (`1d1b09d`).

### Governance ports (waves 2–4)
- `EconomicFirewall` (Python TransactionFirewall port + economic Dharma profile), `NetworkStateProfile` + `GratitudeLedger`, bounty auto-connector.
- Wave 3 violet/security ports: `SecurityEventBus`, `PatternImmunity`, engagement tokens, model signing.
- Wave 4: blue-team deception set (canary tokens, decoy shell, deobfuscator); session miner (`PatternMiner` port, DEFERRED_OBJECTIVES L5).

### Capability & provenance hardening (P-PROV-5 / Glama gap slices A–C)
- Slice A: on-behalf-of delegation triple (`act`/`on_behalf_of`/`delegation_chain`) on `ActorIdentity` + `WriteAuditEntry`; profile-contract surface pin (sorted tool-name SHA-256 rug-pull tripwire) + `binary_version`; host-identity/delegation stance in SECURITY.md; confused-deputy gateway tests.
- Slice B: signed `ReleaseManifest` (artifacts + binary identity + surface pin, Ed25519 on node-key lineage, `wm-release-manifest/v1` domain separation, S9-HKDF upgrade path); warn-only 1-in-N secret-shape sampling of success outputs (`WM_SECRET_SCAN_EVERY`, default 100, 0=off; kinds+sizes logged, content never).
- Slice C: Landlock v1 `ScopedSandboxExecutor` — StoreScoped tools run on a fresh confined thread (thread-local ruleset injection, strict `WM_LANDLOCK_V1=1`, loud degrade, panic containment); first StoreScoped taxonomy batch (`memory.create/batch_create/update/delete`).
- TrustStack: one-call wiring of the economic governance loop (`6055146`).

### Gateway & compatibility truthfulness (Q03–Q05)
- Inner `args.scope` preserved through the pinned gateway proxy (Q03); Q03 manifest accepted, live gateway deployment documented.
- Compatibility routes made truthful; capability audit batch recorded (Q04); version-support and archive-count wording reconciled (Q05); Q06 preservation fixtures.

### Glyph & flight recorder groundwork (Q34/Q35b)
- `glyph.encode`/`decode` routes (`WM_GLYPH`-gated wire format) + dense-encoding bench fixture; flight recorder: args digest, twin-run replay acceptance, replay-from-sidecar (layer 2).

### Crypto-erasure design (Q39)
- One-design draft: RK → identity subkeys + galaxy DEKs, erasure receipts via the anchor stack; root-key ruling = hybrid C (OS keyring default, passphrase opt-in per store); Q10 implementation IS Q39 slices A–B (no second key hierarchy).

### Evaluation
- Grouped-source T3 validation run; constrained heritage pilot harness + pinned llama.cpp synthetic adapter + Ollama native-tools qualification; deterministic evaluation-setup failures.

### CI hardening
- Gates greened: fmt, clippy (incl. new-toolchain lints in `write_gate`), Windows e2e gating + nextest per-test hard timeouts, mesh fleet tests gated for Windows; publish-ready crate metadata, version-pinned internal deps.
- Merge hygiene: post-merge clippy/fmt reconciliation to `-D warnings`-clean across the workspace.

### Release cadence
- `docs/RELEASE_CADENCE.md`: two-clocks model (kaizen improvement clock vs scheduled release snapshot), freeze protocol via `code.claim`, calibration note for coordination writes under load (P-AHIMSA-6).

## [9.1.0] — 2026-09-09

### Distribution and install hardening
- `install.sh`: self-wires shell profile PATH so the first command after install just works, and creates `~/.profile` when no shell profile exists (minimal containers).
- One-command release fan-out: `scripts/release.sh` drives tag → CI → binaries → crates.io → npm → Docker → official MCP registry with 429-aware publish loops.
- v9.1.0 shipped on every channel: GitHub release with 5 binaries (linux gnu+musl, macOS x86_64/aarch64, windows), 15 crates published in a single ordered pass (zero rate-limit stalls), npm `whitemagic-mcp@9.1.0`, Docker tags `9.1.0`/`9`/`latest`, official MCP registry listing.

### Visibility boundaries on content-returning paths (shipped in 9.1.0; recorded retroactively)
- New `content_visible` gate (`mcp_visible` + `model_visible` + `validity_visible` + compartment access), enforced where hologram query builds candidates and where the Alchemist emits insight previews. Private, model-excluded, and compartment-forbidden records can no longer leak through ids, tags, previews, or coordinates on captain / hologram / PRAY / Bagua paths (which share these implementations).
- Aggregate counts are unchanged; only content-bearing outputs are filtered.

### Hardened cold rotation: fail-closed two-phase archive
- `galaxy.cold_rotate` apply path rewritten as chunked two-phase commit (archive → flush + sync → verify id-set → delete); any archive failure aborts before further deletions.
- Exclusive `create_new` archive files (timestamp + nanos + pid stems) plus per-run recovery manifest; same-second reruns can no longer truncate archives.
- Tantivy de-indexing and association cleanup on rotation (mirrors `memory.deduplicate`), with honest per-record counts; `destructive: true` with Filesystem/SearchIndex effects (pipeline requires `confirm: true`).
- NLU structural-gate test corrected to assert the true invariant (no destructive tool executes via NLU) rather than the proxy (no success at all).

### Governed wrapper defaults (PRAY / Bagua)
- PRAY `rebalance` and Bagua Kun preserve the child's dry-run default (`apply` now defaults false); Bagua Kun honors the caller's `galaxy`/`limit` instead of forcing all-galaxy writes.
- PRAY `cold_rotate` forwards caller bounds (`limit`, `output_dir`, `project_name`) and carries the same search/association cleanup wiring as the direct route.
- Removed the `ground` keyword trigger (it matched `background` and routed loose objectives into the write-capable trigram).
- Outer effects of both routers now truthfully declare Filesystem reads/writes.

### Gan Ying revival: synchronicity + rabbit-hole loop
- New taxonomy event `PatternDetected = 233` (Coordination; taxonomy now 234 types) for novel-cluster discoveries; mapped to the Sensory nervous subsystem.
- `SynchronicityDetector` revived: daemon subscribes it to the live Gan Ying Bus and drains new cross-subsystem coincidences on the Gan Ying tick (detection only, no store writes; stats + subsystem health accounting via `UnifiedNervousSystem`).
- `ResearchRabbitHoleTool` wired to the bus (`with_bus`; registered with the server bus): emits `PatternDetected` with topic/terms after synthesis, best-effort.

### Renamed: PRAT → PRAY (Polymorphic Resonant Adaptive Yoga)
- The meta-tool system is now **PRAY** — Polymorphic Resonant Adaptive Yoga (Skt. √*yuj*, "to yoke, join"): the method that ties a thousand or more tools and systems into a single `wm serve` surface. Renamed from PRAT (Polymorphic Resonant Adaptive Tools); PRAT remains the correct name in pre-v9.2 history.
- Code: `expansion::pray::PrayMetaTool` (deprecated `PratMetaTool` alias kept), `PROFILE_PRAY` / `--profile pray` (deprecated `prat` profile name still resolves), response key `pray_action` (was `prat_action`).

## [9.0.0] — 2026-09-06 (Rubedo — The Philosopher's Stone)

### Polymorphic Resonant Adaptive Tools (PRAT) & Single-Tool Default Profile
- Added `PROFILE_PRAT` (`wm serve --profile prat`) exporting **only 1 polymorphic tool: `whitemagic`**.
- Collapses 237 underlying historical tools down to a single polymorphic entrypoint supporting actions: `scout`, `audit`, `distill`, `rebalance`, `query`, `bagua`, `cold_rotate`, `hierarchy`, and `status`.
- Integrated Hongmen Chinese Triad / Tiandihui organizational structure (Incense Master 438 Vanguard, White Paper Fan 415 Alchemist, Straw Sandal 432 Cartographer, Red Pole 426 Sentry).

### Complete Geneseed Transmutation & 28 Lunar Mansions
- Transmuted all **28 Lunar Mansions** from The Grimoire (`01_HORN` through `28_WALL`, plus `29_SUPER_COHERENCE`, `30_DEEP_YIN`, and `TRUTH_TABLE`) into `Galaxy::Codex`.
- Canonized master lineage manuscripts into `docs/lineage/`:
  - `MEMORY_QUALITY_INTELLIGENCE_THEORY.md`: High-IQ vs Great-Memory-Hygiene foundational thesis.
  - `MANDALA_OS_FOUNDATIONS.md`: Bindu microkernel, Ganas, Dharma Engine syscall interception, SutraCode effect typing.
  - `SYNAPSE_SUPERVISOR_BLUEPRINT.md`: Tokio Rust parent supervisor and "Kill the Notepads" strategy.

### Hebbian Reinforcement & Cognitive Hygiene
- **Promotion-on-Read (S5)**: Wired Hebbian neuro-score reinforcement and novelty decay into `RecallEngine::hybrid_search_with_disclosure()` and `Association::activate()` on traversed links (`WM_PROMOTION_ON_READ=1`).
- **Dream Hygiene (D1–D8) & D6 Novelty Gate**: Implemented `NoveltyGate` enforcing proposition predicate-hashing and Jaccard distance floor $>0.15$ to prevent runaway autonomy loops.
- **Cross-Galaxy Traversal & Association Reranking (S9 & S10)**: Added `find_across_galaxies` and graph degree boosting (`WM_ASSOCIATION_RERANK=1`).
- **Galactic Cold Rotation (`galaxy.cold_rotate`)**: Operationalized Rubedo Criterion 2 (Rotation, Not Deletion) serializing candidate telemetry into compressed JSONL cold storage before LMDB pruning.

### Hardened Mesh Networking & Conformal Uncertainty Gating
- **Signed Discovery Beacons (`wm-sangha`)**: Added Ed25519 signature fields and validation to `PeerAnnounce` UDP beacons.
- **Conformal Bicameral Bus (`wm-bicameral`)**: Wired `wm-conformal` split-conformal prediction intervals into `CorpusCallosum::send_conformal()`.
- **Platform Honesty (`wm-substrate`)**: Calibrated non-Linux fallback in `health_score()` to report neutral 0.5 rather than false perfect 1.0 when `/proc` sensors are absent.

### CLI Parity & Developer Experience
- Added `wm geneseed` subcommand for read-only git history pattern longevity mining.
- Added `--kaizen` flag to `wm doctor` for Pearson correlation analysis across operational variables.
- Deployed persistent `whitemagic-daemon.service` running Autonomous Continuous Consolidation (ACC).

## [7.0.0-alpha.7] — 2026-08-31

### Mesh: beacon-first identity binding fixed (live-confirmed on second hardware)

- Unsigned beacons no longer seed identity bindings (`12c933c`,
  `5b4f54e`): beacons inform discovery only; the first **signed**
  heartbeat performs the binding, and a bound entry is never clobbered
  by an unsigned announce. Found live during the two-laptop rehearsal
  (cross-host joins were refused as identity theft after beacon
  pollution).

### memory.query semantics fixed (6da07b4)

- `memory.query` now performs the documented case-insensitive literal
  substring match across the galaxy; no-match returns an honest empty
  result. (The alpha.6 binary shipped before this fix landed —
  rehearsal-confirmed.)

### Provenance attribution defaults fixed (68547b9)

- Unattributed memories default to `source: unattributed` / trust 0.5
  instead of claiming `user` authorship; session and tool paths stamp
  honestly.

### CI hardening (6a929f9)

- Bounded RPC everywhere + job timeouts: no test may hang a job.

### Public surface hygiene (release re-audit, 2026-08-31)

- Removed `python/mcp_config_*.json` sample configs (hardcoded dev
  paths + retired repo name; `docs/MCP_CONFIG_GUIDE.md` is canonical).
- CHANGELOG: dev-local artifact reference reworded.
- Added `docs/STRANGER_SIMULATION_SCRIPT.md` — the faithful
  first-contact protocol and pre-committed scoring rubric for stranger
  runs.

### Friction auto-log default-off (2026-08-30)

- **`WM_FRICTION_AUTOLOG` (opt-in, default off)** — the RSI friction
  auto-logger no longer writes success-anomaly memories to the store
  unless explicitly enabled with `WM_FRICTION_AUTOLOG=1`. Shakeout evidence on a fresh
  store: the anomaly heuristics fired on successful dispatches
  ("high_latency" = any new peak latency, however small; "high_karma_debt"
  at debt > 0.5), grew the codex galaxy from 6 seeds to ~60 records in
  ~10 minutes at importance 0.9 (dominating every ranked view), and
  logged its own internal `__karma__:wm` refusals as user-facing
  friction — a self-amplifying loop. Read-only servers keep the
  `friction_ro.jsonl` sidecar in both modes (file, not store). Enabling
  restores the pre-change behavior exactly.
  Merge amendment (2026-08-31): dispatch/inner FAILURE recording is
  doctrine (test-pinned) and stays always-on for writable stores — the
  gate governs only the success-anomaly branches; with anomalies off, the
  auto-logger initiates no writes by default, so the self-amplifying loop
  cannot re-enter through the failure branch.

### Episodic memory capabilities (2026-08-20/21)

- **Temporal supersession (T1/T6)** — current-value queries ("What's my
  current favorite X?") now resolve at read time: UserStatements carrying
  change markers ("switched to", "switched from", "used to", ...) are
  promoted in deterministic chronology order. Scoring untouched;
  non-current queries take the identical path. MemoraStrict T1/T6
  15%→50%, T9 +11.7pp; LongMemEval unchanged.
- **Contradiction detection (T8)** — `memory.episodic_search` reports a
  `conflicts` array when retrieved user statements carry explicit
  contradiction markers over a shared topic: both records with full
  provenance, never silently resolved. Dietary/alcohol vocabulary added
  to enrichment defaults. T8 0%→100%.
- **Cross-session synthesis (T10)** — new `memory.aggregate` tool:
  count, session_count, and session_span metrics over a full-text query,
  with rarest-term anchor narrowing so similar-but-unrelated turns don't
  distort spans. T10 0%→86.7%.
- **Protected top-K rerank mode** — `memory.episodic_search` with
  `rerank_alpha >= 2.0` fully reorders only the deterministic top-limit
  set by cosine similarity; set membership is fixed so recall@limit is
  preserved by construction (ConvMemory v2 pattern).
- **`current_resolution` flag** in episodic search output.

### Embedder resource safety (2026-08-21)

- **INT8-quantized embedder variants** — `WM_EMBEDDER_ORT_MODEL` names
  ending in `-q` (e.g. `bge-small-q`) select quantized ONNX models:
  ~75% smaller weights, INT8 SIMD execution. Chosen after FP32 inference
  at full logical-thread count OOM-crashed a 16GB machine during
  benchmark runs.
- **ORT thread cap** — default intra-op threads clamped to
  min(logical cores, 4); explicit `WM_EMBEDDER_ORT_THREADS` still wins.

### Benchmark tooling

- **MemoraStrict generator**: guaranteed change statements (previously
  questions could reference values never spoken — unanswerable),
  deterministic T2 topic sampling (PYTHONHASHSEED set-iteration),
  `--scale-turns N` scale-stress generation, current-value T7 phrasing.
- **`scripts/memorastrict_miss_analysis.py`** — zero-CPU static miss
  analysis joining scenario data against the resolution-layer logic;
  found and drove the "switched from" marker fix.
- **Curated smoke test** now covers `wm seal`/`wm verify` end to end
  (B5 complete): seal, clean verify, idempotence, tamper detection.

### v5.8.0 release stabilization (2026-08-20)

- **Tantivy schema-mismatch auto-migration** — stores created before the
  en_stem tokenizer change (commit `3be3e02`) previously failed to open with
  a hard `Schema error`. Now: a writable `SearchEngine::open` moves the old
  index aside (`tantivy.schema-mismatch.<millis>` sibling), creates a fresh
  index, and server startup rebuilds it from the canonical LMDB store, so
  upgrades are seamless. `wm reindex` also recovers such stores directly.
  A read-only open (e.g. `wm doctor --readonly` sharing) refuses to migrate
  and returns an error pointing at `wm reindex`. 3 regression tests cover
  writable migration + backup, read-only refusal without mutation, and
  no-migration on schema match. Verified end-to-end against a real Aug-7
  store: serve → migrate → rebuild → create + search round-trip, and
  `wm reindex` → 301/301 memories re-indexed.
- **Release gate re-run (2026-08-20, from `cargo clean`)**: fmt clean,
  3,570 tests passed, clippy `-D warnings` clean, release build clean,
  curated smoke test + clean-machine handshake + restart persistence +
  read-only enforcement passed on a fresh store and against the installed
  binary at `~/.local/bin/wm`.
- **Public-claims count correction**: the registry registers 237 tools
  (232 available in the default brain wave, 48 in the curated profile) —
  README/AGENTS previously claimed 229. Test count is 3,570 (was 3,513).

### Episodic retrieval — vocabulary enrichment (Phase 1)

- **Storage-time vocabulary enrichment** — hypernym maps (production→play/theater,
  mutt→animal, silent→fundraising, welfare→shelter, etc.) added to the episodic
  inverted index at ingestion time. All map keys and values are stemmed for
  consistent matching. Enrichment applies to lexical postings only, not to
  content used for embedding computation (per SelRoute finding that enrichment
  hurts embeddings).
- **Reverse enrichment (query expansion)** — for `UserStatement` records only,
  query terms are expanded via reverse hypernym lookup at scoring time. This
  bridges the vocabulary gap (e.g., query "theater" matches content "production")
  without boosting competing `AssistantResponse` turns.
- **Reverse match score bonus** — +0.05 per reverse-enrichment match for
  `UserStatement` records, breaking score ties in favor of answer turns that
  bridge the vocabulary gap.
- **Session-aware RRF boost** — turns from sessions with multiple matching turns
  get a small score boost (+0.02 per additional match, capped at 3).
- **Density restored in score** — density * 0.01 weight restored after temporary
  removal; gives shorter answer turns a tiny advantage that breaks ties in their favor.
- **Result**: 10q R@1 70% → 80% (Q4 fixed), R@5=100%, R@10=100%, MRR 0.85 → 0.90.
  50q R@1 76% → 82% (Q4, Q11, Q24, Q47 fixed; Q32 regressed rank 1→5), R@5=100%,
  R@10=100%, MRR 0.87 → 0.90. Zero LLM inference, CPU-only, no new dependencies.

### Episodic retrieval — Q32 fix and latency profiling (Phase 2)

- **Q32 regression fix** — removed the `"take"` action bridge from
  `VocabularyEnrichment::with_defaults()`. The bridge mapped
  `take → [enrolled, joined, attended, started]`, causing
  `reverse_enrich("attend")` to return `["take"]`. Since "take" is one of the
  most common English verbs, unrelated `UserStatement` turns received a +0.05
  reverse match bonus, outranking the correct answer turn (which matched 2/3
  query terms but had no reverse match). Fix: rank 7 → rank 1 for Q32.
- **50q R@1 82% → 84%** (Q32 fixed, no regressions). 8 remaining misses all at
  rank 2-3: Q7, Q9, Q16, Q31, Q33, Q34, Q38, Q42. R@5=100%, R@10=100%,
  MRR 0.90 → 0.91.
- **Embeddings confirmed unnecessary** — benchmark runs with `StubEmbedder`
  (no `WM_EMBEDDER_ENDPOINT`). `search_with_rerank()` falls back to
  `search_with_limits()` when embedder is unavailable. R@1=84% with pure
  lexical search, zero vector computation.
- **Latency profiling** — in-process warm search: ~1ms (10K records).
  Warm search via MCP JSON-RPC: ~35-50ms (includes serialization + dispatch
  pipeline). Process startup: ~53ms. Batch ingest (550 turns): ~1.6s.
  Benchmark per-question latency (~1.7s) is dominated by ingest, not search.
  Term cache is effective: cold search 0.99ms → warm 1.01ms (50 repeats).
- **search.rs cleanup** — removed duplicate `"edly"` entry in `simple_stem`
  suffix list.

### Episodic retrieval — tiebreaker tuning and targeted bridges (Phase 2 cont.)

- **Targeted vocabulary bridges** — added `bachelor ↔ undergrad ↔ college`
  and `computer ↔ science ↔ cs ↔ programming ↔ tech` hypernym bridges.
  These are narrow, domain-specific mappings that bridge the vocabulary gap
  for Q33 ("Bachelor's degree in Computer Science" → "undergrad in CS from
  UCLA") without the collateral damage of broad bridges.
- **Tiebreaker tuning** — `role_boost` increased 0.1 → 0.12, density weight
  increased 0.01 → 0.03. The density weight now provides meaningful
  differentiation between near-tied UserStatement turns (shorter, focused
  answer turns get a slightly higher score). The role_boost increase gives
  UserStatement turns a slightly larger advantage over AssistantResponse.
- **50q R@1 84% → 86%** (Q33 fixed, no regressions). 7 remaining misses all
  at rank 2-3: Q7, Q9, Q16, Q31, Q34, Q38, Q42. R@5=100%, R@10=100%,
  MRR 0.91 → 0.92.

## [5.8.0] — 2026-08-13

### Release hardening (boundary, storage, evidence)

- **Unknown compartments fail closed** — unrecognized compartment values no
  longer grant full access; read and write access is denied.
- **Store-wide read-only** — `--readonly` now refuses every tool that declares
  writes via the dispatch pipeline, and suppresses karma recording, friction
  auto-logging, and mutable-state persistence. Previously it protected only the
  Tantivy writer while LMDB mutations still succeeded.
- **Tool profile precedence** — `WM_TOOL_ALLOWLIST` > `--profile` >
  `WM_TOOL_PROFILE` > `curated` for `wm serve`. `wm daemon` and library
  constructors still default to `full`. The CLI no longer overwrites the
  documented environment path.
- **Store seal/verify** — `wm seal` writes an HMAC-SHA256 per-file
  manifest; `wm verify` reports mismatched, missing, or extra files.
  Detects accidental corruption, not an adversary who can replace
  `.seal_key`.
- **Search default** — OR + stemming-aware token-coverage replaces
  conjunction-by-default. `memory.search` is the public retrieval verb
  (BM25; hybrid fusion when an embedder is set). `memory.hybrid_recall`
  is a compatibility alias. Hybrid n=10 retrieval (not official
  LongMemEval QA) scored R@5=0.90 / R@1=0.40 vs BM25+stem 0.70 / 0.50.
- **Curated surface** — `nlu.shadow_report` and `tools.usage_report` are
  full-profile only. Stranger-install prefixes: memory, session, claims,
  transaction, gnosis, tools.list.
- **Profile-aware discovery** — `tools/list` describes the active profile with
  a registry-derived tool count instead of the hardcoded 229-tool archive text.
- **Exact transaction rollback** — `transaction.begin` snapshots complete
  `Memory` records with no 10,000-record truncation; rollback restores
  byte-equivalent records (original UUIDs, timestamps, hashes, coordinates,
  privacy flags, provenance) and keeps the transaction retryable when a restore
  fails; commit removes the rollback snapshot.
- **Storage consistency** — `MemoryStore::put` removes stale secondary-index
  entries on overwrite; `memory.update` recomputes content hashes; filtered
  reindex (`wm reindex --galaxy`) deletes and re-indexes only the selected
  galaxies instead of wiping the whole index.
- **Curated smoke test** — `scripts/curated_smoke_test.py` asserts the full
  curated workflow (memory, sessions, transactions, claims calibration,
  restart persistence, read-only enforcement) against the release binary and is
  wired into CI and the release workflow.
- **`wm quickstart` fix** — seeded memories are created through the dispatch
  pipeline so the Tantivy index is populated; the demo search previously
  returned nothing on a fresh store and printed empty previews.
- **Privacy enforcement** — `is_private` memories are excluded from MCP
  read/list/query/search/hybrid/vector/chat/batch responses (read reports
  `not_found`); `model_exclude` memories are filtered from reasoning,
  bicameral, imagination, and self-play context gathering.
- **Explicit claims routes** — `claims.add/resolve/status/list/calibration`
  aliases alongside the action-based `claims` tool.
- **Release checksums** — per-platform sha256 files generated and uploaded
  with release binaries.
- **Full-surface hygiene** — `bus.emit` now declares its bus/filesystem writes
  (`Resource::EventBus` added); `system.health` reports failed galaxies instead
  of claiming healthy; `session.start` NLU payload uses `title` (the old
  `name` key silently created "Untitled Session" entries); web tools clamp
  negative timeouts instead of panicking; tool stats track a true peak latency
  so the high-latency anomaly path can fire.
- **MCP tool annotations** — `tools.list` now reports `readOnlyHint` and
  `destructiveHint` derived from each tool's declared effects, so clients and
  registries can make safety decisions without knowing tool internals.
- **Release assets** — legal kit (SECURITY/PRIVACY/TERMS/COC/CITATION), voice
  and tone guide, MCP configuration guide, quickstart, registry listing kit,
  and an agent-facing model guide, plus public-claims and fresh-install gates
  in the release checklist.

## [5.7.7] — 2026-08-11

### Tantivy recall quality (parallel session)

- **Score thresholds** — `SearchOptions { min_score, relative_floor, relaxed }`
  + `search_opt()`; `memory.hybrid_recall` / `memory.search` accept `min_score`
  (default relative floor 0.05). The incident query ("smoke test from
  wmClient") now returns only genuinely relevant memories — no more
  zero-overlap garbage at 0.5–1.0 scores
- **Index-time sanitization** — null bytes skipped, printable-ratio < 0.9
  skipped, 8KB cap, control chars scrubbed; output-side scrub too
- **Stopword stripping** on queries (mirrors the Antigravity client list)
- **`wm reindex` CLI** — rebuilds the tantivy index from LMDB with
  auto-backup, `--galaxy`, `--dry-run`; live dry-run found 2,833 garbage
  artifacts skipped (2,799 in codex — migration leftovers)
- `sanitize_tantivy_query` v2 (quotes only reserved-syntax terms);
  Phase-2 fallback = relaxed OR + token-coverage filter (replaces the
  100-memory scan lottery); `memory.search` verifies hits against LMDB
  (deleted memories gone); `normalized_score` on results
- `wm serve --readonly` — no exclusive index lock, multiple processes
  can share the store
- 3,424 tests passing (was 3,391; +33), 0 clippy warnings

### Claims ledger (evening review)

- Graded claims 0020–0025: STRONG 0020/0024, MODERATE 0021/0023,
  FALSIFIED 0025 (honest-miss discipline). REVIEW.json now covers 21/32
- No status changes — all pending claims kept (no new signals tonight)

### Read-only diagnostics + always-on daemon

- `wm stats` / `wm doctor` / `wm brain-wave` / export now open the store
  read-only, so they work while the daemon holds the index (was LockBusy)
- `whitemagic-daemon.service` systemd unit — always-on consciousness
  against the live store (cycle 300s, dream 600s, watchdog 120s)

### NLU

- `simulation.calibrate` description fix — "run a simulation" no longer
  near-ties with it (0.744 vs sim.mc 0.740); now cleanly routes to sim.mc,
  0 regressions on the judged set
- near-tie debug logging (best/second tool) in `route_with_margin`
- `wm` PATH stub fixed — broken Python wrapper replaced with a launcher
  preferring release, falling back to debug

## [5.7.6] — 2026-08-11

### OATS persistence (NLU learning loop closed)

- `save_mutable_state` now writes the router's OATS outcome stats to
  `mutable_oats.json`; `load_mutable_state` restores them on startup —
  the outcome-aware refinement survives restarts for the first time
- `register_meta_tools_with_router` returns the router so the server can
  persist it; regression test `e2e_oats_persistence_roundtrip`
- Test isolation fix: tests passed the tempdir root to `with_defaults`,
  putting `self_model.json` etc. in shared `/tmp` — cross-test pollution
  made `e2e_mutable_state_persistence_roundtrip` flaky (6 vs 2 samples).
  Tests now use a nested store dir (`test_store_path`)

### NLU router descriptions (systematic fix)

- ~45 tools had no explicit `description()` and embedded to one of 28
  shared Gana-level vectors (all conformal.*, selfmodel.*, several
  others) — the margin calculation collapsed on whole families.
  `anchored_descriptions` now synthesizes a description from the dotted
  tool name for Gana-fallback tools
- All 6 `mc.*` / simulation tools (surrogate, optimize, rare_event, sde,
  superforecaster, simulation.calibrate) got proper descriptions —
  they previously shared the identical Gana vector ("Foresight,
  simulation, convergence"), guaranteeing near-ties
- Verified margin behavior: "run a simulation" → sim.mc 0.74 with margin
  0.011 is a genuine near-tie, not a description artifact; a confidence
  floor on the margin fallback was tried and reverted (net regression)
- Judged dispatch set (56 queries, real registry tools only): nomic 31,
  bge 33, anchored+synthesized 38 (42 counting correct `?`-status rows)

### Daemon

- Removed dead `serve_mcp` config — documented and printed but never
  consumed by `run_daemon` (daemon cycles dispatch tools directly and
  do not serve MCP)

### Counts

- 3,400 tests passing (0 failed), 0 clippy warnings, fmt clean

## [5.7.5] — 2026-08-11

### Configurable dispatch rate limits

- `RateLimiterConfig` + `WM_DISPATCH_GLOBAL_RPM` / `WM_DISPATCH_TOOL_RPM` /
  `WM_DISPATCH_BURST` / `WM_DISPATCH_TOOL_OVERRIDES` env vars, wired into
  the serve pipeline with a startup log line; defaults unchanged (300/60/10).
  The `wm` meta-tool was capped at 70 calls/min — the shadow collector now
  drives 115/115 queries with zero rate-limit losses. 4 new tests

### Intent-anchored NLU router

- `INTENT_ANCHORS`: per-tool natural phrasings appended to embedded tool
  descriptions ("users say: ...") — fixes top-1 collapse on common queries
  ("list tools" → tools.list, "fetch this webpage" → web.fetch, "show my
  karma" → karma.report)
- Prefix-route bonus removed from the anchored path (it fought the anchors);
  `route_with_margin` + `MIN_MARGIN = 0.02` defers to TF-IDF on near-ties
- Embedder A/B (115-query corpus): bge-small-en-v1.5 vs nomic-embed-text —
  near-tie quality; bge wins operationally (canonical model, 37MB vs 84MB,
  ~20% faster, matches `WM_EMBEDDER_DIM=384` default)
- Live shadow collection: `whitemagic-embedder.service` systemd user unit,
  `scripts/live_shadow_serve.sh`, rust-native MCP config → live store with
  embedder env; real MCP sessions accumulate shadow stats, persisted on
  shutdown
- `scripts/collect_shadow_data.py`: `--cooldown-every` / `--dim` flags

## [5.7.4] — 2026-08-11

### Forensic memory recovery

- **`wm_forensic`** binary (`crates/wm-mcp/src/bin/wm_forensic.rs`) — carves
  deleted memories out of raw LMDB pages (deletes free pages but don't zero
  them until reuse). `extract` scans data.mdb for target UUIDs and decodes
  msgpack `Memory` nodes (direct + overflow-page references); `restore` puts
  them back with original IDs + tantivy re-indexing. E2E verified:
  create → delete → carve → restore → readable

### NLU routing (first real shadow data)

- **`EmbeddingRouter::with_descriptions`** — embeds the live registry's prose
  descriptions (228 tools) instead of static keyword-mashup profiles (169)
- **Margin fallback** — `route_with_margin` + `MIN_MARGIN = 0.02`; near-tie
  embedding choices defer to the TF-IDF router
- First shadow-mode data collection (115 queries, nomic-embed via llama-server):
  dangerous misroutes eliminated — "show my karma" no longer routes to
  `karma.clear` (destructive), "research the topic of memory consolidation"
  no longer routes to `memory.delete` (destructive)
- **`nlu.shadow_report` reachability fixed** — was registered top-level only
  and unreachable through `wm(route=...)` (MCP exposes only `wm`); now
  registered inside the meta-tool routing registry + regression test
- `scripts/collect_shadow_data.py` — shadow-mode data collection driver

### Claims ledger (morning review)

- **claim-0029** (conf 0.65) — org-injectable policy hooks become standard
  after Anthropic's inference hooks beta
- **claim-0030** (conf 0.70) — per-agent spending caps/wallets become standard
  after Cloudflare Wallets/cloudflare.pay
- **claim-0031** (conf 0.60) — EU AI Act Art. 50 first significant enforcement
  within 12 months
- 32 claims total (19 validated, 1 falsified, 12 pending); live ledger == docs

### Docs

- NEXT_SESSION.md rewritten for v5.7.3-era state; PROGRESS.md + AGENTS.md
  counts corrected (229 tools, 3,391 tests); shadow-mode analysis note updated
  with both data runs

### Counts

- 3,391 → **3,394 tests passing, 0 failed** (+3: with_descriptions coverage,
  route_with_margin, shadow_report reachability)
- 0 clippy warnings (default + transport), fmt clean

## [5.7.3] — 2026-08-10 (evening)

### Session ops — the last Phase-1 gap (v26 parity)

- **`session.record`** — record a turn (role user/ai, turn_type, importance,
  session_id) as a sequenced session memory in the Sessions galaxy
- **`session.replay`** — full / selective (turn_types + min_importance) /
  progressive (token_budget) replay modes
- **`session.continuity`** — the last N turns of the most recent prior
  session ("where we left off" across sessions)
- **`session.handoff`** — transfer / accept / list: package a session with
  its context summary for continuation on another device

### External merkle anchors

- **`karma.anchor`** gains `publish_path` — appends a chained record
  (root, entry_count, chain_head, prev_hash=SHA-256 of the previous
  record) to a versioned JSONL log. With the log in a git repo, the commit
  history provides out-of-band verifiability the runtime cannot rewrite.
  Live chain (38 entries) anchored to `anchors/karma_anchors.jsonl`

### Claims ledger: evening review (critical pass, 29 claims)

- **Date-arithmetic bug found and fixed** — `epoch_day_from_str` had a
  constant +1,721,451-day offset (days since year 1, not 1970);
  chrono-based fix + regression test; all ledger dates migrated
- **claim-0005 reclassified to pending** — "10x-class efficiency gains"
  was validated on 27% cost reduction (overclaim)
- **claim-0009 kept validated** — event date (2026-05-08) verified before
  its falsification deadline (2026-05-31) after date correction
- **Morning claims merged** (claim-0020+) — including the ledger's first
  honest falsification (the "one-off" claim falsified by Meta's incident)
- **Ledger versioned in the repo** — `docs/CLAIMS_LEDGER.json` +
  `docs/CLAIMS_LEDGER.md` (rendered) + `docs/CLAIMS_LEDGER_REVIEW.json`
  (per-claim grading: 5 STRONG, 5 MODERATE, 4 WEAK, 1 reclassified)
- Calibration: mean Brier 0.078, hit rate 0.950 vs confidence 0.735
  (+0.215 overconfident — inflated by generous validations)

### Counts (corrected)

- **229 tools** (session.record, session.replay, session.continuity,
  session.handoff) — prior entries understated the registry (real count
  at v5.7.2 was 225, not 212); corrected across README/AGENTS/docs
- 3,384 → **3,391 tests passing, 0 failed** (+7)
- 0 clippy warnings (default + transport), fmt clean, cargo-deny green

## [5.7.2] — 2026-08-10

### Ed25519 Sangha mesh (pulse-verification Tier-0 port complete)

- **`wm-sangha::crypto`** — `MeshKeyPair` (Ed25519 via ed25519-dalek):
  per-peer keypairs replace the shared HMAC secret. A compromised peer can
  **never** forge another peer's identity or messages
- **ChatMessage** — carries the sender's public key; `verify_signature()`
  (self-consistent) + `verify_as_sender(bound_key)` (identity binding);
  `send_as` (relay signing); `inject_signed` (store network-signed messages
  as-is); `verify_channel_bound` / `verify_all_bound` enforce binding —
  impostor keys are rejected, not just tampering
- **PeerIdentity** — `PeerInfo` carries its Ed25519 public key; the registry
  binds the first-seen key and **refuses re-registration with a different
  key** (identity theft); `bound_public_key` / `identity_bindings` feed the
  community read path
- **Auto-quarantine policy** — `AutoQuarantineConfig` (default: 3 consecutive
  verification failures, trust floor 0.2): `record_verification_failure` and
  `quarantine_if_untrusted` cut the bad apple off without a human decision;
  the community defends itself
- **Signed transport** — `SanghaState` carries the node keypair; `send_chat`
  RPC verifies signature + sender binding before storing (forged relays
  rejected with an RPC error); signed heartbeats bind identities; legacy
  unsigned relays still accepted (trusted transport)
- **Transport-mode containment test** — two live TCP nodes: honest signed
  chat verifies, forged message claiming a bound ID is rejected, identity
  theft at registration is refused, and the community board stays clean
- **Containment harness extended to 14 vectors** (auto-quarantine on repeated
  failures + trust-floor decay)

### Claims calibration scorecard

- Ledger reviewed end-to-end: 9 claims (5 validated, 1 falsified, 3 pending),
  77.14 points; mean Brier 0.082; the only miss came at the lowest confidence
  (0.5) — calibrated shape; 0.6–0.8 bin overperforms by +0.275 (watch item)
- Full review artifact: the claims-and-scorecards review doc (kept locally; not part of the public tree)

### Counts

- 3,379 → **3,384 tests passing, 0 failed** (+5); 137 with `transport`
- 0 clippy warnings (default + transport features), fmt clean

## [5.7.1] — 2026-08-10

### Sangha quarantine — the bad-apple rule

- **Quarantine subsystem** — `PeerDiscovery::quarantine/release_quarantine/
  is_quarantined/quarantined` with visible `quarantine_reason`; quarantined
  peers cannot re-register (`discover_signed` refuses until release)
- **Community protection** — `SanghaChat::read_trusted` (verified + non-
  quarantined senders only), `SanghaChat::purge_sender` (bad apple's words
  removed from the logs), `ResourceLockManager::revoke_peer` (its leases
  released so the community is never held hostage)
- **`sangha.quarantine` tool** (211 → **212 tools**) — actions
  `quarantine` (peer_id + reason; revokes locks, purges messages),
  `release`, `list`
- **Containment harness extended to 12 vectors** — the bad-apple scenario:
  a provisioned peer goes rogue; quarantine isolates it (messages filtered,
  locks revoked, rejoin refused) while the community keeps working;
  explicit release restores a reformed peer
- **`docs/SANGHA_SECURITY.md`** — threat model (July 2026 agent incidents +
  the v2 incident), design principles, quarantine semantics, harness table,
  honest limitations (HMAC vs Ed25519, default mesh key, manual quarantine)

### Counts

- 211 → **212 tools** (sangha.quarantine)
- 3,377 → **3,379 tests passing, 0 failed** (+2)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.7.0] — 2026-08-10

### Governance & security tools (v26 `dharma.escalate` / `karma.*` / `sandbox.*` / `tx_firewall.*` parity)

- **Dharma escalation** — `wm-governance::escalation` (`EscalationQueue`):
  ambiguous verdicts (Advise/Correct) escalate to a human review queue;
  tools `dharma.escalate`, `dharma.review_queue`, `dharma.resolve_review`
  (allow/warn/block + score); queue persists to `<store>/escalation_queue.json`
- **Karma chain surface** — `karma.verify_chain` (chain-integrity audit,
  tamper detection) and `karma.anchor` (publish Merkle checkpoints of the
  whole chain; `anchor`/`status` actions; anchor history persisted to LMDB)
- **`sandbox.set_limits` / `sandbox.limits`** — runtime tuning of the
  resource-limit config (per-minute write/spawn/network budgets, novelty
  window, repeats, human-review requirement); `ResourceRules::config` is now
  runtime-mutable
- **`tx_firewall.set_policy` / `tx_firewall.status`** — transaction firewall
  policy (allowed tool prefixes, max ops, rollback confirmation); persisted
  to `<store>/tx_firewall_policy.json`

### ACS Output checkpoint (L2/L3 egress policy)

- `DharmaPolicy` gains `tier2_deny_unknown_egress` + `egress_allowlist`
  (deny egress to unknown hosts, subdomain matching) and
  `tier3_output_validation` + `output_max_bytes`; enabled in the strict
  profile; `check_egress(host)` + `dharma.acs egress` action; egress
  controls exported in the ACS policy YAML — the last open row of the
  ACS_ALIGNMENT gaps table

### Code structure graph (v26 `code.*` / `fragment.search` parity)

- **`wm-tools::expansion::code`** — dependency-free code graph: regex-based
  symbol extraction (Rust/Python/JS/TS/Go/Java/C/C++/Ruby/Shell/Zig/Julia),
  cross-file call edges, imports, inheritance; tools `code.graph`,
  `code.query` (callers/callees/path/explain/god nodes/search),
  `code.affected_by` (reverse call-graph BFS), `fragment.search`
  (symbol + line-level fragment search); bounded file walk (50K files,
  1MB/file), skips target/node_modules/.git

### Signed Sangha mesh (pulse-verification port)

- `wm-core::sign_hmac` / `verify_hmac` shared HMAC-SHA256 primitives
  (attestation now built on them)
- **`ChatMessage` signatures** — every sangha message is signed with the
  mesh key (HMAC-SHA256); `sangha.chat` gains `verify` action reporting
  checked/verified/rejected; the server wires the mesh key at startup
- **`PeerInfo` identity signatures** — `PeerDiscovery::discover_signed`
  rejects unsigned or forged peer identities (wrong key, tampered
  authority); `verify_peer` for stored identities
- **Containment harness** (`wm-sangha::containment`) — deterministic
  simulation of a multi-agent mesh with an adversarial peer: 8 attack
  vectors (forged identity, forged/unsigned messages, authority
  escalation, out-of-scope tool execution, memory writes, delegation,
  lock theft) all contained by the governance layer; motivated by the
  July 2026 agent-incident reporting (message-board swarms, cryptographic
  signing proposals)

### Fuzz hardening

- **`web_parsers` fuzz target** — fuzzes `strip_html`, `bing_decode`,
  `ddg_target`, `resolve_url`, `percent_encode_query`,
  `parse_bing_results`; committed seed corpus (real Bing HTML + edge
  cases); 4 real bugs found and fixed: relative `ck/a` decode targets,
  byte-index panic on multibyte input in `ddg_target`, entity decoder
  swallowing tags inside script content, stray `;`/unknown-entity leaks
- `just fuzz` recipe + CI fuzz workflow extended to the new target
- Web parser functions exposed as `pub` (dependency-free, fuzzable)

### Counts

- 211 tools (unchanged; `sangha.chat` gained a `verify` action)
- 3,352 → **3,377 tests passing, 0 failed** (+25)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.6.0] — 2026-08-09

### ACS compliance surface (Microsoft Agent Control Specification)

- **`wm-governance::acs`** — the five-checkpoint model (input / llm / state / tool_execution / output) mapped onto Dharma governance: `AcsCheckpoint`, `AcsAction` (allow→block severity ladder), `AcsRule` → `PolicyRule` conversion with sutra + OWASP mapping
- **Policy YAML import/export** (`acs-yaml` feature, `serde_yaml`): `DharmaPolicy::to_acs_yaml()` renders the live policy as portable ACS policy YAML; `import_acs_yaml()` parses ACS policies into dharma rules unchanged. Feature-gated: `--features wm-governance/acs-yaml`
- **`dharma.acs` tool** (202 → **204 tools**, with `claims`) — actions: `report` (per-checkpoint coverage table + percent), `export` (policy as ACS YAML), `import` (ACS YAML → dharma rules)
- **`AcsComplianceReport`** — per-checkpoint coverage with `coverage_percent()`, mirroring the OWASP coverage surface; `docs/ACS_ALIGNMENT.md` published as the positioning asset

### Prescience claims ledger (v26 `temporal_db` port)

- **`wm-simulation::claims`** — `ClaimsLedger` with dated, falsifiable claims: `record` (source date + mandatory falsification criterion), `resolve` (validation event → validated credits lead weeks, 1 week = 1 point; falsified recorded as a miss), `status` (totals + per-domain breakdown), `list` (domain/status filters)
- **`claims` tool** — actions: `add`, `resolve`, `status`, `list`; ledger persists to `<store>/claims_ledger.json` on shutdown, restored on startup
- The falsified count is always reported alongside the score — honesty is part of the store, not an afterthought

### Self-model persistence + doctor drift health

- **`SelfModel::to_json()` / `from_json()`** — full state persistence: per-metric
  histories with timestamps, alert rules, and confidence calibrator state. A
  restarted process resumes forecasting, drift alerts, and confidence exactly
  where it left off. Persisted to `<store>/self_model.json` on shutdown,
  restored on startup
- **`wm doctor` live drift health** — reads the persisted self-model and reports
  latest conformal coverage + Brier score with the same thresholds as the alert
  engine (0.85/0.80 coverage warning/critical, 0.15/0.30 Brier), including
  trend direction and exit code contribution on critical drift. The
  conformal → monitor → doctor loop is now closed
- E2E: mutable-state persistence roundtrip now also verifies self-model
  history restore

### Web research tools (v26 `web_research` parity, phase-1 gap port)

- **`web.fetch`** — fetch a URL and return clean text (title, content,
  status code, duration); default 30K chars
- **`web.deep_fetch`** — full-content retrieval up to 200K chars
- **`web.search`** — no-API-key web search via the Bing HTML endpoint
  (`li.b_algo` parsing, `ck/a` click-link decoding to real URLs)
- **`web.search_and_read`** — search + fetch top results in one call
  (`fetched_count` reports how many pages were retrieved)
- Safety: every URL (and every redirect hop) passes the `is_url_safe` SSRF
  guard; bodies are bounded (1MB raw budget, `Read::take` truncation);
  timeouts bounded; DuckDuckGo's bot-challenge (HTTP 202) is detected and
  degrades to an empty result list instead of an error
- Dependency-free HTML tooling: compact tag/entity stripper + RFC 3986
  relative-URL resolution + base64url decoder (no scraper crate)

### Research tools (v26 `research_*` parity, phase-1 gap port)

- **`research.topic`** — deep research pipeline: search → fetch top sources →
  extractive key-term analysis (cross-source frequency, stopword-filtered) →
  synthesis; stores the report in the Research galaxy when
  `store_memories: true` (returns `memory_id`)
- **`research.repo`** — GitHub repo deep-read: raw README candidates first,
  rendered page fallback; returns description, section outline, full content
- **`research.rabbit_hole`** — bounded recursive spiral: search the topic,
  extract unfamiliar terms from titles/snippets, search each term, fetch top
  results, recurse one level deeper, synthesize the whole exploration
  (depth capped at 3, term parallelism capped at 12)
- All synthesis is extractive (no LLM dependency) — the pipeline works
  air-gapped against the search backend

### Counts

- 208 → **211 tools** (research.topic, research.repo, research.rabbit_hole)
- 3,345 → **3,352 tests passing, 0 failed** (+7)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.5.0] — 2026-08-08

### MC suite completion (v26 `mc.*` parity)

- **`mc.rare_event`** — rare-event probability estimation:
  - *Subset simulation* (Au & Beck): Metropolis–Hastings conditional sampling with the correct φ(x')/φ(x) acceptance ratio; verified against the analytic chi-square tail P(χ²₂ > 9) ≈ 0.0111
  - *Importance sampling* with exact likelihood-ratio weights and coefficient-of-variation diagnostics
- **`mc.sde`** — SDE solvers: Euler–Maruyama and Milstein (with the ΔW²−Δt correction for GBM), GBM + Ornstein–Uhlenbeck drift, terminal statistics (mean/std/percentiles/min/max), and two-level MLMC extrapolation (coupled seeds)
- **`mc.superforecaster`** — the full orchestrator:
  - *LHS* (Latin Hypercube Sampling with Fisher–Yates stratum permutations)
  - *PCE* surrogate (Hermite basis, normal-equation least squares) with analytic Sobol' first-order/total-effect indices
  - *Bayesian optimization* refinement on top
  - Verified: recovers linear surfaces (R² > 0.99), ranks dominant variables, finds 2-D optima

### GP hyperparameter fitting

- **`GaussianProcess::log_marginal_likelihood`** — `−½yᵀK⁻¹y − ½log|K|` from the existing Cholesky factor
- **`GaussianProcess::fit_hyperparameters`** — optimizes (ℓ, σ_f², σ_n²) in log space using the crate's own BayesianOptimizer (dogfooding); fixes the fixed-hyperparameter limitation
- `mc.surrogate` gains `fit_hyperparameters: true` + `hp_iterations` — verified to recover the length scale of high-frequency data

### Brier → self-model monitoring (feedback triangle complete)

- **New `BrierScore` self-model metric** (lower is better, warning 0.15 / critical 0.3 — the v26 "good calibration" threshold)
- `simulation.calibrate` scorecard now records the average Brier score into the self-model and surfaces drift alerts — alongside `ConformalCoverage`, the calibration subsystem is now fully monitored: conformal (quantification) → Brier (measurement) → selfmodel (monitoring)

### Counts

- 199 → **202 tools** (mc.rare_event, mc.sde, mc.superforecaster)
- 3,284 → **3,311 tests passing, 0 failed** (+27)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.4.0] — 2026-08-08

### Conformal drift monitoring

- **`conformal.monitor` tool** — evaluate empirical coverage on recent observations (classification sets or regression intervals + truths), returns coverage report, `drift` flag, and live drift alerts
- **`ConformalCoverage` self-model metric** — each monitor run records empirical coverage into the self-model; the alert engine fires warning/critical drift alerts when coverage persists below 0.85/0.80 (default rules, per-alpha overridable)
- **Auto-persistence** — conformal calibration state now saves to `<store>/conformal_store.json` on shutdown and restores on startup (`wm doctor` section 10 reads the same file — the persistence loop is closed)
- `CoverageReport::evaluate_sets` — new list-based evaluator in wm-conformal

### Brier scorecard (`simulation.calibrate`)

- **New `wm-simulation::calibration` module** — `CalibrationStore` (record/resolve/scorecard), `CalibrationPrediction`, `BrierScorecard` with the **Murphy decomposition**: Brier score, reliability, resolution, uncertainty, and Brier skill score (BSS) vs. climatology — beyond v26's basic average
- **`simulation.calibrate` tool** with actions `record` / `resolve` / `scorecard`; historical calibration gap feeds a small adjustment into future predictions (v26 parity)
- Calibration state auto-persists to `<store>/calibration_store.json` across restarts

### GP surrogate + Bayesian optimization

- **New `wm-simulation::bayesian` module** (pure Rust, no external linear algebra):
  - `GaussianProcess` — RBF-kernel regression with Cholesky solve, posterior mean/variance, numerical jitter
  - `expected_improvement` — EI acquisition with exploration bias
  - `BayesianOptimizer` — random init → GP fit → EI-guided candidate search
  - `Expr` — tiny safe expression evaluator (`x[0]`, `+ - * / ^`, `sin/cos/tan/exp/log/sqrt/abs`, `pi`, `e`) with structural validation, unary minus, and correct `-x^2 = -(x^2)` precedence
- **`mc.surrogate` tool** — fit a GP response surface, predict with uncertainty at query points
- **`mc.optimize` tool** — Bayesian optimization over `param_ranges` with a `fitness_expr` (e.g. `"-(x[0] - 3)^2 + 5"`), full iteration trace in the response

### Hardening batch

- **Time-windowed rate limiting at the MCP boundary** — `RateWindow` (sliding 60s window, default 600 req/min, `wm serve --rate-limit`); complements the per-connection `RequestBudget`; throttled requests get `-32000` with `retry_after_secs`
- **`wm doctor` exit codes** — real issue counting (missing store, corruption, missing Tantivy index, conformal/calibration problems) with exit code 1 on any issue, 0 when healthy; useful for health-check automation
- **CI fuzz corpus regression** — fuzz workflow now replays the committed seed corpora (`-runs=1000`) before the 30s timed runs

### Counts

- 195 → **199 tools** (conformal.monitor, simulation.calibrate, mc.surrogate, mc.optimize)
- 3,240 → **3,284 tests passing, 0 failed** (+44)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.3.0] — 2026-08-08

### Boundary hardening (MCP input limits + request budget)

- **Validation layer now enforced** — `validate_request`/`validate_tools_call` existed but were never wired into the request path; SSRF, path traversal, injection, and the 64KB params cap were dead code. All requests now pass boundary validation in `handle()` before any dispatch: malformed structure → `-32602`, unsafe URL → SSRF rejection, traversal → rejection, oversized params → rejection
- **Per-session request budget**: `RequestBudget` (default 10,000 requests/connection, `0` = unlimited), enforced at the boundary with `-32000` when exhausted. Configurable via `wm serve --max-requests`
- **Bounded stdin reads**: raw request lines capped at 1MB (`MAX_REQUEST_SIZE`) in both sync `run()` and async `run_async()` — prevents unbounded allocation from a malicious client (drains to EOL and responds `-32600`)
- New public API: `RequestBudget`, `MAX_REQUEST_SIZE`, `MAX_PARAMS_SIZE`, `MAX_STRING_LEN`, `DEFAULT_MAX_REQUESTS_PER_SESSION`

### Daemon watchdog

- **Stall detection**: watchdog thread monitors the main-loop heartbeat; if no tick within `watchdog_timeout` (default 60s, `0` = disabled), logs CRITICAL, grants a 10s grace window for state saving, then force-exits (`exit(1)`) so a supervisor (Docker `restart` / systemd `Restart=always`) restarts the daemon
- **Panic resilience**: all five heavy components (cycle sweep, dream, codegen, research, self-play) wrapped in `catch_unwind` — a panic in one component no longer kills the daemon
- Configurable via `wm daemon --watchdog-timeout` / `config.toml [daemon] watchdog_timeout_secs`

### Fuzz corpus seeds (committed)

- **76 curated seeds across all 7 targets** (was: only auto-generated nlu_classify inputs, nothing tracked) — seeds committed as `seed_*` files so CI bootstraps coverage instantly; regenerated sha1 artifacts stay ignored
- **Fuzz build fix**: `serde` was missing from `fuzz/Cargo.toml` deps — `json_rpc_parse` target did not compile
- **`--all-features` fix**: `wm-polyglot` enabled jlrs without selecting a Julia version feature (jlrs-macros hard-error); added `julia-1-10`

### Tooling

- **`wm doctor` conformal calibration health** (section 10): reports classifier/regressor/APS fitted status, sample counts, and alphas from `<store>/conformal_store.json`; guides calibration/persistence when absent
- **Count correction**: tool registry is 195 (docs previously said 192)
- **Doctest fix**: `SplitConformalClassifier` doc example used the pre-`&[f64]` API and failed to compile

### Counts

- 3,212 → **3,240 tests passing, 0 failed** (28 new: budget 5, boundary 5, bounded-line 6, watchdog 3, doctest 1, +8 config/daemon)
- 0 clippy warnings, fmt clean, cargo-deny all green

## [5.2.2] — 2026-08-08

### Conformal Prediction (net-new feature)

- **New crate `wm-conformal`** — distribution-free uncertainty quantification with finite-sample coverage guarantees (present in neither v26 nor v5 before)
- `SplitConformalClassifier`: label prediction sets, nonconformity `1 − score`
- `SplitConformalRegressor`: value intervals, nonconformity absolute residual
- `AdaptivePredictionSets` (Romano et al. 2020): smaller sets for calibrated models, with the required uniform tie-break term
- `CoverageReport`: empirical coverage evaluation for drift monitoring
- 7 new MCP tools: `conformal.fit_classifier`, `conformal.fit_regressor`, `conformal.predict_set`, `conformal.predict_interval`, `conformal.status`, `conformal.export`, `conformal.import`
- Coverage guarantee statistically verified: ≈ 1−α averaged over 40 calibration draws × 80K test points (classifier 0.90, regressor 0.95, APS ≥ 0.89)
- 20 new tests; total 3,212 passing, 0 failed

### Hardening

- **Daemon SIGTERM handling**: graceful shutdown (karma flush + learned-state save) on SIGTERM for Docker/systemd, alongside existing SIGINT
- **Audit of production unwraps**: all 31 remaining sites confirmed logically guarded (length-checked slices, is_empty guards, checked_sub)
- 0 clippy warnings, fmt clean, all cargo-deny checks passing

### Tool surface

- 185 → 192 tools (7 conformal)
- Dependency audit: 2 vulnerabilities → 0 (pyo3 0.22→0.29, tantivy 0.22→0.26)
- 72 lock()/read()/write().unwrap() panic sites → graceful degradation

## [5.2.1] — 2026-08-10


### Karma Ledger Optimization & Phase 7 Benchmarks

#### Karma Write-Behind Batching
- **Batched LMDB writes**: `KarmaLedger` buffers `record()` calls in memory and flushes via single LMDB transaction (`flush_threshold=16` default)
- **Benchmark results** (criterion, release profile):
  - `karma_record_batched`: 97.7 µs/call (batched, threshold=16)
  - `karma_record_synchronous`: 1.07 ms/call (threshold=0, flush every record)
  - **10.9x throughput improvement** (batched vs synchronous)
  - `karma_flush_16_entries`: 314.7 µs per batch flush (16 entries in one LMDB transaction)
  - `dispatch_noop_with_karma`: 168.2 µs (full pipeline + karma record)
  - `dispatch_noop_no_karma`: 1.25 µs (pipeline overhead without karma)

#### Mutable Structure Benchmarks (13 criterion benchmarks)
- **GanaRegistry**: record_usage 228 ns, record_co_usage 1.02 µs, co_usage_count 171 ns, analyze_drift 80 ns, serialize 1.13 µs, deserialize 1.61 µs
- **LearnedDreamCycle**: record_phase 488 ns, phases_to_run 457 ns, update_phase_order 568 ns, serialize 3.71 µs, deserialize 5.45 µs
- **LearnedCycleStrategy**: record_cycle 362 ns, cycles_to_run 29 ns, update_priority_order 390 ns, serialize 3.97 µs, deserialize 3.81 µs

#### Daemon Karma Flush on Shutdown
- **Explicit `flush()` call**: Daemon's graceful shutdown now explicitly flushes the karma ledger before saving mutable state, ensuring no pending batched entries are lost when the process exits
- **Root cause**: `KarmaLedger::Drop` flushes, but the daemon holds `Arc<KarmaLedger>` inside `McpServer` — `Drop` doesn't fire until the server itself is dropped, which is outside `run_daemon`'s scope

#### E2E Integration Test
- **`pipeline_karma_batched_e2e`**: Full dispatch cycle with 20 tool calls (10 honest + 10 wasteful), verifies pending buffer count, total_debt accuracy (2.0), chain integrity after flush, and persistence across ledger instances

### Metrics
- **185 tools** (unchanged)
- **3,168 tests** (up from 3,167: +1 E2E karma batching test)
- **0 clippy warnings**, fmt clean

## [5.2.0] — 2026-08-10

### v5 Strategy Implementation (Phases 5–6)

#### Phase 5: Self-Play Training Loop ✅
- **`SelfPlayLoop`** (`wm-bicameral/src/self_play.rs`, ~1,650 lines): proposer → solver → verifier → training data collection loop
- **`TaskProposer`**: grounded/ungrounded task generation with memory context, 5 task types (CodeGeneration, ToolDispatch, Reasoning, Memory, Creative)
- **`TaskSolver`**: attempts to solve proposed tasks using bicameral handlers
- **3 Verifier implementations**: `SelfVerifier` (LLM self-critique with calibration), `ExactMatchVerifier`, `ToolResultVerifier`
- **`LoRAAdapterManager`**: hot-swap adapter management with versioning and min-sample thresholds
- **`SelfPlayConfig`**: configurable cycle count, task types, consecutive failure limits, adapter update thresholds
- **`SelfPlayStats`**: accuracy tracking, per-task-type success rates, difficulty trends, adapter update history
- **3 MCP tools**: `selfplay.run`, `selfplay.status`, `selfplay.export` (`wm-tools/src/expansion/self_play.rs`)
- **Daemon integration**: `--selfplay-interval` CLI flag, self-play cycle in daemon main loop with memory grounding
- **27 new tests**: task proposer, solver, verifiers, LoRA adapter, full cycle, multi-cycle, training data export, stats
- **1 benchmark**: `self_play_bench` (single cycle ~100µs, 20 cycles ~134µs)

#### Phase 6: Mutable Structures ✅
- **`GanaRegistry`** (`wm-core/src/mutable.rs`): Gana taxonomy drift based on co-usage patterns
  - Co-usage matrix with string keys for JSON serialization
  - Drift threshold triggers suggested merges with confidence scores
  - Per-Gana usage counts and rolling success rates
  - `analyze_drift()` returns top-N reorganization suggestions
- **`DynamicGalaxyRegistry`**: dynamic galaxy creation from memory clustering
  - Configurable min cluster size, max galaxies, prune threshold
  - Auto-pruning of ineffective galaxies
  - Effectiveness tracking per dynamic galaxy
- **`LearnedDreamCycle`**: learned dream cycle phase selection
  - 12-phase effectiveness tracking (runs, useful results, avg improvement, avg duration)
  - Phase reordering by effectiveness score
  - Ineffective phase filtering (configurable threshold + min runs)
- **`LearnedCycleStrategy`**: learned autonomous cycle strategies
  - 4 strategies: FixedOrder, PriorityBased, BestOnly, Adaptive
  - Auto-transitions from FixedOrder to PriorityBased after min_runs
  - Per-cycle-type effectiveness tracking with proposal counts
  - Priority order updates based on effectiveness scores
- **31 new tests**: GanaRegistry (7), DynamicGalaxyRegistry (5), LearnedDreamCycle (6), PhaseEffectiveness (1), LearnedCycleStrategy (7), serialization (4), CycleEffectiveness (1)

### Metrics (v5 Phases 1–6)
- **14 crates** (unchanged)
- **179 tools** (176 + 3 self-play)
- **3,142 tests** (up from 3,080; 31 Phase 6 + 4 E2E wiring)
- **0 clippy warnings**, fmt clean
- **~3,400 lines new code** (Phase 5: ~1,950, Phase 6: ~1,200, Wiring: ~250)

### Phase 7: Polish & Verification (In Progress)
- **Mutable structures wiring**: All 4 mutable structures integrated into the live pipeline
  - `GanaRegistry` → `DispatchPipeline` via `with_gana_registry()`, records usage + co-usage on every tool dispatch
  - `LearnedDreamCycle` → `DreamCycle` via `with_learned()`, reorders phases by effectiveness, records phase results
  - `LearnedCycleStrategy` → `AutonomousCycleRunner` via `with_learned()`, selects cycles adaptively, records cycle effectiveness
  - `GanaRegistry` + `DynamicGalaxyRegistry` → `McpServer` via `Arc<Mutex<>>`, shared instances initialized in `with_defaults()`
  - `LearnedCycleStrategy` + `LearnedDreamCycle` → Daemon main loop
- **4 E2E integration tests**: GanaRegistry recording, DynamicGalaxyRegistry access, LearnedDreamCycle attachment, full pipeline integration
- **All benchmarks passing**: dream, reflex, RSI, self-play, router, pipeline
- **0 clippy warnings**, fmt clean

## [5.1.0] — 2026-08-09

### v5 Strategy Implementation (Phase 4)

#### Phase 4: Imagination Engine ✅
- **`WorldModel`** (`wm-bicameral/src/world_model.rs`, 775 lines): bicameral LLM state prediction with `predict()`, `rollout()`, `generate_actions()`
- **`ScenarioEngine`** (`wm-bicameral/src/scenario.rs`, 602 lines): core imagine→simulate→evaluate loop with `imagine()`, `select_best()`, `reflect()`
- **`ScenarioEvaluator`** (`wm-bicameral/src/evaluator.rs`, 438 lines): multi-criteria scoring (goal progress, risk, novelty, confidence)
- **`SimulationBridge`** (`wm-bicameral/src/simulation_bridge.rs`): connects `wm-simulation` (Monte Carlo, forecasting, counterfactual) to imagination engine
- **`ImaginationConfigurator`** (`wm-bicameral/src/configurator.rs`, 440 lines): `DeliberationMode` (Direct, Shallow, Deep, Research) for depth selection
- **3 MCP tools**: `imagine.scenario`, `imagine.predict`, `imagine.reflect` (`wm-tools/src/expansion/imagination.rs`, 557 lines)
- **Dream cycle integration**: Oracle phase enhanced with `ScenarioEngine::reflect()` for counterfactual replay on hub memories
- **`CycleType::Research`**: 8th autonomous cycle — scans for open problems, generates hypotheses, stores as `MemoryType::Hypothesis`
- **Daemon `--research-interval`**: dedicated Research cycle on separate schedule (0 = run with regular cycle sweep)
- **`McpServer::init_imagination()`**: builds `ScenarioEngine` at startup, wired into dream + cycle contexts
- **2 new tests**: `dream_context_with_imagination`, `dream_cycle_oracle_with_imagination`

### Metrics (v5 Phases 1–4)
- **14 crates** (unchanged)
- **176 tools** (unchanged)
- **3,080 tests** (up from 3,078)
- **0 clippy warnings**, fmt clean

## [5.0.0] — 2026-08-08

### v5 Strategy Implementation (Phases 1–3)

#### Phase 1: Foundation (Async + Crate Merge) ✅
- **Crate merge**: 19 → 14 crates (wm-cognitive absorbs wm-consciousness, wm-reflex, wm-timescale, wm-drive, wm-resonance, wm-autonomic)
- **Async dispatch**: `async fn dispatch`, `#[async_trait]` Tool, `.await` at all call sites
- **Async MCP server**: `handle_request`, `handle`, `handle_tools_call` all async
- **Test conversion**: All tests converted to `#[tokio::test]` + `async fn`
- **3,009 tests pass**, 0 clippy warnings, fmt clean
- ~5,000 lines changed across 60+ files

#### Phase 2: Embedding NLU Router ✅ (shadow mode)
- **`EmbeddingRouter`** (`wm-tools/src/embedding_router.rs`, ~530 lines): cosine similarity against pre-computed tool embeddings
- **OATS** (Outcome-Aware Tool Selection): offline embedding refinement from success/failure centroids (α=0.15, min 10 observations)
- **Shadow mode**: embedding router primary, TF-IDF fallback runs alongside logging disagreements
- **Graceful fallback**: stub embedder detected at init → TF-IDF used directly
- **Integration**: `WmMetaTool::with_embedder()`, `register_meta_tools()` calls `create_embedder()`
- **31 new tests**: cosine sim, OATS refinement, A/B comparison with TF-IDF
- Step 2.8 (remove TF-IDF) deferred until production accuracy validation

#### Phase 3: Learned Inference Router ✅ (shadow mode)
- **`LearnedRouter`** (`wm-bicameral/src/learned_router.rs`, ~1,100 lines): embedding k-NN (k=5) + conformal calibration
- **`RoutingHistory`**: k-NN store with prompt frequency tracking and outcome-based weighting
- **`EdgeRuleGenerator`**: auto-promotes high-frequency simple responses to compiled edge rules (frequency ≥ 5, confidence > 0.9, response < 200 chars)
- **Shadow mode**: learned router primary, regex classifier runs alongside logging disagreements
- **Cold-start fallback**: `ComplexityClassifier` (regex) when history < 10 records
- **Integration**: `InferenceRouter::with_embedder()`, `with_learned_router()`, `record_learned_outcome()`, `observe_for_edge_rules()`, `promote_edge_rules()`
- **29 new tests**: cosine sim, k-NN routing, A/B comparison with regex, edge rule promotion
- Step 3.5 (remove regex) deferred until production accuracy validation

### Metrics (v5 Phases 1–3)
- **14 crates** (down from 19)
- **176 tools** (unchanged)
- **~115,000 LOC** (up from ~112,300)
- **3,078 tests** (up from 2,818: +152 crate merge, +31 embedding router, +29 learned router, +48 other)
- **0 clippy warnings**, fmt clean

## [4.0.0] — 2026-08-07

### Summary

Complete rewrite of WhiteMagic from Python to Rust. A cognitive operating system for agentic AI with 176 tools, 19 crates, ~112,300 lines of Rust, 2,818 tests, and zero clippy warnings. Exposed as an MCP server with a single `wm` meta-tool — all tools accessible via NLU routing or explicit dispatch.

### Architecture

- **19 crates**: wm-core, wm-memory, wm-dispatch, wm-consciousness, wm-governance, wm-polyglot, wm-tools, wm-mcp, wm-substrate, wm-bicameral, wm-drive, wm-autonomic, wm-reflex, wm-timescale, wm-workspace, wm-selfmodel, wm-resonance, wm-sangha, wm-simulation
- **176 tools** organized across 28 Gana (cognitive function categories)
- **14-galaxy memory** architecture backed by LMDB (zero-copy, memory-mapped)
- **Tantivy** full-text search with BM25 scoring and query sanitization
- **LanceDB** optional vector indexing (SIMD-accelerated ANN)
- **Local embedder** via HTTP (llama-server) with stub fallback
- **Shared IndexWriter** — single Tantivy writer behind Mutex, eliminating lock contention

### Cognitive Architecture

- **Citta consciousness**: 16D consciousness vector with coherence measurement
- **Dream cycle**: 12-phase memory consolidation
- **Brain-wave eco mode**: 5 states (Gamma, Beta, Alpha, Theta, Delta) with zero idle CPU
- **7 autonomous cycle types**: Connect, Compress, Emergence, Prune, Improve, Redteam, Sensorimotor
- **Bicameral reasoning**: Dual-hemisphere (left: heuristic, right: LLM/BitNet/stub) with inference router
- **Self-model**: Predictive introspection with forecasting and alerts
- **Global workspace**: Spotlight arbitration, salience scoring, event bus
- **Drive core**: 5 intrinsic motivation drives with decay toward baseline
- **Reflex dispatch**: Safety bitmask, 8 builtin handlers, permissive/strict modes
- **Timescale bus**: 3-tier event bus (Reactive/Planning/Strategic) with brain-wave gating

### Safety Features

- **Destructive tool confirmation**: 8 tools require `"confirm": true` in args
- **Transaction snapshot/rollback**: 3 tools (begin/commit/rollback) with batch restore (>99% performance improvement)
- **Compartment-based access control**: sandbox/production/secure levels with runtime galaxy arg enforcement
- **Karma ledger**: SHA-256 hash chain for all tool actions
- **Dharma governance**: Ethical rules and resource management

### RSI Pipeline (Phases 1–3)

- **Phase 1**: Friction logging (friction.log, friction.review, friction.auto_log)
- **Phase 2**: Outward spiral (WS-1–WS-5) with telemetry, deduplication, karma bridge, resolution verification
- **Phase 3**: Adversarial (redteam.from_friction, redteam.coverage_report, E2E tests, criterion benchmarks)
- **12 RSI tools** total

### NLU Router

- 166 TF-IDF profiles with cosine similarity
- 12 prefix routes for common patterns
- Stopword filtering, English stemmer
- Payload extraction (e.g., "remember that X" → memory.create with content=X)

### Polyglot Integration

- **Julia** (jlrs), **Haskell** (FFI), **Zig** (C ABI), **Koka** (C ABI)
- All in-process via FFI — no subprocess overhead

### MCP Server

- Single `wm` meta-tool exposed via `tools/list`
- JSON-RPC over stdio
- CLI: `wm serve`, `wm quickstart`, `wm doctor`, `wm stats`, `wm brain-wave`, `wm polyglot`
- Optional PyO3 bridge for Python MCP shell

### Embodiment I/O

- Linux /proc + /sys sensor reading
- Sensorimotor bus with hardware abstraction
- Homeostatic loop and anomaly detection
- Harmony Vector (Lakshmi) for hardware-aware governance

### Security Hardening

- 20 catalog attack vectors covered
- 33 manifest attack surfaces tested
- Query sanitization (Tantivy injection prevention)
- Input validation on all MCP endpoints
- `#![forbid(unsafe_code)]` in all crates except FFI boundaries

### Performance

- Sub-6ms dispatch latency
- 14 MB release binary
- Zero-copy LMDB reads
- Atomic stats (no locks in hot path)
- Transaction rollback: ~4.5ms for 100 memories (was ~1.8-2.6s)

### Development Phases (All Complete)

- Phases 0–8: Core runtime, memory, dispatch, consciousness, governance, polyglot, MCP, fuzz, CI
- Phases A–F: Governed autonomy roadmap
- Phases R1–R7: CyberBrain architecture (reflex, timescale, workspace, self-model, bicameral, drive)
- Phases L1–L5: Local AI integration (BitMamba, LlamaLeftHemisphere, BitNet, inference router, OrtEmbedder)
- Phases N1–N21: Neural integration (Gan Ying Bus, Sangha mesh, simulation, resonance, sensorimotor)
- RSI Phases 1–3: Friction logging, outward spiral, adversarial testing

### Bug Fixes (Post-Initial Development)

- **Tantivy writer lock contention**: Moved IndexWriter into SearchEngine behind Mutex, eliminating lock errors when multiple tools try to index simultaneously
- **Dynamic galaxy compartment bypass**: Pipeline now checks runtime galaxy argument in addition to static EffectRow declarations
- **Silent Codex fallback**: BM25 results with unknown galaxies are skipped instead of misattributed
- **Orphaned embeddings**: Vector search skips embeddings whose memory was deleted
- **LMDB nested transaction bug**: Fixed silent failures in vector search caused by opening read txns during cursor txns
- **Transaction rollback performance**: Batch operations reduce 100-memory rollback from ~2s to ~4.5ms

### Removed (vs v2)

- Python runtime (replaced by Rust)
- Subprocess-based polyglot (replaced by FFI)
- ~10,000 tests (replaced by 2,818 focused tests: property, fuzz, E2E, criterion, security, red-team)
- 877-tool catalog (distilled to 176 runtime-authoritative tools)
