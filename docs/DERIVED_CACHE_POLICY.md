# Derived embedding-cache policy — 2026-09-22

Status: policy for the persistent derived embedding cache (`embed_cache` LMDB database). It
resolves the Article 7 boundary recorded as open in `GATE_9A_EXTERNAL_EFFECT_BOUNDARIES.md` and
errata #3/#57. This cache is **derived state**, never canonical evidence.

## Classification

| Property | Value |
|---|---|
| Authority | None. No capability, no receipt; entries are not evidence and cannot be cited as such. |
| Canonical? | No. Canonical records/relations/receipts live in their own databases; cache writes never touch them (tested). |
| Rebuildable? | Yes — from model computation over content; dropping the cache is always safe. |
| Atomicity | Outside the canonical LMDB transaction (Article 9 boundary). A cache write may be lost without affecting any commit. |
| Reachability | Only when projection is enabled: the recall path (`embed_cached`). Projection-enabled intake and sweep refuse fail-closed (Slice 1), and projection-disabled recall performs no cache writes (tested). |
| Key | `{MODEL_ID}:v{EMBED_CACHE_FORMAT_VERSION}:{sha256(content)}` — binds model identity, cache-format version and content. |
| Invalidation | Bump `EMBED_CACHE_FORMAT_VERSION` (all prior keys unreachable); a model change (`MODEL_ID`) also invalidates; changed content changes the hash. |
| Integrity | Trusted local store only; cached vectors are not re-verified against the model on read. |
| GC | Not implemented. Superseded-version entries may remain until a later cleanup pass. |

## Evidence on the current tree

- `versioned_cache_keys_invalidate_on_version_bump` — keys differ across versions and a v1 entry
  misses under the v2 key (`ops.rs::cache_boundary_tests`).
- `cache_writes_leave_canonical_state_unchanged` — records, epoch and relations unchanged after a
  cache write.
- `projection_off_recall_writes_no_cache` — projection-disabled recall performs no derived writes.
- Evil Gana attempt 7: the derived hologram has no handle to the canonical store; runtime test plus
  compile-fail proof (`hologram.rs`, `contract.rs::derived_hologram_index_cannot_mutate_canonical_store`).
- Article 9: cache/model activity is inventoried in `GATE_9A_EXTERNAL_EFFECT_BOUNDARIES.md` with its
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
