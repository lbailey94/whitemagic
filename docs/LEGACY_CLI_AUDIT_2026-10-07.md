# Legacy CLI Audit — v9-only commands (Preserve / Translate / Deprecate / Remove)

- **Date:** 2026-10-07
- **Lane:** `docs/gate9b-evidence` (worktree `wt-gate9b`), base `ef623fbd5e80d64a47c3335e99a34ea3b9bf7511`
- **Owner:** opencode (release-evidence engineering lane)
- **Closes:** Gate 9B open item 3 (`receipts/GATE_9B_CLOSURE_VERDICT_2026-10-07.md` §4.3);
  PEB-15 §9.3 carried item 5
- **Subject binaries:** legacy `wm9` 9.3.4 (installed) vs Gen3 `wm10` 10.2.0-alpha.6 (installed;
  sha256 `fcd7f5a0f0353a482c85ba04b0fe7cd0d7e3db599947f9182ccdce58575819aa`)
- **Method:** command inventory from `wm9 --help` + `wm9 help --all`; Gen3 presence determined by
  `wm10 <cmd> --help` exit status and help text. Raw inventory (63 names):
  `receipts/gate9b_artifact_evidence_20261007/logs/10-command-presence.txt`.
  This audits the **CLI** surface; the Gen3 MCP route surface is separately machine-checked by
  `wm10 contract --json` (44 routes / 40 declared / 4 undeclared).
- **Rev 2 (2026-10-07, post-merge `80b34c2`):** wave-3 commit `88ac66a` wired `wm at-rest`
  (`status|migrate`) and added the Gen3-only `wm host-guard` (`status|run|arm|disarm`) and
  `wm compact` commands; row #29 and §4.2 updated. All other dispositions stand.

## 1. Disposition vocabulary

| Disposition | Meaning |
|---|---|
| **Preserve** | Capability continues on the v9 line (`wm9`) for v9 stores; no Gen3 port claimed in this audit. |
| **Translate** | A Gen3 command covers the capability, possibly with changed semantics; replacement named. |
| **Deprecate** | No Gen3 successor; the v9 command remains only in `wm9` and should be announced end-of-line for new work. |
| **Remove** | The capability's premise does not exist in Gen3; no successor and no migration needed. |

## 2. v9-only commands (present in `wm9` 9.3.4, absent from `wm10` 10.2.0-alpha.6)

