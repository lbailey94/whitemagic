# Gate 9A Article 9 — durable and external effect boundaries

Status: source inventory, not runtime qualification or Gate 9A closure. Prepared during the
next hardening round; concurrent changes require rechecking the hashes below.

The supported atomic intake guarantee covers record, lexical postings, allocator, epoch,
operation nullifier and receipt inside one LMDB transaction. It does not guarantee exactly-once
logging, response delivery, network delivery, model computation, or writes in another ledger.
Postings are mechanically derived but transactionally coupled; rebuildability does not exempt
those writes from consistency requirements.

| Surface | Source anchor | Observed behavior | Boundary |
|---|---|---|---|
| Canonical intake | store.rs::commit_intake | One LMDB transaction couples effects and operation ledger | Supported local atomic domain; synthetic reopen/abort evidence, not physical power-loss proof |
| Authorized sweep | store.rs::commit_sweep | One LMDB transaction couples relation effects, both counters, one epoch advance, operation nullifier and tagged receipt; replay validates the persisted plan inertly | Same local atomic domain as intake; abort/reopen, replay, tamper and cross-kind tests in `store::tests::sweep_*` |
| Audit JSONL | journal.rs::Journal::event; ops.rs::Substrate::j | Append + flush; failed event sets journal_ok=false and reports stderr | Not part of LMDB transaction; missing audit event does not imply no commit; flush is not fsync |
| RPC response | harness main.rs::respond / rpc_error | stdout write and flush errors are ignored | Commit may succeed without delivered acknowledgement; stable operation replay is recovery mechanism, not exactly-once delivery |
| Transport replay ledger | transport.rs::DurableReplayStore | Separate prepared/committed append records with sync_all and its own state | Its transport replay guarantee is not an atomic commit with production LMDB; no cross-ledger atomicity established |
| Capability JSONL | capability.rs::NullifierSet | Separate append/fsync reference execution mechanism | Not the canonical LMDB intake ledger; must not pre-burn a production operation outside LMDB |
| Embedding cache | ops.rs::embed_cached; store.rs::put_embedding_cache | Model miss computed then separate cache write, keyed by `{MODEL_ID}:v{format}:{content hash}` | Persistent derived state outside intake receipt; authority/version/invalidation policy resolved as `docs/DERIVED_CACHE_POLICY.md` (derived, rebuildable, versioned; canonical invariance and projection-off no-write tests; GC deferred to 9C) |
| Projection execution | projection.rs::Projection::load / embed | Local artifact preflight and fastembed calls; execution stats | Model/library effects are not within LMDB atomicity; no model execution or library-level no-egress qualification performed in this inventory |
| Diagnostics | ops.rs::Substrate::j; harness main.rs | stderr output | Best-effort external observation, not canonical receipt |

Projection-enabled recall can call embed_cached and persist a cache miss. Read operations
must not be described categorically as side-effect-free on that configuration. A read-only
Store checks writability before cache writes, but that does not itself prove no computation
or other external effect occurred before refusal.

## Remaining acceptance work

- ~~Synthetic journal failure after a successful canonical commit~~ — done:
  `gate9a_article9_acceptance.rs::audit_failure_after_commit_does_not_undo_the_commit`
  (journal at `/dev/full`; commit stands, audit failure reported, authenticated retry replays).
- ~~Response loss/retry across processes~~ — done:
  `lost_acknowledgement_retry_recovers_identical_receipt` (outcome dropped, reopen, identical
  receipt, no second epoch advance). This is recovery by authenticated lookup, not exactly-once
  delivery; the boundary wording above is unchanged.
- ~~Explicit proof that production intake does not create/use the separate capability JSONL ledger~~
  — done: `production_commits_create_no_jsonl_ledgers` (intake + sweep leave only `data.mdb`).
- Keep transport tests scoped to their ledger and protocol. Do not cite WAIL as Article 9 proof
  for atomicity of arbitrary external actions.
- ~~Resolve derived-cache authority/versioning~~ — resolved as derived policy
  (`docs/DERIVED_CACHE_POLICY.md`); GC/model migration remain registered 9C items.

No external execution was performed for this inventory. Source hashes follow:

Updated 2026-09-22 (article-evidence round; sweep row and cache resolution added above):

- `crates/wm-gen3-core/src/ops.rs`: `6110358de643f13d54219c706f805dfbd5c8b3ef1c7f0ef7fc6ccdcad3a6a18b`
- `crates/wm-gen3-core/src/store.rs`: `9610f85e0de6fd18527abaaefc7cde3aa42e45863e55a7ff2097e587fc967235`
- `crates/wm-gen3-core/src/journal.rs`: `12f12a06abd3fae96f84d4ef0238f9523c4c3eadf890c7cb74282a5d8030a60b`
- `crates/wm-gen3-core/src/transport.rs`: `e115f51f2edf0b5876324f5495fa37d8ab0e9fccdc2ed9c5663cb16a4bddf867`
- `crates/wm-gen3-core/src/capability.rs`: `5289d1e696586c9a4e0fb33f46a21dec85887e5c078985d4c308621d7e366480`
- `crates/wm-gen3-core/src/projection.rs`: `0dea408d6a4c5be50bafc739527e4723df754d281b9598a34a244fb1a1ac9ff5`
- `crates/wm-gen3-harness/src/main.rs`: `d6b5bac628a03e4c4351ad5cb75dc92db00f8f7acbc8680b6331d6c11d1615d9`
