# Gate 9A authority and sweep-contract handoff — 2026-09-21

Status: focused evidence for an uncommitted working-tree candidate based on
`981b0bfac7acefb383ef86ef64699e32545c7849`. This is not Gate 9A closure, sweep
implementation, packaged-release qualification, model execution, migration, or
historical activation.

## Completed authority hardening

- Arbitration warrant minting now requires the private `pulse_compiler::CompilerSeal`.
  Production minting is reachable through `PulseTree::arbitrate`; other crate modules
  cannot construct the seal. A `cfg(test)` compiler helper supplies a legitimate
  arbitrated capability for wrong-basis boundary tests.
- Feasibility warrants cannot enter the reference arbitration executor: the typed
  arbitration view, nullifier derivation, and transactional executor return
  `WrongCapabilityBasis` before nullifier registration or mutation.
- Store-authenticated `AuthorizationSnapshot` construction and `CompilerSeal` visibility
  have downstream compile-fail tests.
- `ops::remember_authorized` performs authenticated receipt lookup before budget gates,
  current-epoch snapshot creation, and compiler issuance. The focused replay test retries
  an epoch-0 request after epoch advances to 1 and budget is exhausted; replay succeeds,
  establishing the ordering through observable behavior.

## Sweep contract recommendation

`docs/GATE_9A_SWEEP_TRANSACTION_PLAN.md` now specifies the same `CommitCapability`, exact
ordered effects, and hard preflight bounds for records, postings bytes, token occurrences,
relations, pair examinations, and effects. Exceeding any bound refuses without mutation or
operation consumption. No numeric constants were invented: the repository has no measured,
ratified values for all six dimensions, so sizing and ratification remain blockers.

Existing promotion and demotion semantics require a manifest-bound trusted process-local
usage snapshot. The receipt discloses its digest and process-instance ID. Restart loses that
usage lineage and can change lifecycle eligibility until new recalls occur. Age-only demotion
is excluded because it does not preserve current behavior.

No sweep Rust types or canonical sweep writer were added. Current direct sweep/relation paths
remain outside compiler authorization, so Article 1 is not yet closed for those effects.

## Focused checks

| Command | Result |
|---|---|
| `cargo check --offline --locked -p wm-gen3-core --no-default-features` | pass |
| `cargo test -p wm-gen3-core --offline --locked capability::tests -- --nocapture` | 8 passed |
| `cargo test -p wm-gen3-core --offline --locked pulse_compiler::tests -- --nocapture` | 14 passed |
| `cargo test -p wm-gen3-core --offline --locked contract::tests -- --nocapture` | 1 passed |
| `cargo test -p wm-gen3-core --offline --locked --doc` | 12 passed |
| `cargo test -p wm-gen3-core --offline --locked authenticated_replay_precedes_budget_and_stale_epoch -- --nocapture` | 1 passed |
| targeted `git diff --check` | pass |

Terra independently reported nine passing focused Store tests after consuming the test-only
compiler helper. That result is coordination evidence and was not rerun by this workstream.

## File hashes at handoff

```text
5289d1e696586c9a4e0fb33f46a21dec85887e5c078985d4c308621d7e366480  crates/wm-gen3-core/src/capability.rs
b511013a550adccd7b0eb071bb58c209d50fd3802e89c464033ec9e6f91ff3a8  crates/wm-gen3-core/src/pulse_compiler.rs
08de833a383c83f295745da554b781f93cfc3ed04e27d5c6a66091e18670dfc1  crates/wm-gen3-core/src/intake.rs
69ed25ddf664215754810d205a0cc21ab3bc95b9bbd32d09456884962f57ed2a  crates/wm-gen3-core/src/ops.rs
97bf24460edba5c23006427fcd7ab55006d0910f692e9c195022d36a84e76fd1  crates/wm-gen3-harness/src/main.rs
33b35680e720bfb77151c5a6520bfe15a9f6d6d08e5a766c3eddb5547c7bd2a7  docs/GATE_9A_SWEEP_TRANSACTION_PLAN.md
```

These hashes identify the shared working-tree files at the handoff instant. Some files include
earlier convergence work from other workstreams; the hashes do not attribute sole authorship.

## Remaining risks and decisions

1. Sweep/relation creation, lifecycle changes, sweep-counter allocation, and any legacy automatic
   sweep still need one compiler-authorized LMDB transaction and removal of bypass writers.
2. Six numeric preflight limits require measured synthetic sizing and explicit ratification.
3. Process-local usage is trusted whole-process evidence, not durable or independently signed.
   A later durable-usage protocol would require its own authorized canonical write path.
4. `CommitCapability::claim` remains public for the existing public arbitration API. The warrant
   is opaque and its production mint paths are compiler-sealed, so claim alone cannot forge
   authority. Making claim private would require a broader arbitration API change.
5. This focused pass does not supersede the earlier convergence receipt and did not run the full
   workspace, release binary, harness smoke, model-dependent, physical crash, or M0–M8 suites.
