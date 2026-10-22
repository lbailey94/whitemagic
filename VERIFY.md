# Verify in five minutes

A reviewer should not have to trust this repository's prose. This page is the
shortest path from "interesting claim" to "I checked it myself", and it says
which claims are checkable and which are not.

The concrete examples below pin the release and fixture they exercise. Their
results apply to those versions; a moving release page or a passing local
check does not establish the state of a newer artifact or a protected branch.
If a link rots, that is a bug — open an issue.

## 1. The source and the licence

| Check | Where | What it establishes |
|---|---|---|
| Source, MIT licence | <https://github.com/lbailey94/whitemagic> | The source and in-tree licence are available here; this does not establish release provenance or hosted settings |
| Receipt spec + verifiers | <https://github.com/lbailey94/continuity-receipt> | The format is separate from the product and has Python and Rust reference verifiers |
| Verifier package | <https://pypi.org/project/continuity-receipt/> | Pin the tested release with `pip install continuity-receipt==0.5.1` |

## 2. The zero-egress proof (the claim people most want to check)

```bash
git clone https://github.com/lbailey94/whitemagic && cd whitemagic
cargo build --release --bin wm
WM_BINARY=$PWD/target/release/wm bash scripts/zero_egress_test.sh
```

The script checks the selected binary's digest before executing it, then uses
a fresh temporary home, XDG directories, and store. Inside a Linux user and
network namespace it asserts that the only interface is a **down** loopback,
the route tables are empty, and an external TCP negative control is blocked by
namespace routing. It then completes a full-profile JSON-RPC
`initialize` → `memory.create` → exact-ID `memory.search` loop. A namespace
that cannot be created, an unexpected reply, timeout, or host-policy denial
fails without producing a pass.

The [`zero-egress`](.github/workflows/zero-egress.yml) workflow is present on
the open [PR #11](https://github.com/lbailey94/whitemagic/pull/11) branch
`ci/evidence-gates-20261022`. It is configured there for pushes to `main` or
`master`, pull requests targeting those branches, release tags, and a weekly
schedule; it uploads the run log and binary identity. When checked on
2026-10-22, PR #11 was still open, so this workflow had not yet become a
default-branch check. A passing run or uploaded artifact does not establish
that GitHub requires the check for merging.

**What this does not establish:** that no code path could ever attempt egress
on a host that *has* a live interface. The proof is about the product loop
functioning without a network, not about a syscall-level egress ban. The
stricter, kernel-enforced version is work in progress, not a shipped claim.

## 3. Releases, signatures, SBOMs

- Tested release: <https://github.com/lbailey94/whitemagic/releases/tag/v10.5.0>
- The pinned `v10.5.0` release publishes a signed manifest
  (`release-manifest.json` + `.sig`), CycloneDX SBOMs, cosign bundles and
  per-asset `.sha256` files. Other releases need their own asset checks.
- Verify the Linux x86-64 artifact from the pinned `v10.5.0` release:

```bash
curl -fLO https://github.com/lbailey94/whitemagic/releases/download/v10.5.0/wm-linux-x86_64
curl -fLO https://github.com/lbailey94/whitemagic/releases/download/v10.5.0/wm-linux-x86_64.bundle
curl -fLO https://github.com/lbailey94/whitemagic/releases/download/v10.5.0/wm-linux-x86_64.sha256
sha256sum -c wm-linux-x86_64.sha256
cosign verify-blob \
  --bundle wm-linux-x86_64.bundle \
  --certificate-identity 'https://github.com/lbailey94/whitemagic/.github/workflows/release.yml@refs/tags/v10.5.0' \
  --certificate-oidc-issuer 'https://token.actions.githubusercontent.com' \
  wm-linux-x86_64
```

The expected signing identity and issuer above were read from the certificate
in this release's bundle and matched to the `release.yml` workflow and
`v10.5.0` tag. This command was exercised against the published artifact
(SHA-256 `7d7082a470b16f661469aef2e544d32dce57fa6903384c1457f40e928323f1f0`)
with Cosign 2.4.1 and returned `Verified OK`; a wrong-identity control failed.
`sha256sum` checks byte integrity against the downloaded sidecar. The Cosign
check separately verifies the blob signature against the specified keyless
workflow identity and issuer. Neither establishes that the source or release
is free of defects.

## 4. Receipts: what a valid signature actually means

Verify the pinned `continuity-receipt` v0.5.1 full fixture offline:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install continuity-receipt==0.5.1
git clone --depth 1 --branch v0.5.1 \
  https://github.com/lbailey94/continuity-receipt.git continuity-receipt-v0.5.1
test "$(git -C continuity-receipt-v0.5.1 rev-parse HEAD)" = \
  3a4b9c2eb141381517e94def5117d25788c9fb93
continuity-receipt-verify \
  continuity-receipt-v0.5.1/vectors/02_happy_full.json
```

The tested PyPI wheel SHA-256 was
`9268eeff8208a3ac3ee9425c9267a48632d59ddd7044097a5542ee4880183144`, matching
the GitHub v0.5.1 release wheel. The fixture is from tag commit
`3a4b9c2eb141381517e94def5117d25788c9fb93` and returned `TRUSTED` with no
errors. It is a bundle fixture using spec `continuity-receipt/0.1`; the CLI
expects a bundle, not an arbitrary single receipt.

A passing check establishes that **the stated key signed these canonical
bytes and they have not changed since**. It does **not** establish that the
claim inside is true, that the signer had authority, that a key was not
revoked, that an action happened, or that a payment settled. A cryptographic
check is narrower than a policy decision, and this repository tries not to
blur the two.

The format, vectors and both reference verifiers are in the pinned
[`continuity-receipt` v0.5.1 source](https://github.com/lbailey94/continuity-receipt/tree/v0.5.1);
conformance is claimed for the published vectors only.

## 5. Continuous security signals

| Signal | Where | Notes |
|---|---|---|
| Secret scanning + dependency advisory gate | [`.github/workflows/security.yml`](.github/workflows/security.yml) | gitleaks (fixture allowlist in `.gitleaks.toml`), `cargo-deny` policy in `deny.toml` |
| Fuzzing | [`.github/workflows/fuzz.yml`](.github/workflows/fuzz.yml), `fuzz/` | receipt parser and frame decoding targets |
| OpenSSF Scorecard | [`.github/workflows/scorecard.yml`](.github/workflows/scorecard.yml) | score published to the OpenSSF API once the workflow runs on the default branch |
| Dependency updates | [`.github/dependabot.yml`](.github/dependabot.yml) | cargo, actions, npm, docker |
| Security policy | [`SECURITY.md`](SECURITY.md) | private reporting, 48h/7d response targets |

## 6. What is not claimed

Listed because it is easier to check a project's honesty than its marketing:

- **No third-party security audit.** Self-assessment only; see
  [`SECURITY-INSIGHTS.yml`](SECURITY-INSIGHTS.yml).
- **No external adoption claim.** Distribution numbers are install events
  from package registries, not counts of active users. They are quoted from
  the registry APIs at a dated point, never projected.
- **No standards conformance claim.** Mapping notes exist for IETF SCITT
  envelopes and the W3C agent-memory work; those are crosswalks written by us,
  not endorsements or certifications.
- **No benchmarks win claimed against other systems.** The in-tree benchmark
  work is synthetic-fixture and scoped to itself.
- **Single-maintainer governance.** See [`GOVERNANCE.md`](GOVERNANCE.md).

## Feedback

If you are reviewing this for a programme and something here does not hold up,
say so in an issue — a reviewer who finds a broken claim is doing the project a
favour, and the correction gets published rather than quietly edited.
