# RECEIPT — W1_B2 sessions & continuity acceptance demonstrated (2026-09-18)

**Status: evidence — acceptance demonstrated; row exit criteria met.** AI session
`221fbb57-905f-4e7d-a4d3-3c11810ea0b7` (Antigravity) executed and attests. Spec
`docs/specs/W1_B2_sessions_continuity.md`. Append-only; corrections create a new receipt referencing this one.

---

## 1. Artifacts

| Field | Value |
|---|---|
| Bundle | `receipts/impl_w1_b2_2026-09-18/` (3 files) |
| **SHA256SUMS** | `f43e403d488ae9ffd4c9b8cb4248bf76c715f1ab0fb0c78d8eced16b02deb255` |
| Gen3 Binary | `target/release/wm-gen3` (sha256 `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`) |
| Link Test Suite | `WHITEMAGIC/WMv9/target/debug/deps/wm_tools-8ba6399ac8e6dfca` |
| Driver | `driver_w1_b2_sessions.py` (`d357aa71ae9cb0ba5c258e40c0124d7c33bf49fe8fc790b96c9b59c8e8e5f663`) |
| Results Log | `sessions.results.txt` (`f3b21518d345e9f9d73a81ea760f4f622835cc176e9b00507c286c9d4b1310bd`) |
| Tip at run | `500a7ff` |

---

## 2. Acceptance Criteria Demonstrated (Spec §5)

| # | Item | Result |
|---|---|---|
| 1 | **Lossless replay shape (§5.1)** | **PASS**: `session.export` $\rightarrow$ `session.import` round-trip preserves ids, timestamps, and tags. Superseded turns are hidden by default on replay and restored when requested with `include_superseded: true`. Hand-written summaries that duplicate records are excluded. (`export_import_roundtrip_preserves_history`) |
| 2 | **No payload-less shells (§5.2)** | **PASS**: Empty handoffs and missing payloads are refused with typed errors (`import_rejects_missing_payload`). Stored checkpoints carry concrete handoff payloads (`commit`, `branch`, `tests_green`, `next_queue`, `open_flags`, `lease_id`). The Gen1 24-empty-shell defect class (W0 errata #30) is systematically excluded. |
| 3 | **Resolution semantics (§5.3)** | **PASS**: Session resolution is time-based by `created_at` ordering, never LMDB UUID key scan order (`continuity_picks_newest_prior_by_time_not_key_order`). Empty newest candidate sessions are bypassed in favor of the newest prior session with turns (`continuity_skips_empty_newest_session`). When zero sessions exist, the empty store discloses truthful project scoping (`continuity_empty_store_discloses_project_scoping`), never hallucinating facts or panicking under starvation. |
| 4 | **Nodiscovery proof (§5.4)** | **PASS**: `session.checkpoint_nodiscovery` stores exactly the caller-supplied fields with 0 filesystem reads, 0 subprocess spawns, and 0 repository discovery (`nodiscovery_checkpoint_stores_exactly_the_supplied_fields`). Strict mode admits it (`is_no_discovery_checkpoint() == true`). Conversely, `session.checkpoint` truthfully declares `Resource::Filesystem`, `Resource::Process`, and `spawns: true`, and is refused under strict mode. |
| 5 | **Phrase table test (#2) (§5.5)** | **PASS**: All continuity phrases in `PHRASE_ROUTES` (`"where were we"`, `"where did we leave off"`, `"what did we decide last"`, `"continue from"`, `"pick up where"`) route to `session.continuity` with confidence 1.0 bare and with trailing content before tokenization. The stopword-only early return is prevented from pre-empting the phrase table. Live MCP verification confirmed. |
| 6 | **Write-time indexing (§5.6)** | **PASS**: Session writes index immediately at write time into Tantivy (`session_record_indexes_at_write_time`, `import_indexes_tantivy_no_drift_even_on_reimport`). Fulltext search retrieves turns with 0 drift while serving and unchanged after shutdown. |
| 7 | **Superseded visibility (§5.7)** | **PASS**: Turns tagged `superseded-by:<id>` are excluded from default replay views (`load_turns`), presenting the current story. Setting `include_superseded: true` restores full historical visibility (`supersedes_hides_old_turn_until_requested`). |
| + | **Gen3 Anti-Bloat Canon (§1.1, §1.7)** | **PASS**: Proof that Gen3 core (`crates/wm-gen3-core`) contains ZERO session modules or standalone session files. Storage/lifecycle = link (`session.*`); continuity/digest = compile (`recall` + `think` over session-tagged records). All Gen3 closure static scans PASS. |

---

## 3. Adversarial Cases Demonstrated (Spec §3)

1. **Two-writer sequence race (§3.1)** — PASS: sequence is canonical; single-writer per session invariant maintained.
2. **Ambient valence leak (§3.2)** — PASS: no global affective tone stamping across sessions; turns record explicit semantic content only.
3. **Previous-session selection (§3.3)** — PASS: time-based newest-with-turns resolution; empty sessions bypassed; bounded query.
4. **Cap bypass (§3.4)** — PASS: generic update path enforces statutory caps.
5. **Capture hygiene (§3.5)** — PASS: one declared default; secrets excluded fail-closed.
6. **Phrase routing (#2, 9.1.7) (§3.6)** — PASS: pre-tokenization check routes bare and trailing phrases decisively to `session.continuity`.
7. **Write-time indexing (9.1.7) (§3.7)** — PASS: index writes at write time; drift probe 0.
8. **`checkpoint_nodiscovery` semantics (9.1.8) (§3.8)** — PASS: exact caller-supplied fields, no auto-capture git leakage, strict-mode admitted.
9. **Payload-less shells (§3.9)** — PASS: empty handoff refused, never stored as an empty shell.
10. **Starvation (9.1.8) (§3.10)** — PASS: continuity reads stay open under starvation; empty continuity discloses project-scoping hint.

---

## 4. Disclosures

- **Boundary Characterization (Temporal Identity)**: B2 establishes temporal identity—the ability of an agent to wake up and recover an exact operational handoff without inventing missing context or hallucinating summaries.
- **Replay Shape Precision**: `session.export` $\rightarrow$ `session.import` round-trip preserves IDs, timestamps, and tags. Superseded turns are hidden by default and restored on request. Hand-written duplicate summaries are excluded.
- **The Split ratified in action**: Gen2 `session.*` (`wm-tools`) remains the live storage surface (link). Gen3 expresses continuity as `recall` over session-tagged records and digest as `think` synthesis (compile). No unearned session primitive was added to Gen3 core.
- **Strict-mode rhythm adopted**: `session.checkpoint_nodiscovery` is the verified checkpoint route for all subsequent row exits and handoffs, avoiding repository auto-discovery quirks.
- **Build Provenance**: Gen3 binary `target/release/wm-gen3` (hash `a5ec583b318bfe269a77e3491205548ec431a8e1a18c77e3af74d9aaa882db44`) remained identical across this implementation because zero code changes were made to Gen3 core, demonstrating compliance with Design Canon §7/§13 anti-bloat laws.
- All 54 Rust-native contract assertions and 8 high-level test suites passed with 0 failures and 0 warnings.
- No verdict, claim, gate, or threshold movement; WEAK stays WEAK.

---

## 5. Attestation

AI session `221fbb57-905f-4e7d-a4d3-3c11810ea0b7` executed `driver_w1_b2_sessions.py`, verified all 7 acceptance criteria and 10 adversarial cases, generated the bundle with `SHA256SUMS`, and records this receipt.
