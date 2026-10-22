# Verify in five minutes

A reviewer should not have to trust this repository's prose. This page is the
shortest path from "interesting claim" to "I checked it myself", and it says
which claims are checkable and which are not.

Everything below was checked on **2026-10-22** against the live endpoints and
the release artifacts. If a link rots, that is a bug — open an issue.

## 1. The source and the licence

| Check | Where | What it establishes |
|---|---|---|
| Source, MIT licence | <https://github.com/lbailey94/whitemagic> | OSI-approved licence; every claim in this file is reproducible from this tree |
| Receipt spec + verifiers | <https://github.com/lbailey94/continuity-receipt> | The format is separate from the product; two independent implementations |
| Verifier package | <https://pypi.org/project/continuity-receipt/> | `pip install continuity-receipt` — runs offline |

## 2. The zero-egress proof (the claim people most want to check)

```bash
git clone https://github.com/lbailey94/whitemagic && cd whitemagic
cargo build --release --bin wm
WM=$PWD/target/release/wm bash scripts/zero_egress_test.sh
```

The script enters a network namespace whose only interface is a **down**
loopback, asserts that interface set before doing anything, then asserts the
full `serve` → `memory.create` → `memory.search` loop still completes. It
prints `PASS` and exits 0 only if the whole loop worked with no network path.

The same script runs in CI as the
[`zero-egress`](.github/workflows/zero-egress.yml) workflow on every push,
pull request, release tag and a weekly schedule, and the log is uploaded as a
build artifact — so the newest run is always inspectable, not just the one we
photographed.

**What this does not establish:** that no code path could ever attempt egress
on a host that *has* a live interface. The proof is about the product loop
functioning without a network, not about a syscall-level egress ban. The
stricter, kernel-enforced version is work in progress, not a shipped claim.

## 3. Releases, signatures, SBOMs

- Latest stable release: <https://github.com/lbailey94/whitemagic/releases>
- Each release publishes a signed manifest (`release-manifest.json` +
  `.sig`), CycloneDX SBOMs, cosign bundles and per-asset `.sha256` files.
- Verify a downloaded artifact:

```bash
sha256sum -c <artifact>.sha256
cosign verify-blob --bundle <artifact>.bundle --key <published key> <artifact>
```

## 4. Receipts: what a valid signature actually means

Verify a published receipt, or your own:

```bash
pip install continuity-receipt
continuity-receipt verify <receipt.json>
```

A passing check establishes that **the stated key signed these canonical
bytes and they have not changed since**. It does **not** establish that the
claim inside is true, that the signer had authority, that a key was not
revoked, that an action happened, or that a payment settled. A cryptographic
check is narrower than a policy decision, and this repository tries not to
blur the two.

The format, vectors and both reference verifiers are in
[`continuity-receipt`](https://github.com/lbailey94/continuity-receipt);
conformance is claimed for those vectors only.

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