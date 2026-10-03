# Gate 9A hardening report — cross-check against current tree — 2026-09-21

Status: external review artifact (opencode, independent verifier). It re-evaluates the
**Codex Review Pass & Gate 9A Hardening Report** (2026-09-20, held in the Codex/Antigravity threads;
also pasted as an attachment in Codex session `01a0c0d5`) against the current uncommitted working
tree and `docs/GATE_9A_COVERAGE_MAP_REVIEW_2026-09-21.md`. No implementation files were modified.

The hardening report's headline status was "GATE 9A RATIFIED, FROZEN, AND VERIFIED IN TEST
(167/167 tests passing)". That status predates the same-day independent audit that kept Gate 9A
open, and it is not supported by the current tree. Its RED fixes survive; its article matrix
overstates several articles and contains two inventory claims contradicted by the current design.

## 1. Article-by-article cross-check

| Article | Hardening report claim (old refs) | Current enforcement (file:line) | Cross-check |
|---|---|---|---|
| 1 State mutation | "Zero public mutable handles; write authority ONLY via `CommitCapability` bound to payload digest"; cites `pulse_compiler.rs:590`, `store.rs:250`, `pulse_compiler.rs:1883` | `store.rs:493` `commit_intake` consumes `CommitCapability` and revalidates digest/scope/operation/realm/epoch/authority/kind in-txn; `ops.rs:884` production issuance; raw writers `store.rs:809–979` are `pub(crate)` | **Overstated then, partial now.** The report's evidence was the in-memory reference path (`SubstrateStore`/`KernelStore`); the LMDB production writers were only `pub(crate)`, not capability-gated. A later uncommitted candidate added a parallel `IntakeCapability` (`ops.rs:881` per the Sep 20 review), which the convergence removed. Sweep/relation/cache writers remain unauthorized. |
| 2 Remote input | "`contract.rs:180` has no execution methods; tested in `adversary_contract.rs:14`" | `contract.rs:212` `RemoteStimulus` (data only); nearest tests `ganying.rs:1181`, `adversary_contract.rs:44–47` | **Partial.** The adversary "test" is an assertion on passive fields; the declared attempt (feed stimulus into a mutation path) is comment-only. Production admission path still untraced. |
| 3 Foreign confidence | "`contract.rs:150` fails closed" | `contract.rs:192` `try_ingest_remote_conformal_score`; tests `conformal.rs:762`, `contract.rs:334` | **Survives** (model level). No production ingestion→calibration boundary test. |
| 4 Background execution | "`contract.rs:114` fails closed" | `contract.rs:154` `try_spawn_authoritative_loop`; permitted transport threads `transport.rs:592,599` | **Survives at model level; partial overall.** No inventory or static rule over production spawn sites. |
| 5 Canonical identity | "Tested in `relativity.rs` and PEB-14B battery" | Ed25519 auth is `ganying.rs:486`; relativity tests `584/609/630` cover DAG ancestry and identity forks | **Misattributed.** Relativity does not exercise Ed25519 provenance; the socket/IP→identity attempt (Evil Gana #6) has no executable adversary test. |
| 6 Historical causality | "`relativity.rs` enforces Causal Influence Closure by construction; proven in PEB-14B" | `relativity.rs:584,609,630`; benchmark test `615` | **Survives at model level; partial overall** (production mapping outstanding). |
| 7 Shared hologram | "`hologram.rs:30` rejects NaN/Inf; proven in PEB-14C" | `hologram.rs:123` `try_quantize_coords`; tests `653`, `adversary_contract.rs:41` | **Survives for coordinates; partial overall.** Derived-writer boundary open: `ops.rs:539` `put_embedding_cache` has no authority/versioning policy. |
| 8 Feature evolution | "Verified via `cladistics.rs` and formal S⃗ vector tracking" | Pareto tests `cladistics.rs:717–813` | **Partial.** Model-level gate tests only; production evolution entry points and the receipt-bearing requirement are not traced. |
| 9 External side effects | "WAIL two-phase commit preserves zero phantom side-effects" | WAIL lives in the transport/PEB-14A layer; no inventory of audit/replay files, transport effects, model/cache activity | **Category mismatch.** WAIL is a transport replay protocol, not evidence that external effects are explicitly scoped outside local atomicity. Article 9 remains open. |

## 2. Line-reference staleness

Every file:line citation in the hardening report predates the Sep 20 convergence — and several do
not match the base commit `981b0bf` either, meaning they referred to an even earlier working tree.
Checked at `981b0bf`: `pulse_compiler.rs:590` is `pub mutations_applied: usize`,
`pulse_compiler.rs:1883` is a `#[test]` attribute, `store.rs:250` is `alloc_relation_id`,
`contract.rs:180/150/114` are brace/comment lines, and `hologram.rs:30` is a variant in an error
enum. Current mapping: `contract.rs:180→212`, `contract.rs:150→192`, `contract.rs:114→154`,
`hologram.rs:30→123`, `store.rs:250→493/809`, `pulse_compiler.rs:590→217+`,
`adversary_contract.rs:14→36–50`. The report cannot be cited as current evidence without re-mapping.

## 3. Test-total comparison

| Source | Claim | Composition |
|---|---|---|
| Hardening report | 167 passed | 155 lib + 3 integration + 9 doc |
| AGY synthesis §14.3 | 152 passed | 146 lib + 1 integration + 5 doc |
| Slice 1 receipt | 181 passed | 162 lib + 3 + 1 + 2 + 13 doc |
| Current tree (this review) | 180 passed | 165 lib + 3 + 1 + 2 + 9 doc |

The hardening total omits the harness unit tests and predates the public intake integration test;
the doc count later dropped by four with the removal of the superseded `IntakeCapability`
compile-fail doctests (explained in the verification receipt). None of the older totals identifies
the current candidate.

## 4. Inventory discrepancies (hardening report §2)

1. **Postings classified as derived.** The report lists "LMDB embed_cache / postings" together as
   "Derived / Index state … Zero canonical authority". In the current design, lexical postings are
   committed atomically with the record inside `commit_intake` (`store.rs:493`), i.e. they are part
   of the canonical ingestion effect. Only `embed_cache` is derived.
2. **JSONL nullifier journal treated as canonical replay defense.** The report places
   `NullifierSet (journal.jsonl)` in canonical sovereign state and claims write-ahead fsync as
   sufficient. The next review round found the split-brain hazard this creates beside LMDB; the
   current production path uses the LMDB `nullifiers` table inside the same transaction
   (`store.rs:467–547`), and the JSONL journal remains only for the reference-model path
   (`capability.rs:382–454`).
3. **"Rebuildable? Yes (100% from canonical)" for the embedding cache** has no implemented rebuild,
   versioning, or invalidation path or test; it is an aspiration, not evidence.

## 5. What survives from the hardening report

- RED 1: raw LMDB writers remain `pub(crate)`; `SubstrateStore` fields remain private with
  read-only accessors (verified in the current tree).
- RED 2: write-ahead nullifier persistence with `sync_data()` and fail-closed malformed-journal
  handling remain in `capability.rs` and its tests.
- RED 3: payload digest binding remains enforced on both `SubstrateStore::commit` and
  `KernelStore::commit_mutation`, plus the new LMDB path.
- The 4 `CommitCapability` compile-fail doctests and 3 adversary integration tests still pass.
- AMBER 1 (Article 4 / scorecard wording) and AMBER 2 (9A/9B boundary) remain resolved in the
  preregistration text and are consistent with the current closure checklist's §8.2 interpretation.

## 6. Consequences for the closure record

- The hardening report should be retained as a historical audit snapshot, not as current evidence;
  the verdict record should supersede its status line explicitly, without rewriting it.
- Articles 5, 9 (and the article-7 derived boundary, article-8 receipts) need the evidence listed in
  `docs/GATE_9A_COVERAGE_MAP_REVIEW_2026-09-21.md` §E before any "all nine articles" claim.
- The inventory corrections in §4 should be reflected in the final derived/canonical state map,
  since the hardening report's version would misclassify postings and understate the LMDB nullifier
  consolidation.
