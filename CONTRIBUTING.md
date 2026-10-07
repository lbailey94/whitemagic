# Contributing

Thanks for considering a contribution. WhiteMagic is a small, evidence-driven
project, and the rules below exist so changes stay reviewable.

## Ground rules

1. **Evidence over adjectives.** Claims in issues and pull requests link to a
   command, a test, or a document. Numbers come from artifacts, never from
   memory or marketing.
2. **The alpha contract is the product boundary** (README → *What it does*).
   Changes outside it are research-surface work: welcome as discussion, but
   they do not ship under the alpha contract.
3. **Tests or it didn't happen.** Behavior changes need a test; bug fixes need
   a reproduction.
4. **Honest degradation.** Optional dependencies (models, embeddings) must
   fail loudly and truthfully, never silently.
5. **AI-assisted contributions are welcome and must be disclosed.** You are
   responsible for what you submit, including its claims.
6. **Be kind.** See [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md).

## Good first contributions

- MCP client configurations and setup notes for clients not yet covered
  (start from [`docs/INDEX.md`](docs/INDEX.md) and [`skill.md`](skill.md)).
- Documentation fixes — docs bugs are real bugs.
- Interoperability mappings (continuity receipts, memory wire formats,
  W3C / IETF drafts).
- Regression fixtures for the contract harness (the generated
  `wm contract --json` manifest is the route/schema authority).
- Translations — coordinated outside this tree; see below.

## Translations

This repository currently ships the canonical English onboarding only
([`README.md`](README.md), [`skill.md`](skill.md), [`llms.txt`](llms.txt)).
The localized quickstart set referenced by older revisions is not present
here; do not add links to it. If you want to translate the onboarding,
open an issue to coordinate placement and review. When a translation lands:
leave commands, route names, JSON blocks, and asset names exactly as they are
(the contract, not copy), keep it version-free, and require a native-speaker
review before merge. Machine translation without a human review is not
accepted.

## Development

Requires Rust 1.85+.

```bash
cargo build                      # debug build
cargo test                       # full test suite
cargo clippy --all-targets       # lint (warnings are treated as review blockers)
cargo fmt --all -- --check       # format check
```

Disk hygiene: never run `cargo clean`; use `scripts/prune_build_cache.sh` or
`cargo clean -p <crate>` only when free space is actually low.

## Pull requests

- One slice per pull request; describe the claim and the evidence.
- Keep the curated surface stable. New tools or routes need an `EffectRow`
  and a profile decision (profiles are defined in
  `crates/wm-gen3-harness/src/bridge.rs`; `wm contract --json` reports the
  compiled catalog).
- Documentation: no unverified numbers. Version and count references are
  generated or dated, never typed.
- Commit messages: imperative and scoped, matching `git log`.
- Do not run `git add -A`; commit your own slice only.

## Security

Do not open public issues for vulnerabilities — see
[`SECURITY.md`](SECURITY.md).

## License

MIT. By contributing you agree that your contribution is licensed under MIT
(© Lucas Bailey and WhiteMagic Contributors). No separate CLA is required.
