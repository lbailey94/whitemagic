# WhiteMagic v9 — threat model and read/egress limits

**Baseline:** 9.2.0 (`aa3c266` + Q08, 2026-09-19) · **Status:** living
artifact; A-prefixed adversary IDs and L-S7 surface rows are stable names.
**Scope:** Q09 (M2) + ledger S7 ("confinement truth: publish read/egress
limitations; loopback bind + token/PSK before off-host exposure").
**Related:** `docs/S9_SECURITY_BRIEF_2026-09-10.md`,
`docs/HONEST_GAPS_2026-09-14.md`, `docs/MESH_JOIN_PROTOCOL.md` §11,
`docs/MESH_TLS_REVOCATION_DESIGN.md`, `docs/Q39_CRYPTO_ERASURE_DESIGN.md`,
`docs/contract/boundary-matrix.md` (Q08),
`docs/SANGHA_SECURITY.md`, `SECURITY.md`.

Method: controls are cited to code/tests, not aspirations. Anything not
enforced today is listed in §6 with its accepted-residual status and target
wave. "Enforced" means a test pins it; "declared" means the type system
records it but no runtime path consumes it.

## 1. Assets

| Asset | Where | Why it matters |
|---|---|---|
| Memory records (all galaxies) | `<store>/lmdb`, Tantivy index, vector store | Contains prompts, decisions, client data; may contain secrets the operator pasted |
| Store keys | `.seal_key`, `.at_rest_key` / `WM_AT_REST_*` RK, galaxy DEKs in the `keyring` DBI | Compromise = at-rest confidentiality loss; loss = unreadable store |
| Node identity keys | HKDF-from-`WM_MESH_KEY` (`wm/mesh-identity/v1`) | Mesh impersonation, chat/lock/authority abuse |
| Attestation signer | `wm/record-attestation/v1` | Record provenance / Q36 receipts |
| Backups | backup archives + `SHA256SUMS` (+`envelope.json`, Q07-F1) | Plaintext copies with the same content |
| Governance ledgers | karma chain, write-audit journal, attestations DBI, claims ledger | Integrity of governance evidence; audit trail |
| Coordination leases | `$(git-common-dir)/wm-leases.json` | One-writer discipline across worktrees |
| Tool surface + pipeline | `wm-tools` registry, `wm-dispatch` gates, firebreak | The only thing between a client and the store |
| Host | store-root writes under Landlock; git-dir grant | Containment boundary (writes only; reads free) |

## 2. Adversaries

| ID | Adversary | Capability assumed |
|---|---|---|
| A1 | Passive local observer | Can sniff the local link (mesh v0 is plaintext TCP/UDP) |
| A2 | Local unprivileged process | Can read world-readable files, probe ports, race locks |
| A3 | Malicious/compromised mesh peer | Valid keypair, can send frames, claim any `peer_id`, replay captured traffic |
| A4 | Untrusted MCP client / injected content | Can call tools, embed instructions in memory content or tool results; prompt-injection class |
| A5 | Malicious tool args | Can attempt command injection, path escape, protected-file access through legit tools |
| A6 | Supply chain | Malicious dependency, build-time artifact, optional FFI surface |
| A7 | Offline thief | Steals the disk or a backup archive; no live process |
| A8 | Operator error | Wrong scope, disarmed guardrails, exposed SSE port, missed retention |

Out of scope for v9: a root/administrator attacker on the host (can read
process memory and keys), kernel exploits, physical coercion, and remote
attackers with no foothold (no listener is internet-exposed by default).

## 3. Trust boundaries and controls

| # | Boundary | Primary controls (evidence) |
|---|---|---|
| B1 | MCP client → server | JSON-RPC input validation + param-injection tests (`crates/wm-mcp/src/input_validation.rs`, `injection_in_params`); profile filtering before meta-tools (`wm-tools/src/profiles.rs`); `--readonly` refuses everything with declared writes; compartments fail closed on unknown values; NLU structural gate keeps `thought=` away from destructive routes (`wm-tools/src/lib.rs` `nlu_cannot_reach_any_destructive_tool`); destructive confirm + scope law at the pipeline (`wm-governance/src/firebreak.rs`, Q08 artifact) |
| B2 | Untrusted content | Content admission gate + injection-pattern rejection at write time (`wm-memory/src/validator.rs` `detect_injection`, `reject_injection_pattern`); recall results are labeled data (`recall_mode`, `source`, `trust_factor` disclosed), never executed; write-audit journal excludes prose (firebreak scans the irreversible seam only) |
| B3 | Pipeline governance | Effect rows per tool; queue → brain-wave/effect gate → confirm → dharma → resource rules → write gate → rate limit → circuit breaker → firebreak → sandbox routing → audit/karma (`crates/wm-dispatch/src/pipeline.rs`; Q08 matrix maps every registered route) |
| B4 | Filesystem confinement | Landlock v0 whole-process write-class confinement (reads free), v1 per-tool `StoreScoped` threads; every degrade is loud and graded by `wm doctor` 11d (`AGENTS.md` Landlock sections) |
| B5 | Subprocess / spawn | Spawn declarations in `EffectRow`; `Sandbox::Subprocess` contract; firebreak forbidden-command veto (31 patterns) blocks `rm -rf /`-class, device writes, pipe-to-shell even with `confirm: true`; `WM_FIREBREAK=0` is loud + doctor-flagged |
| B6 | Mesh peer | Ed25519 signed heartbeats + chat + beacons (beacon signatures verified at ingest under the announced key), freshness windows, replay caches, TOFU-then-pin binding, bind-seam reservation for pinned grants (E10 `1cc4cc9`), local default-deny grant table, quarantine enforced at ingest; unknown-peer address hints expire and are never auto-dialed (HG-S1-7). Wire is **plaintext until Q26** (§6) |
| B7 | At rest / offline | `keyring` DBI with wrapped galaxy DEKs + wrong-key discriminator (slice A, `crates/wm-memory/src/at_rest.rs`); RK precedence env → key file → generated 0600 `.at_rest_key`; mode B never advertises crypto-erasure; seal (HMAC) disclosed by `wm doctor` 11b as corruption/casual-tamper detection only. **Records and backups are plaintext until Q39 B/E** (§6) |
| B8 | Federated gateway | Explicit scope on writes (no scope → `no_scope` refusal), unknown scope fails closed naming reachable scopes, inner `args.scope` is payload not routing, 5 federated read routes only (`crates/wm-mcp/src/gateway.rs`); spawned end-to-end gateway coverage is gap Q08-G2 |
| B9 | Update path | Signed release manifest + signed git tags verified on `wm update`; Ed25519 + sha256 checks before install; rollback kept at `.previous`; TUF-style rotation/freeze protection is the acknowledged next step |
| B10 | Supply chain / FFI | `cargo deny check` CI job (advisories, licenses); `#![forbid(unsafe_code)]` in all crates except `wm-polyglot` and `wm-mcp/pyo3_bridge`; Python bridge and polyglot are feature-gated and excluded from the release binary |

## 4. L-S7 — read and egress limits per surface

What each surface can **read** and where it can **send** data. "Egress"
means data leaving the process boundary the operator thinks it is using.

| Surface | Read scope | Egress | Default |
|---|---|---|---|
| stdio MCP (`wm serve`) | Whatever the profile exposes; recall spans galaxies unless filtered; compartments constrain at the store API | None (no network in the request path) | Default transport; local only |
| SSE transport (`--transport sse`) | Same as stdio | Listener on the operator-supplied `--bind` | **No auth token/PSK**; must stay loopback-only until S7 lands (§6); `--bind` is mandatory (no silent default) |
| Federated gateway | The 5 federated read routes fan out to configured scopes; everything else pinned to one scope | Only to configured backing endpoints | Listener on the operator-supplied bind; no gateway-specific auth — S7 applies to every SSE surface |
| Mesh node | Local stores; peer frames are action-class only (chat/signals/locks) | Plaintext TCP/UDP on the local link | Off unless `--mesh`/`WM_MESH=1`; a local passive observer can read the wire (A1) |
| Daemon | Store APIs for cycles and consolidation | None by default | Autonomous work off the request path |
| `wm update` / grimoire manifest check | Release metadata | HTTPS to the release host, checksum-verified | Operator-invoked; offline degrades visibly |
| Activation funnel | Local counters only | **Opt-in only** (`--share`): the exact payload is printed at enable time; per-install id, no content | Off; `wm doctor`/privacy copy discloses |
| Embedder (`WM_EMBEDDER_ENDPOINT`) | Text to embed (memory content, queries) | HTTP POST to the operator-configured endpoint | Unset → stub/TF-IDF, no egress; a configured non-local endpoint is an operator decision and should be disclosed |
| `web.*` tools | Arbitrary URLs | Arbitrary outbound HTTP by design | Full profile only; treat fetched content as untrusted input (A4) |
| Filesystem (general) | Reads are free under Landlock; store-root writes confined; `WM_PROJECT_ROOT/.git` granted for the lease ledger | n/a | v1 `StoreScoped` narrows writes per tool |

**Zero-egress evidence (Q37, network leg):** CI job "Zero-Egress Proof
(Q37)" runs `scripts/zero_egress_test.sh` in a network namespace with `lo`
DOWN, executes create + recall with the release binary, and runs a negative
control that must fail. Scope honesty (from Q37 itself): this demonstrates
operation with networking disabled — not the absence of attempted egress in
every configuration.

## 5. Prompt injection and untrusted content (A4)

- Memory writes reject known injection patterns (`validator.rs`), and the
  write-audit journal deliberately excludes prose so an incident note quoting
  dangerous strings cannot become an execution path.
- Destructive routes are structurally unreachable through NLU regardless of
  what content says; the confirm + scope gates see only explicit `route=`
  dispatches.
- The server does not run an LLM in the default request path, so recall
  content is never interpreted as instructions *inside the server*. Clients
  that paste recall output into a model inherit model-level injection risk —
  a client-side property, disclosed here rather than defended.
- `web.*` and `wm ingest` bring third-party text into the store; the same
  write path validator applies.

## 6. Honest gaps and accepted residuals

| Gap | State | Owner / wave |
|---|---|---|
| Mesh wire is plaintext; no in-transit encryption | Accepted residual; TLS 1.3 + pinned certs + rotation designed, not implemented | Q26 (`MESH_TLS_REVOCATION_DESIGN.md`); Gate 2 cohort use blocked on it |
| Signals unsigned (`source` is a claim) | Accepted residual; first production emitter must land signing with its consumer | Q26 |
| Locks/signals are claimed-identity checks in permissive mode | Documented residual (chat is bound-key verified) | Q26 / E10 §11 |
| Records plaintext at rest; backups plaintext; backup erasure latency is the disclosed D1 design limit ("content leaves all rotating backups within ≤7 days", Q39 §5) | Slice A keyring landed; no crypto-erasure claim permitted before B+C+D+E | Q10 (B–E) |
| SSE has no token/PSK; must not be exposed off-host | **Open — S7 gate** | This artifact; enforce before any off-host deployment |
| Landlock confines writes only; reads are free; no egress policy; v1 skips dispatch timeout and excludes subprocess tools | Documented limitation | `L-S5`/`L-S6`, C66-40 |
| Effect-based B4 sandbox block (Process/Network/FS/Execute) not implemented | Open | `L-S5` / C66-40 |
| Requested-containment failure is loud-degrade, not refuse-to-start | **Design decision** (availability bias): unsupported kernel/ABI logs WARN + doctor issue and runs unconfined | Revisit if strict mode is requested for fleet deployments |
| Beacons are discovery hints, not identity (signed, verified, but hints) | Accepted by design; hints expire, capped, never auto-dialed | HG-S1-7 closed |
| Trust-weighted retrieval ships disabled (`WM_TRUST_WEIGHT=0`) | Declared, not scored; disclosure stays | After benchmark re-run |
| Gateway has no spawned multi-process E2E in CI | Open | Q08-G2 |
| TUF-style rotation / rollback+freeze protection on updates | Acknowledged next step | Post-9.2 |
| `pyo3`/polyglot FFI outside `forbid(unsafe_code)` | Feature-gated, not in release binary; reviewed at crate level | Standing |

## 7. Q09 queue-scope reconciliation

| Q09 item (`V9_2_WORK_QUEUE.md`) | Where satisfied |
|---|---|
| Explicit attacker model | §2 (A1–A8), out-of-scope statement |
| Read/write/egress limits | §4 (L-S7 table), §3 B4/B6/B7 |
| Prompt-injection fixtures | Existing: `wm-memory/src/validator.rs` injection tests, `input_validation.rs::injection_in_params`, `nlu_cannot_reach_any_destructive_tool`; §5 states the client-side limit |
| Strict requested-containment failure behavior | §6 row (loud-degrade decision); Landlock doctor grading 11d; firebreak disarm 11h |
| Dependency/FFI review | §3 B10 (`cargo deny` job, unsafe-code policy, feature-gated FFI) |

## 8. E10 review record

Independent verification pass over every "enforced" claim above against code
and tests at `f2a55c7`; receipt:
`planning/private/E10_Q09_THREAT_MODEL_REVIEW_2026-09-19.md` (findings,
corrections, and the claims re-verified with the exact commands).
