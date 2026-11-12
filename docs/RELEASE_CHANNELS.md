# Release identities and channel gates

Manifest generation requires Python 3.11+ (`tomllib`); source CI uses Python
3.12. The workspace declares Rust 1.92 as its minimum and separately pins the
local toolchain. Record actual release-run compiler identities; a declared
minimum is not a completed test on that minimum toolchain.

The workspace/package version identifies the source under preparation.
It does not establish that a native binary or package has been published.
Preserve existing public tags, signed artifact bytes and stable selectors
while preparing a forward release. A benchmark-only release record does not
satisfy the native release contract.

## Channel labels

The manifest records `open alpha` as an evidence label. A non-prerelease
version in the v11 generation can become the default install selection only
through the separate release-health gates; its major version does not prove
product maturity, operator adoption or completed platform certification.

The active native build and public-installer certification matrix covers
Linux x86-64, Linux arm64 and macOS arm64. Windows and Intel macOS are outside
that matrix. `install_gated` declares a required certification path; the
manifest is published before that path runs. Check the completed Release run
and the exact signed-manifest-bound release-health record for its result.

## Publication order

1. Review the version/source diff and pass CI on the exact release commit.
2. Create a new full-semver tag only after publication is authorized. The
   tag-triggered Release workflow builds assets and signatures, publishes the
   manifest, and certifies every supported public installer path.
3. The registries job waits for installer certification. npm first publishes
   the exact version under `quarantine`; it does not move `latest` or `next`.
4. Release health independently installs the exact native/package/container
   identities. Only its successful gate promotes the applicable npm/Docker
   selector, refusing downgrades. Missing or failed checks remain visible.
5. The Gen3 release tail records a route contract from the released binary.
   Website facts and runtime observations need their own review and preview;
   source preparation or a passing source test does not refresh them.

Do not repair historical benchmark output or relabel old runtime observations
as evidence for a new release. Test counts are optional manifest observations
from the exact source CI; do not copy earlier counts into a new manifest.