| # | v9 command | v9 purpose | Disposition | Gen3 replacement / route | Rationale |
|---|---|---|---|---|---|
| 1 | `build-info` | Executable build provenance without opening a store | **Deprecate** | `wm --version` + signed `release-manifest.json` / SBOM | Release provenance is carried by the signed release manifest and SBOM; an in-binary provenance command was not re-derived. |
| 2 | `manifest` | Read a running HTTP server's capability manifest | **Translate** | `wm contract --json` | Gen3 emits the machine-checked route/schema manifest locally (44/40/4); remote HTTP manifest fetch is not re-derived. |
| 3 | `config` | Generate/show TOML configuration | **Deprecate** | `--store` flag + environment variables | Gen3 is deliberately config-light (no TOML generation); v9 config management stays on `wm9`. |
| 4 | `quickstart` | Built-in quickstart demo | **Translate** | `wm grimoire` (and `wm init`) | Guided first-run onboarding replaces the demo walkthrough. |
| 5 | `docs` | Print bundled documentation offline | **Deprecate** | repo `docs/`, `llms.txt`, published site | Offline doc printing was not re-derived; the canonical Gen3 guide ships in-tree and via `llms.txt`. |
| 6 | `setup` | Configure an MCP client (JSON/JSONC/TOML patching) | **Translate** | `wm grimoire --plan` | Grimoire detects clients and plans config changes without writing; auto-patching is intentionally not re-derived. |
| 7 | `connect` | Detect and wire all MCP clients in one command | **Translate** | `wm grimoire` (client detection step) | Gen3 detects Claude Code/OpenCode/Antigravity and emits a plan; wiring is agent/manual per MCP config policy. |
| 8 | `update` | Self-update from GitHub Releases | **Deprecate** | `scripts/install.sh` / package channel; `wm9 update` | In-binary self-update was not re-derived for Gen3; the signed install path is canonical. |
| 9 | `doctor` | Diagnose system issues (optionally write a support bundle) | **Translate** | `wm selftest` (`--strict`, `host_health`) + `wm inspect` | Host diagnostics (disk/mem/PSI/swap/crash-loops) replaced the v9 doctor; support-bundle writing is not ported. |
| 10 | `ledger` | Local token/savings ledger | **Deprecate** | — | v9 MCP accounting (stored vs injected state) has no Gen3 successor; sessions/receipts cover evidence, not savings. |
| 11 | `receipt` | Emit/verify/list/show continuity receipts | **Translate** | `wm verify-receipt`, `wm outcome`, `wm mandala record-receipt` | Gen3 signs and verifies CR 0.5 receipts against the store gate key; the v9 bundle CLI is not carried over. |
| 12 | `stats` | Resource usage and brain-wave state | **Translate** | `wm inspect` + `wm status` | Substrate/epoch/journal views replace the v9 stats readout; no brain-wave state exists in Gen3. |
| 13 | `telemetry` | Telemetry schema, funnel status, display preview | **Remove** | — | Gen3 is local-first/zero-egress by construction; there is no telemetry surface to expose. |
| 14 | `report` | Sanitized local support bundle (`report.json`) | **Deprecate** | `wm selftest --json` + logs | Support-bundle generation was not re-derived; structured selftest output covers first-line triage. |
| 15 | `backup` | Full-store disaster-recovery backup (LMDB + indexes + JSON) | **Preserve** | `wm9 backup` (v9 stores) | **Gen3 whole-store backup is not yet implemented — an open gap**, not a 9B blocker; see §4. |
| 16 | `restore` | Restore a `wm backup` archive | **Preserve** | `wm9 restore` (v9 stores) | Same open gap as `backup`; Gen3 restore is not yet re-derived. |
| 17 | `reindex` | Rebuild the Tantivy full-text index from LMDB | **Remove** | — | Gen3 has no separate Tantivy index (retrieval runs on the in-substrate index), so there is nothing to rebuild. |
| 18 | `geneseed` | Mine git history patterns with longevity scores | **Translate** | `wm vault` (Geneseed Action Vault) + `wm apotheosis` cladistics | Gen3 re-derived action skeletons and cladistic lineage under the vault/apotheosis surfaces. |
| 19 | `polyglot` | Polyglot acceleration status | **Deprecate** | `wm organ status` (backend reporting) | v9 polyglot status was not re-derived; Gen3 acceleration is internal (ONNX/fastembed) and reported by organ/selftest. |
| 20 | `export-training-data` | Export collected data for LoRA fine-tuning | **Deprecate** | — | No Gen3 training-data collector; the v9 pipeline is not re-derived. |
| 21 | `daemon` | Persistent daemon with autonomous cycles | **Remove** | `wm serve` (transport only, under systemd) | Kernel Article 4 forbids autonomous cognitive background loops; Gen3 keeps only physical I/O/transport. |
| 22 | `brain-wave` | Show brain-wave state (alias for stats) | **Deprecate** | `wm inspect` / `wm status` | Brain-wave state was a v9 runtime concept not present in Gen3; substrate health is exposed instead. |
| 23 | `opencode` | Bridge opencode session data (digest/export) | **Translate** | `wm ingest` + `wm session` | Gen3 ingests transcripts/JSONL and maintains session lanes directly; client detection is in grimoire. |
| 24 | `seal` | HMAC-SHA256 seal of the LMDB store core | **Preserve** | `wm9 seal` (v9 stores) | Store-format-specific sealing was not re-derived; Gen3 integrity uses signed receipts (`wm verify-receipt`, `mandala record-receipt`). |
| 25 | `verify` | Verify the LMDB store core against a seal manifest | **Preserve** | `wm9 verify` (v9 stores) | Same as `seal`: Gen3 verifies receipts and Merkle state commitments, not a whole-store HMAC seal. |
| 26 | `anchor` | Merkle-anchor store attestations, optional publish | **Translate** | `wm mandala record-receipt` + `wm mesh export` | Gen3 anchors Merkle state commitments in signed receipts and signed sync bundles. |
| 27 | `repair-content` | Repair gate-failing V8-drift memory content | **Remove** | `memory.update` (if supersession is needed) | The V8 drift corpus never existed in Gen3 stores, so in-place repair is not applicable. |
| 28 | `redact-content` | Retro-redact credential-shaped stored content | **Translate** | `memory.ingest` (`redact: true`, default) / MCP ingest | Redaction moved to the ingest boundary; there is no retro-scan CLI in Gen3. |
| 29 | `at-rest` | At-rest keyring operations (Q39 slice B) | **Translate** (rev.2) | `wm at-rest status` / `wm at-rest migrate` (merged main `88ac66a`) | CLI now wired: `status` reports mode/keyring/wrapped DEKs/migration ledger; `migrate` is bounded-batch seal-on-rewrite (`--dry-run` available, `--yes` required for writes). |
| 30 | `trust` | Survey/correct memory source-trust provenance | **Translate (partial)** | `wm peer` (peer trust tiers); `min_trust` read-side filter | Peer trust is re-derived; the memory source-trust survey/correction workflow is not — v9 memory curation stays on `wm9 trust`. |

