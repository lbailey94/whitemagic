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
  (see [`docs/MCP_CONFIG_GUIDE.md`](docs/MCP_CONFIG_GUIDE.md)).
- Documentation fixes — docs bugs are real bugs.
- Interoperability mappings (continuity receipts, memory wire formats,
  W3C / IETF drafts).
- Translations — see [Translations](#translations) below; Spanish and
  Portuguese especially welcome, plus the help-wanted list.
- Regression fixtures for the contract harness
  ([`docs/TRACK_LOG.md`](docs/TRACK_LOG.md) is the track ledger contract).

## Translations

The quickstart is the first document most people read, and it ships in four
languages. The current set and the help-wanted list live in
[`docs/TRANSLATIONS.md`](docs/TRANSLATIONS.md):

- [`docs/QUICKSTART.md`](docs/QUICKSTART.md) — English (canonical)
- [`docs/QUICKSTART.es.md`](docs/QUICKSTART.es.md) — Español
- [`docs/QUICKSTART.pt-BR.md`](docs/QUICKSTART.pt-BR.md) — Português (BR)
- [`docs/QUICKSTART.fr.md`](docs/QUICKSTART.fr.md) — Français

**Adding a translation:**

1. Copy the English quickstart (or an existing translation) to
   `docs/QUICKSTART.<tag>.md` (`es`, `pt-BR`, `fr`, `de`, `sw`, `hi`, `ne`, …).
2. Translate the prose. **Leave commands, route names, JSON blocks, and asset
   names exactly as they are** — they are the contract, not copy.
3. Keep it **version-free**: never type a release version into a translation;
   point at the README for the current version so the file cannot rot.
4. Add the language switcher line at the top and add the row to
   `docs/TRANSLATIONS.md` and the README documentation index.
5. Open a PR. **A native speaker must review before merge** — say so in the
   PR if you are one, and we will route a reviewer if you are not. Machine
   translation without a human review is not accepted.

The website's locale work is built on these translations (the plan lives in
the site repo, `docs/MULTILINGUAL_PLAN.md`); site page copy is applied by the
lab, so contributing a quickstart translation here is the way in.

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
  and a profile decision (see [`AGENTS.md`](AGENTS.md)).
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
