# Bounded answers over explicit assertions

`wm answer-contract` resolves structured assertions supplied by its caller. It accepts an explicit subject, predicate, valid date or two dates, and knowledge cutoff. The operator binds these fields; the command does not infer them from the prose `query`. It does not open a memory store or authenticate the supplied sources.

```sh
wm answer-contract --mode resolve --request-json '{"assertions":[{"record_id":"r1","subject":"Workshop","predicate":"opening_time","value":"09:00","source_id":"schedule","valid_from":"2026-01-01","valid_until":null,"recorded_at":"2025-12-01","supersedes":null}],"question":{"question_id":"example","query":"When does Workshop open on January 2, as known December 15?","subject":"Workshop","predicate":"opening_time","valid_at":["2026-01-02"],"known_at":"2025-12-15"}}'
```

The deterministic `resolve` operation returns a structured decision and record citations derived from the applicable assertions. Its authority label is `caller_asserted_metadata`: a correct result means that the supplied metadata resolves that way, not that the underlying claim is true or complete.

The separate `verify` operation requires an additional `proposal` with `status` (`answer`, `conflict` or `insufficient`) and a `claims` array. Each claim contains exactly `valid_at`, `record_id`, and `value`. For an answer, supply supporting claims for every requested date. For a conflict, supply supported competing values; for insufficient evidence, supply no claims. Wrong scope, time, status, value, record ID or incomplete support is rejected with `accepted: false`, `decision: null`, and reason codes. The verifier does not repair a proposal or return a replacement answer when it rejects one.

Assertions use exact subject and predicate matching. Recording cutoffs are inclusive; valid intervals include `valid_from` and exclude `valid_until`. Date strings mean UTC midnight, while timestamp fields also accept offset-bearing RFC3339. A correction must reference an existing assertion with the same source, subject and predicate, cannot precede its target's recording time, and cannot form a cycle. A known correction terminates the prior assertion from its effective start onward. Expiry of the replacement does not resurrect the prior assertion.

Later recording alone does not choose a winner. Distinct applicable values produce a conflict hold; no applicable value produces an insufficient hold. A question with two dates receives a whole-question status so that an unresolved date cannot become a complete answer. Holds must be handled as holds by callers, even if diagnostic support is included in the decision.

Inputs are bounded to 1 MiB, 512 assertions, 4,096 bytes per string, and one or two strictly ascending requested dates. Unknown fields and malformed assertion graphs fail closed. This contract does not qualify arbitrary prose synthesis, source honesty, cryptographic provenance, native Temporal ledger import, direct-ID authorization, hosted operation or independent operators.
