# Temporal assertions and queries v1

Temporal metadata is an explicit, versioned assertion layer attached to an
existing canonical record. It does not change ordinary intake, native
revisions, recall ranking, or the meaning of `include_historical`. A temporal
assertion records what an operator supplied and when this store accepted it;
it does not verify the asserted fact or authorize an action.

## Assert after intake

Create or revise the canonical record through the existing interface first.
Then call `memory.temporal_assert` (MCP) or `wm temporal-assert
--request-json '<object>'` (CLI). The request names the existing `record_id`,
the exact `namespace`, `subject`, and `predicate`, one scalar `value`, an
operator-declared `source_id`, two explicit valid-time bounds, and a stable
`operation_id` for retry. Optional `supersedes` names a prior temporal
assertion ID, not a record or relation ID.

Each assertion describes one field. Correcting one field therefore leaves
other field assertions available. The binding is the store realm, record ID,
exact content hash, and actual canonical `record.source()`. V1 does not bind an
intake receipt or intake operation identity because reverse receipt lookup is
not exposed here. `source_id` is an operator-declared claim-stream label, not
proof of external identity. The store assigns `recorded_at` on acceptance.
Requests cannot provide or backdate it. Repeating an identical operation ID
is idempotent; reusing it for different input is rejected.

Bounds use one of these exact objects:

```json
{"kind":"instant","at":"2026-06-14T12:00:00-04:00"}
{"kind":"unbounded"}
{"kind":"unknown"}
```

Instants must be strict RFC 3339 with an explicit offset and are normalized to
UTC. Date-only strings, impossible dates, and leap-second spellings are
rejected. Lower bounds are inclusive; upper bounds are exclusive. An
`unknown` bound means the time is not established; it is not infinity.

## Query modes

Use `memory.temporal_query` or `wm temporal-query --request-json '<object>'`.
Every request names a namespace and subject, and may name a predicate.

- `current` uses the store's current valid time and knowledge time. Caller
  `valid_at` and `known_at` overrides are rejected.
- `as_of` requires an offset-bearing RFC 3339 `valid_at`. Optional `known_at`
  asks what the store knew by that acceptance-time cutoff; when omitted, the
  store uses now.
- `history` omits `valid_at` and may set `known_at`. Results are explicitly
  history and do not imply one current value.

The query returns per-predicate evidence and a status such as `resolved`,
`conflict`, `time_unknown`, `no_evidence`, or `history`. A requested predicate
with no evidence remains visible as `no_evidence`. Evidence includes assertion
and record IDs, value, source labels, normalized bounds, acceptance time, and
the bound record content hash. Cross-source incompatible values remain a
conflict; latest-recorded does not mean true. Explicit corrections can end a
predecessor's applicability only when that correction is known by the query
cutoff. Independent overlapping assertions are not silently suppressed.

For example, if a source announces on June 14 that a location change is
effective July 1, an as-of query for June 20 returns the old location while a
July 2 query can include the new one. A correction recorded later does not
rewrite what was known at an earlier `known_at` cutoff.

## Availability and compatibility

This is an experimental v1 for Unix plain stores only. It refuses temporal
assertions and queries whenever at-rest keyring state is `Present` or
`Malformed`, including read-only access; configured/encrypted stores are not
supported because the temporal sidecar is plaintext. The temporal ledger is a
separate plaintext append-only sidecar. A missing ledger means no temporal
evidence and a query does not create it. An assertion requires a writable
store and an explicit ratified channel. Full-profile MCP exposes the write
route only on writable instances; read-only Full exposes query only. Other
profiles do not expose these routes. The adapter rejects unknown request
fields, including any caller-supplied `recorded_at`.

This v1 ledger currently requires Unix file locking. Temporal assertion and
query return an explicit unsupported error on non-Unix platforms; ordinary
record intake and recall are unaffected.

Queries validate that referenced records remain available and match their
stored content binding. If a record is missing, erased, or changed, v1 fails
closed rather than returning a detached value. This is a logical query limit,
not metadata erasure: assertion values remain in the plaintext append-only
ledger, and v1 does not erase them when a canonical record is erased. The
sidecar does not provide independent anti-rollback custody. Existing records
without annotations remain usable through ordinary recall and have no temporal
evidence by default.
