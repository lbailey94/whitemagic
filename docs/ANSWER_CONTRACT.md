# Bounded answers over explicit assertions

`wm answer-contract` resolves structured assertions supplied by its caller. It accepts an explicit subject, predicate, valid date or two dates, and knowledge cutoff. The operator binds these fields; the command does not infer them from the prose `query`. It does not open a memory store or authenticate the supplied sources.

```sh
wm answer-contract --mode resolve --request-json '{"assertions":[{"record_id":"r1","subject":"Workshop","predicate":"opening_time","value":"09:00","source_id":"schedule","valid_from":"2026-01-01","valid_until":null,"recorded_at":"2025-12-01","supersedes":null}],"question":{"question_id":"example","query":"When does Workshop open on January 2, as known December 15?","subject":"Workshop","predicate":"opening_time","valid_at":["2026-01-02"],"known_at":"2025-12-15"}}'
```

For files and pipelines, pass `--request-json -` and send the JSON through
standard input:

```sh
wm answer-contract --mode resolve --request-json - < request.json
wm answer-contract --mode verify --request-json - < proposal-request.json
```

This avoids command-line argument size limits and placing the request contents
in the process arguments. The stream reader consumes at most 1 MiB plus one
byte, rejects oversized input, invalid UTF-8 and read failures, and uses the
same strict resolver/verifier as inline JSON. Requests must end with EOF;
the byte limit does not impose a deadline on a stalled producer. Both input
paths run before store resolution and leave the memory store unopened.

The deterministic `resolve` operation returns a structured decision and record citations derived from the applicable assertions. Its authority label is `caller_asserted_metadata`: a correct result means that the supplied metadata resolves that way, not that the underlying claim is true or complete.

The separate `verify` operation requires an additional `proposal` with `status` (`answer`, `conflict` or `insufficient`) and a `claims` array. Each claim contains exactly `valid_at`, `record_id`, and `value`. For an answer, supply supporting claims for every requested date. For a conflict, supply supported competing values; for insufficient evidence, supply no claims. Wrong scope, time, status, value, record ID or incomplete support is rejected with `accepted: false`, `decision: null`, and reason codes. The verifier does not repair a proposal or return a replacement answer when it rejects one.

Assertions use exact subject and predicate matching. Recording cutoffs are inclusive; valid intervals include `valid_from` and exclude `valid_until`. Date strings mean UTC midnight, while timestamp fields also accept offset-bearing RFC3339. A correction must reference an existing assertion with the same source, subject and predicate, cannot precede its target's recording time, and cannot form a cycle. A known correction terminates the prior assertion from its effective start onward. Expiry of the replacement does not resurrect the prior assertion.

Later recording alone does not choose a winner. Distinct applicable values produce a conflict hold; no applicable value produces an insufficient hold. A question with two dates receives a whole-question status so that an unresolved date cannot become a complete answer. Holds must be handled as holds by callers, even if diagnostic support is included in the decision.

Inputs are bounded to 1 MiB, 512 assertions, 4,096 bytes per string, and one or two strictly ascending requested dates. Unknown fields and malformed assertion graphs fail closed. This contract does not qualify arbitrary prose synthesis, source honesty, cryptographic provenance, native Temporal ledger import, direct-ID authorization, hosted operation or independent operators.

The MCP `sutra.contract` / `sutra_contract` route accepts either structured
`assertions`, `question` and optional `proposal`, or a single `request_json`
string. Mixing these forms is refused, including nullable duplicate forms.
`mode` is an optional string (`resolve` by default) and `attest` is an optional
boolean (`false` by default); wrong types are refused. The handler consumes
caller-supplied assertions and does not consult or enforce native-store
sanctuary access. The hosting MCP server may already have its store open.

For compatibility, `attest: true` requests an **unsigned byte digest**, not a
signed attestation or CPR receipt. The result carries `contract_digest`,
`digest_profile: "wm-answer-contract-sha256-v1"`, and
`digest_authentication: "unsigned"`. It does not carry `attestation_spec`.
The digest is SHA-256 over the UTF-8 domain `wm-answer-contract-sha256-v1`
followed by a NUL byte, then three byte strings: mode, the exact JSON request
passed to the resolver, and the compact serialized result before digest
metadata is added. Each string is preceded by its UTF-8 byte length encoded
as an unsigned 64-bit big-endian integer. The result uses this Rust build's
`serde_json` serialization; this is a byte-binding profile, not RFC 8785
canonicalization. Re-serialization may produce a different digest.
Anyone can recompute it; it authenticates no issuer or source. A rejected
proposal retains `accepted: false` and `decision: null` even when a digest
is requested.
