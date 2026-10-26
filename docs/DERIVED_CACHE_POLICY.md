# Derived embedding-cache and projection-vector policy — updated 2026-10-25

Status: policy for the persistent derived embedding cache (`embed_cache` LMDB database) and
per-record projection vectors (`embeddings` LMDB database). It resolves the Article 7 boundary
recorded in `archive/gate9a/GATE_9A_EXTERNAL_EFFECT_BOUNDARIES.md` and errata #3/#57, and supersedes
the historical Gate 9A Slice 1 projection-intake exclusion following Gate 9C requalification. Both
databases hold **derived state**, never canonical evidence.

## Classification

| Property | `embed_cache` (content-hash cache) | `embeddings` (per-record projection vectors) |
|---|---|---|
| Authority | None. No capability, no receipt; entries are not evidence. | Derived from committed records (`CommitReceipt.vector_effect == 0`). |
| Canonical? | No. Canonical records/relations/receipts live in their own databases. | No. Canonical intake commits in `records`/`postings`/`nullifiers`/`receipts` first. |
| Rebuildable? | Yes — from model computation over content; dropping the cache is safe. | Yes — via bounded `Substrate::repair_missing_vectors` (`memory.repair_vectors`), replay, or duplicate-retry repair. |
| Atomicity | Outside the canonical LMDB transaction (Article 9 boundary). | Written in a separate LMDB transaction after `commit_intake`; status is exposed as `ready`, `pending`, `not_requested`, or `record_absent`. |
| Reachability | Only when projection is enabled (`embed_cached`); projection-disabled recall performs no writes. | Written on projection-enabled intake or explicit bounded repair; read-only handles never write. |
| Key / Format | `{MODEL_ID}:v{EMBED_CACHE_FORMAT_VERSION}:{sha256(content)}` | `u64` big-endian record ID → MessagePack `Vec<f32>` (`DIM = 384`, all finite, pinned to `MODEL_ID = "Qdrant/bge-small-en-v1.5-onnx-Q"`). |
| Liveness / T10 Guard | Content-addressed cache only; never indexed directly by recall. | `Store::put_vector` verifies inside its LMDB RW transaction that `record_id` still exists in `records`, preventing repair from ever resurrecting a removed or erased record. |

## Evidence on the current tree

- `versioned_cache_keys_invalidate_on_version_bump` — keys differ across versions and a v1 entry
  misses under the v2 key (`ops.rs::cache_boundary_tests`).
- `cache_writes_leave_canonical_state_unchanged` — records, epoch and relations unchanged after a
  cache write.
- `projection_off_recall_writes_no_cache` — projection-disabled recall performs no derived writes.
- Evil Gana attempt 7: the derived hologram has no handle to the canonical store; runtime test plus
  compile-fail proof (`hologram.rs`, `contract.rs::derived_hologram_index_cannot_mutate_canonical_store`).
- Article 9: cache/model activity is inventoried in `archive/gate9a/GATE_9A_EXTERNAL_EFFECT_BOUNDARIES.md` with its
  distinct durability guarantee.

## Explicit non-claims

- Not "harmless": projection-enabled recall can persist a cache miss, so read operations on that
  configuration are not side-effect-free.
- No dedup or integrity guarantees across model versions beyond key separation.
- No cache GC, size bound, or migration is implemented; 9C owns those (along with projection
  requalification).

## Follow-on (9C register)

1. Cache GC / size bound and optional integrity tag.
2. Model-version migration or cold-cache policy on `MODEL_ID` changes.
3. If the cache ever becomes load-bearing for results, give it a receipted derived-write contract
   rather than treating it as reconstructible-by-assertion.
