# Next Session — v7 Product Readiness

**Prepared:** 2026-08-20
**Last updated:** 2026-08-21 (Stage 0 website containment deployed and verified)
**Status:** Stage 0 complete; Gate 1 implementation not yet started

The canonical product-gate plan is
[`V7_PRODUCT_READINESS.md`](V7_PRODUCT_READINESS.md). The historical v5.8.0
release record remains in [`RELEASE_READINESS.md`](RELEASE_READINESS.md).
Technical v6/v7 architecture and benchmark plans do not override the product
gates.

## Current Decision

The public website is now in a truthful work-in-progress state. It will remain
there while WhiteMagic completes:

1. Gate 1 — coherent private alpha;
2. Gate 2 — stranger-tested alpha.

The website must not advertise retired Python/Core installs, dead repositories,
stale benchmark claims, or an available v7 release.

## Current State

- **Stage 0 is complete.** The live website at `whitemagic.dev` and
  `www.whitemagic.dev` serves a minimal WIP notice. All historical routes
  redirect to `/`; all retired API endpoints return 503; `robots.txt`
  disallows all crawlers; `sitemap.xml` contains only the root URL.
- Deployed commit: `91ebb353` on `master` (Vercel production branch), promoted
  from `wip/v7-gates` on 2026-08-21.
- The deployment repository is `lbailey94/whitemagic-site-private`, checked out
  at `~/Desktop/whitemagic-site`.
- Vercel project settings corrected: `outputDirectory` set to default `.next`,
  `framework` set to `nextjs`.
- WIP mode is controlled by `NEXT_PUBLIC_WIP_MODE=1` in `.env.production` and
  the middleware WIP block in `middleware.ts`. Setting the flag to `0` and
  redeploying restores the full site.
- WMv5 contains the strongest tested substrate, while v6/v7 development remains
  active and must be separated from the narrow alpha promise.
- `V7_PRODUCT_READINESS.md` defines the required evidence for every gate and
  contains the full Stage 0 deployment evidence record.

## Completed Work — Stage 0 Website Containment

1. ~~Check out `lbailey94/whitemagic-site-private` into a clean local project
   directory.~~ Done — `~/Desktop/whitemagic-site`.
2. ~~Read its project rules, deployment configuration, current branch state, and
   Vercel linkage before changing files.~~ Done.
3. ~~Preserve a recoverable snapshot through Git history.~~ Done — `wip/v7-gates`
   branch preserved; `master` force-promoted.
4. ~~Replace the active site with a minimal WIP surface.~~ Done — root page,
   `robots.txt`, `sitemap.xml`, middleware redirects, API 503s, SW cleanup.
5. ~~Verify local production build and every public route.~~ Done — 34
   historical routes verified, all POST APIs return 503, metadata routes serve
   correctly.
6. ~~Review the exact deployment diff and confirm no secrets.~~ Done.
7. ~~Deploy only after explicit review.~~ Done — Vercel preview verified, then
   force-promoted to `master`.
8. ~~Verify `whitemagic.dev` in a clean browser and record the deployed commit
   and date.~~ Done — both `whitemagic.dev` and `www.whitemagic.dev` verified;
   evidence recorded in `V7_PRODUCT_READINESS.md`.

## Next Execution Slice — Gate 1 Foundation

Stage 0 is complete. The next work is Gate 1, in the order defined by
`V7_PRODUCT_READINESS.md`:

1. **G1.1 Canonical identity:** choose and apply one canonical product name,
   repository name/URL, binary/package name, version line, support/security
   contact, and website relationship. All Cargo metadata, citation metadata,
   documentation, release assets, MCP server names, and website references must
   agree.
2. **G1.2 License and public metadata:** include the complete chosen license
   text in the repository and release; correct repository URLs in Cargo
   metadata and `CITATION.cff`; add an accurate repository description and
   homepage; state support expectations.
3. **G1.3 Retired public surfaces:** inventory and resolve every public surface
   (GitHub repositories/releases, PyPI package pages, MCP registry listings,
   social/profile links). Each must be current, clearly historical, redirected,
   or removed.
4. **G1.4 One supported install path:** make the Linux x86-64 non-admin install
   path pass from a clean account — download, verify integrity, install, version
   check, `doctor`, MCP handshake.
5. **G1.5 Product quickstart:** replace the storage-engine demo with an
   isolated two-session continuity demo (initialize → start → record →
   checkpoint → stop → restart → retrieve → show store location).
6. **G1.6 Agent instruction delivery:** deliver the supported session rhythm
   automatically to connected agents via MCP server instructions or a generated
   client rule.
7. **G1.7 Process-level continuity gate:** add a release-gating test that
   exercises record → restart → continuity/replay through the real binary and
   MCP boundary.
8. **G1.8 Documentation truth:** correct all supported documentation so it
   agrees with behavior — curated/full defaults, tool counts, repository URLs,
   store paths, platforms, benchmark versions, privacy flags, credential
   storage, conversation capture.
9. **G1.9 Backup/restore:** provide one supported full-store workflow with
   backup, verify, and restore — including all user state, not just LMDB.
10. **G1.10 Technical baseline:** format, lint, tests, release build, dependency
    audit, and supported smoke tests pass from a clean checkout; artifact tied
    to commit and checksum; no secrets; public claims removed or tied to
    reproducible runs.

**Gate 1 exit:** the private-alpha artifact and instructions can be handed to a
stranger without exposing the stale public launch surface.

## Guardrails

- Do not publish a v7 launch date.
- Do not treat architecture completion as product readiness.
- Do not expand the alpha surface with research tools.
- Do not recommend storing credentials; privacy flags are not encryption.
- Do not advertise a platform until its install and first-run path passes.
- Do not preserve public claims merely because they appeared in an older site.
- Do not use developer assistance to convert a failed stranger test into a pass;
  record the friction and return it to Gate 1.
- Do not disable WIP mode on the website until Gate 2 passes.

## Verification for This Documentation Slice

- `V7_PRODUCT_READINESS.md` exists, is linked from active planning docs, and
  contains the full Stage 0 deployment evidence.
- `RELEASE_READINESS.md` is clearly labeled as the v5 historical record.
- v6/v7 architecture notes point to the independent product gate.
- The independent-builder strategy places readiness before launch and income
  forecasts, and marks Stage 0 complete.
- Stage 0 website containment is deployed, verified, and recorded.
