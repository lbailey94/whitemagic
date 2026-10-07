# Bundle ↔ journal parity (A2 §1.4 link boundary)

**Status: check landed 2026-09-17 (fold-in register #13) · driver
`receipts/ops_foldin_2026-09-17/driver_parity.py` · no verdict/claim movement.**

**The rule (A2 §1.4):** the Gen2 **evidence bundle v0** is the live product surface (capability
source); the Gen3 **journal** is the evidence surface. Each disclosed field is owned by exactly one
side — **one side discloses, never neither**; a divergence between the two is a *finding*, not a
silent choice. There is no shared store between the systems, so the "join" is a field-semantics
mapping, not value equality (scores in particular are different systems' scales).

## Field mapping (bundle v0 → Gen3 journal)

| Bundle v0 field | Gen3 journal counterpart | Status |
|---|---|---|
| `id` | `selection.decision.selected[].id` + `provenance.chain.result_id` | **covered** |
| `galaxy` | `provenance.chain.chain[0]` = `corpus:<galaxy>:<tags>` | **covered** (the recall response's `galaxy` label is a harness display artifact; the journal source is authoritative) |
| `retrieval.route` | `projection_ran` / `projection_error` / `semantic_candidates` / `arbitration` (single substrate route: lexical ± semantic) | **covered (derived)** |
| `retrieval.score` | `selected[].score` (+ `rank_key`) | **covered** (scale is Gen3's D2 policy — never compared for equality across systems) |
| `retrieval.matched_terms` | — | link-side (not in A2's required reconstruction list) |
| `retrieval.via` | — | link-side (galaxy-merge concept) |
| `source_time.created_at` / `event_time` | — | link-side (Gen3 tracks intake `created_at` durably, no event-time concept) |
| `source_time.basis` | `provenance.chain` (intake source label) | **covered (semantic)** |
| `history.revision_count` / `chain_valid` | — | link-side (Gen2 hash-chain revision history; A3 §1.4) |
| `history.superseded` / `current` | `stratum` / `superseded_by` / `relations_applied`; `include_historical` restores | **covered** |
| `integrity` | — | link-side (Gen2 source-read class) |
| `visibility.private` / `model_exclude` | — | link-side (no Gen3 policy fields) |
| `coverage.representation` / `truncated` / `exact_read_available` | — | link-side (Gen2 content representation) |
| `conflicts{count,pairs}` | Gen3 preserves contradictions in stratum 1 (no adjudication); no `conflicts` event | link-side (A3 §1.2: the bundle is the link-side disclosure of the same discipline) |
| cold-only `unavailable_cold_record` | no cold tier in Gen3 | link-side (A2 case 6 N/A) |

## What the check asserts

For a live recall: every selected result has a complete `provenance.chain` (id/chain), a numeric
`score`/`rank_key`, a `stratum` consistent with `superseded_by`, a parseable `galaxy` from the
source label, and route-derivable fields (`projection_ran`/`projection_error`/`semantic_candidates`/
`arbitration`). It also scans the journal for any claim of Gen2-bundle-only keys
(`bundle`/`visibility`/`integrity`/`conflicts`/`cold`/`private`/`representation`/`truncated`/
`exact_read_available`/`revision_count`/`chain_valid`/`event_time`/`via`/`matched_terms`) — none
may appear. **Result: PASS (2026-09-17, driver + receipt `OPS_FOLDIN_PARITY_AUDIT_2026-09-17`).**

## Divergence policy

If a future change makes a journal-side field disagree with its bundle counterpart (same semantic,
different value within one system's own surface), that is a **finding** to record in
`PHASE4_ERRATA.md`; the wrapper must not choose silently. Cross-system value equality is never
required (different scoring systems by design).