Not a command: **`federate`** does not exist in `wm9` 9.3.4
(`error: unrecognized subcommand 'federate'`). The federated concept maps to `wm mesh`
(sovereign sync) and `wm serve --transport http|sse` (loopback-gated) in Gen3; nothing to
disposition.

Wave-3 Gen3-only additions (not v9-derived, so not dispositioned above): `wm host-guard
status|run|arm|disarm` (wave-3 `88ac66a`; `run` is report-only unless `--act`, single-lease
locked, durable armed flag), `wm compact` (LMDB compaction; e2e gated on `lmdb-utils`/`mdb_copy`,
report math unit-tested), and `wm at-rest status|migrate` (#29 above).

## 3. Shared names with changed semantics (present in both, not v9-only)

| Name | v9 9.3.4 | wm10 10.2.0-alpha.6 | Note |
|---|---|---|---|
| `serve` | MCP server; `--profile` curated/default, `--max-requests`, `--rate-limit` | MCP server; `--profile cyberbrain` (default) / `full` (`curated` accepted alias), no `--max-requests`/`--rate-limit`, new `--legacy-store` read-only Gen2 mount and loopback-gated `--transport http\|sse` | **Flag drift breaks v9-era scripts** (`curated_smoke_test.py`, `longmemeval_bench.py`, `memorastrict_bench.py`) — see `GATE_9B_ARTIFACT_EVIDENCE_2026-10-07.md` §4. |
| `migrate` | SQLite v26 → v5 LMDB | Gen2 LMDB → Gen3 (plus `census`, `migrate-all`, `quarantine`, `backfill-session-evidence`) | Same name, different source/target; not interchangeable. |
| `session` | Session continuity over LMDB (CLI parity for MCP routes) | Session lanes: `checkpoint`, `record`, `continuity`, `list`, `digest` | Capability preserved; surface expanded. |
| `ingest` | Documents/transcripts into a knowledge store | JSONL/transcript/event ingest with default credential redaction | Capability preserved; redaction added at ingest. |
| `contract` | Route/schema contract catalog | Route/schema manifest (44 routes / 40 declared / 4 undeclared) | Preserved; counts are machine-checked. |
| `selftest` | Five-second end-to-end invariant check | Invariant self-test + host diagnostic (`--json` install contract stable; `host_status` added) | Rewritten 10.2.0-alpha.4; JSON contract kept. |
| `status` | Human-facing health summary | Gen3 kernel status (epoch/records/journal) | Preserved. |
| `grimoire` | Guided first-run (7 steps incl. release check) | Guided first-run (host/substrate/galaxy/clients/verification), `--plan` | Preserved. |

## 4. Open gaps this audit surfaces (not 9B blockers)

1. **No Gen3 whole-store `backup`/`restore`** (#15/#16) — Gen3 disaster recovery is an
   unimplemented capability; production graduation should schedule it or record an explicit
   acceptance of the risk.
2. **`wm at-rest` CLI: CLOSED (rev.2)** — `wm at-rest status|migrate` wired in wave-3
   `88ac66a` (see #29); `migrate` is bounded-batch seal-on-rewrite and requires `--yes`.
3. **Memory source-trust curation** (#30) — peer trust re-derived, memory-side survey/correction
   not yet.
4. **v9-era bench scripts** depend on the removed `serve --max-requests/--rate-limit` flags and
   the v9 MCP contract; they need a Gen3 port (evidence receipt §4).
