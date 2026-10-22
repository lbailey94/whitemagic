# Governance

WhiteMagic is a single-maintainer project. This file exists so that the
question "who decides, and how do I get a change in?" has a written answer
rather than an inferred one.

## Maintainer

- **Lucas Bailey** — sole maintainer and final decision-maker
  (`@lbailey94`, <security@whitemagic.dev>).
- The maintainer holds commit rights, release signing keys and the hosted
  service credentials. Those are not currently shared.

This is a deliberate, temporary state. The project is small; the honest
description of its governance is "one person, documented process, no
committee". Where that creates risk — a bus factor of one, no second reviewer
— it is listed under *Known limitations* below rather than smoothed over.

## How decisions are made

1. **Bug reports and small fixes** — pull request, review by the maintainer,
   merge when CI is green.
2. **Behaviour changes and new public surfaces** — open an issue first. The
   bar is: does it keep the local-first and offline-verifiable properties
   intact? A change that requires a network call to work, or that makes a
   previously verifiable artifact unverifiable, is refused regardless of
   convenience.
3. **Receipt format changes** — the format lives in
   [`continuity-receipt`](https://github.com/lbailey94/continuity-receipt).
   Changes require a spec revision, new conformance vectors and both reference
   verifiers (Rust and Python) passing the same vectors. A one-implementation
   change is not a format change.
4. **Security-sensitive changes** — see
   [`SECURITY.md`](SECURITY.md). Do not open a public issue.

## Contributions and licensing

- Contributions are accepted under the repository licence (MIT), with no
  copyright assignment required. Sign-off is not enforced today.
- AI-assisted contributions are accepted. The requirement is on the human
  submitting them: you are responsible for the change, and a claim in a commit
  message or PR description should be checkable by someone else.
- Automated change requests (Dependabot, Scorecard, cargo-deny) are enabled;
  each one is reviewed before merge like any other change.

## Releases

- Semantic versioning; stable and experimental channels are tagged separately.
- A release is: signed tag, release manifest, SBOMs, cosign bundles, published
  install artifacts, and green CI on the release commit. The
  [zero-egress workflow](.github/workflows/zero-egress.yml) runs on every
  release tag.
- Older minors are archival (see the support window in `SECURITY.md`).

## Known limitations

Stated so that reviewers do not have to discover them:

- **Bus factor of one.** No second maintainer, no succession plan yet.
- **No third-party security audit.** Self-assessment only (see
  `SECURITY-INSIGHTS.yml`).
- **Branch protection is enforceable but narrow** — the maintainer can merge
  their own changes after CI passes; there is no second human reviewer.
- **No formal RFC process.** Design notes live in issues and in the
  specification repository.

## Changes to this document

Edits to `GOVERNANCE.md` are announced in the issue tracker and take effect
when merged. If the project gains a second maintainer or a fiscal host, this
file is updated in the same change.
