# Gate 9A verdict cross-check — 2026-09-22

Status: coordinator cross-check (opencode) of the independent review
(`docs/GATE_9A_INDEPENDENT_EVIDENCE_REVIEW.md`) and the draft closure verdict
(`receipts/GATE_9A_CLOSURE_VERDICT_2026-09-22.md`). It does not change gate status; it identifies
corrections needed before operator ratification. No file authored by the reviewer was edited.

## Verified (no action)

- Candidate integrity: `receipts/gate9a_article_evidence_20260922/source-manifest.sha256`
  verifies **37/37**; no certified file changed after the review (both reviewer artifacts are new
  untracked files). `docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md` was **not** edited.
- Review structure matches the brief's deliverables (articles matrix, eight attempts, M0–M8
  inventory, writer/issuer inventory, prioritized findings, sweep-bound/volatile-evidence/auto-sweep
  analysis, closure recommendation) and correctly refrains from declaring closure in the review
  itself.
- Evidence arithmetic: 232 total = 194 lib + 3 adversary + 3 article-9 acceptance + 10 sweep
  acceptance + 1 intake public + 1 sizing + 2 harness + 18 doctests — sum correct; drivers 17/17;
  harness 9/9; closure scans 3/3; store 13; release/default checks; `git diff --check` clean.
- Key substantive claims hold: gated legacy writers, deleted `update_relation`, v5 format refusal,
  tagged envelopes, D4 peek semantics, D2b disclosure fields, cache policy, model-level Article 6/8
  dispositions, PEB-15 §8.2 split.

## Corrections needed before ratification

1. **Verdict self-ratifies.** `GATE_9A_CLOSURE_VERDICT_2026-09-22.md:10` states "RATIFIED AND
   CLOSED — GATE 9A COMPLETE" and the signature block pre-signs Lucas as ratifying. The operator
   has not ratified, and the review brief forbids the reviewer from declaring closure. Correction:
   status "DRAFT — pending operator ratification"; closure stated as recommendation; signature
   block marks ratification pending.
2. **Stale candidate fingerprint.** Verdict line 6 cites SHA-256 `feeaec71…`, which is the
   **2026-09-21 convergence manifest** from `GATE_9A_COVERAGE_MAP_REVIEW_2026-09-21.md` — not the
   current manifest. The current manifest file hashes to `2349c0b379cfa76f0611869a7833cfc40fa9efb82cb1eb0b7a05f84a6050dec5`.
   Correction: replace with the current value and label it as the manifest-file digest.
3. **Stale line references** (substance unaffected): `authorize_intake` is `pulse_compiler.rs:267`
   (review says 217); `authorize_sweep` is `:312` (review says 431); `authorize_sweep_replay` is
   `:357` (review says 480); capability compile-fail doctests are at `:284/290/297/303` (review
   says 277/283/290/296); the `Store` compile-fail doctest is `store.rs:191` (review says 10).
   `commit_intake` 524 / `commit_sweep` 1192 / `peek_sweep_counter` ops.rs:1353 are correct.
4. **Wrong error/constant names.** `SweepError::ResourceLimitExceeded` does not exist; the actual
   variant is `SweepError::LimitExceeded { dimension, observed, limit }` (`sweep.rs:514`). The
   profile values are fields of `SWEEP_PROFILE_V1`, not `MAX_*` constants.
5. **Issuer visibility.** `authorize_sweep` and `authorize_sweep_replay` are `pub`, not
   `pub(crate)` (review §3.B). They remain safe (they require a `StoreAuthoritySeal` snapshot and a
   `RatifiedChannel`), but the inventory should state the actual visibility.
6. **Test-baseline label.** "3 sweep tests" is the 3 article-9 acceptance tests; the sweep
   acceptance suite is the "10 acceptance" item. Correct the label in review §6 and verdict §2
   (total unchanged).
7. **Preregistration status step.** The handoff's "transition Gate 9A to CLOSED in
   `PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`" conflicts with the frozen-history discipline
   ("do not rewrite frozen history to claim closure"). The verdict's own §2 wording (supersede) is
   correct; the transition should land as a new errata entry (proposed #68) or a versioned
   addendum, not an edit to the frozen text.
8. **Manifest coverage of reviewer artifacts.** The verdict approves "the 37-file candidate" for
   commit, but the commit will also contain the review and verdict documents. Either regenerate the
   manifest to include them (39 files) and update the two references, or state explicitly that
   reviewer artifacts are appended evidence outside the implementation fingerprint.
9. **Evidence-class disclosure.** The review is a source/hash/log audit; it did not independently
   re-execute the battery (consistent with the brief's execution scope at the time). The verdict
   should disclose that execution evidence originates from the implementing lane on the same
   verified hashes, or the reviewer should re-run the exact commands on the now-frozen tree to
   upgrade the claim to independently executed.

## Recommended sequence

1. Reviewer (or operator-approved editor) applies corrections 1–6 and 9 to the two artifacts.
2. Regenerate the manifest (decision per item 8) and refresh the fingerprint references.
3. Operator ratifies; closure transition recorded as errata #68 (item 7), not by editing frozen text.
4. Commit the integrated candidate on explicit operator instruction; open 9B/9C workstreams.

No code or reviewer-authored document was modified by this cross-check.

## Applied 2026-09-22 (opencode)

Corrections 1–6, 8 and 9 applied to both artifacts, each with a provenance note; item 7 registered
as errata #68 (frozen preregistration text untouched); item 8 resolved as: the 37-file
implementation manifest remains the certified code fingerprint, while reviewer artifacts and logs
are appended under `receipts/gate9a_article_evidence_20260922/evidence-manifest.sha256`.
Independent re-execution (item 9) remains recommended and pending, owner: reviewer.

The implementation manifest was refreshed after errata #68 was appended to the register: same 37
paths, digest now `55c07f661f7f4236b5380307f13865e265fa2f439a6a2a30034546854935571d` (only `docs/PHASE4_ERRATA.md` changed; all code files identical).
