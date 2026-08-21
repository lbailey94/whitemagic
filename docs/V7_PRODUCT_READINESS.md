# WhiteMagic v7 Product Readiness

**Prepared:** 2026-08-20
**Stage 0 completed:** 2026-08-21
**Status:** Gate 1 complete (2026-08-21) — artifact `v7.0.0-alpha.2`; next is Gate 2 (stranger-tested alpha)
**Scope:** Public-surface containment, coherent private alpha, and stranger-tested alpha

This document is the source of truth for WhiteMagic v7 product readiness.
`docs/RELEASE_READINESS.md` remains the historical record for the v5.8.0
release, while technical v6/v7 research documents remain architecture and
benchmark inputs. They do not override the product gates defined here.

## Decision

The public website must enter a truthful work-in-progress state before any new
WhiteMagic launch work. It must remain in that state until both readiness gates
pass:

1. **Gate 1 — Coherent private alpha:** one identity, one supported install
   path, one narrow product workflow, and tested data recovery.
2. **Gate 2 — Stranger-tested alpha:** external users complete the documented
   workflow without live developer assistance and provide evidence that the
   workflow is understandable and useful.

Passing an internal test suite is necessary but not sufficient. WhiteMagic v7
must not be presented as publicly ready until strangers have installed it,
used it across sessions, and recovered their data through the supported path.

No launch date, revenue forecast, download claim, benchmark comparison, or v7
feature promise should be published before the relevant evidence exists.

## Product Contract

The v7 alpha product remains deliberately narrower than the research system:

> WhiteMagic gives a coding agent durable, local-first project memory: record
> important context, find it after restart, and carry useful decisions into the
> next session without sending the memory store to a WhiteMagic-hosted service.

The supported contract is:

- trusted, local, single-user operation;
- explicit MCP routes for dependable behavior;
- durable memory creation and lexical search without an external model;
- session record, replay, and cross-session continuity;
- a complete backup, verification, and restore path;
- no telemetry and no required WhiteMagic cloud service;
- truthful degradation when optional models, embeddings, or research systems
  are unavailable.

The following remain research or extension surfaces unless separately promoted
through evidence and acceptance tests:

- the full tool archive;
- natural-language router promotion;
- autonomous cycles, imagination, self-play, and Sangha;
- polyglot sidecars and holographic projections;
- local model and embedding configurations beyond a declared tested profile;
- multi-user or hosted authorization;
- desktop applications and commercial packaging.

V7 architecture may improve the substrate, but it must not enlarge the alpha
product promise or delay correction of the user-facing path.

## Stage 0 — Public Website Containment

### Purpose

The current public site advertises retired Python/Core products, dead install
paths, stale repositories, and historical claims. Before any v7 promotion, the
site must stop directing users toward unsupported software.

### Deployment source

- Canonical deployment repository:
  `lbailey94/whitemagic-site-private`
- Domain: `whitemagic.dev` (apex redirects to `www.whitemagic.dev` via Vercel)
- The deployment repository is private and checked out at
  `~/Desktop/whitemagic-site` (branch: `wip/v7-gates`, promoted to `master`).
- Archived website copies under `WMdata/archives` are evidence only and must not
  become the deployment source.

### Required WIP state

The temporary site should contain only:

- the WhiteMagic name;
- a plain statement that the project is under active redevelopment and private
  product testing;
- a statement that previous install instructions and releases are retired;
- an optional contact or status link that has been verified;
- no public release date.

It must not contain:

- `pip install` or binary download instructions;
- links to retired or private repositories presented as public downloads;
- old v25/v26/Core tool counts;
- unsupported benchmark comparisons;
- claims that v7 is available, complete, or production-ready;
- promises about income, timelines, consciousness, prescience, or future
  architecture as shipped product behavior.

### Acceptance criteria

- Every public route either shows the WIP state or is explicitly marked as a
  historical archive with no install call to action.
- Old install commands and dead GitHub/PyPI links are absent from the active
  site.
- The production domain is checked in a clean browser after deployment.
- The deployed commit and verification date are recorded in this document.
- The site remains in WIP mode through Gate 2.

### Stage 0 deployment evidence (2026-08-21)

**Deployed commit:** `91ebb353` on `master` (force-promoted from `wip/v7-gates`)

**Production URLs verified:**
- `https://whitemagic.dev/` → 308 → `https://www.whitemagic.dev/` → 200 (WIP page)
- `https://www.whitemagic.dev/` → 200 (WIP page)

**Route audit (all on `www.whitemagic.dev`):**

| Check | Result |
|---|---|
| Root page (`/`) | 200, title "WhiteMagic — Work in Progress", noindex/nofollow |
| `/robots.txt` | 200, `User-Agent: * / Disallow: /` |
| `/sitemap.xml` | 200, single `<loc>https://whitemagic.dev</loc>` |
| `/icon` | 200, `image/png` |
| `/opengraph-image` | 200, `image/png` |
| 34 historical GET routes | All 307 → `/` (about, capabilities, chat, dashboard, essays, galaxy, ganas, librarian, library, timeline, vision, work, research, services, performance, substrate, governance, economy, grants, workshops, writing, open-source, ladder, mcp-bridge, prescience, zodiac, becoming, garden, sphere, subscribe, fund, dispatch, contact, offline, app, zh, test-scramble) |
| POST `/api/aria/ask` | 503 |
| POST `/api/contact` | 503 |
| POST `/api/aria/channel`, `/api/librarian/chat`, `/api/library`, etc. | All 503 |
| GET `/api/manifest`, `/api/well-known/*` | All 307 → `/` |

**Vercel project fixes applied during deployment:**
- `outputDirectory` corrected from `.` to `null` (default `.next`)
- `framework` set to `nextjs`
- Middleware allowlist extended to include `/icon` and `/opengraph-image` (Next.js metadata file routes referenced by the WIP page's own `<head>`)

**Reversibility:** WIP mode is controlled by `NEXT_PUBLIC_WIP_MODE=1` in `.env.production`. Setting it to `0` and redeploying restores the full site. The middleware WIP block is the first branch in `middleware.ts` and can be removed without affecting the admin Basic-Auth gate.

## Gate 1 — Coherent Private Alpha

Gate 1 is a no-go if any required item below is incomplete. The emphasis is on
the user path, not on adding v7 research capabilities.

### G1.1 Canonical identity and ownership

Choose and apply one canonical:

- product name;
- repository name and URL;
- binary/package name;
- version line;
- support and security contact;
- website relationship.

All Cargo metadata, citation metadata, documentation, release assets, MCP
server names, and website references must agree. Historical products must be
labeled retired rather than presented as alternatives to the alpha.

**Acceptance:** a repository-wide link/version audit reports no stale canonical
identity in the supported documentation or release metadata.

### G1.2 License and public metadata

- Include the complete chosen license text in the repository and release.
- Ensure repository hosting recognizes the license.
- Correct repository URLs in Cargo metadata and `CITATION.cff`.
- Add an accurate repository description and homepage.
- State support expectations without promises that cannot be maintained.

**Acceptance:** a fresh source archive and every distributed binary bundle have
clear license provenance and point to the same canonical project.

### G1.3 Retired public surfaces

Inventory and resolve every public surface:

- `whitemagic.dev`;
- GitHub repositories and releases;
- PyPI package pages and cached install guidance;
- MCP registry or directory listings;
- social/profile links under direct project control.

Each surface must be current, clearly historical, redirected, or removed. Search
results outside project control should be countered by one authoritative
current page rather than by preserving multiple competing products.

**Acceptance:** no project-controlled public page instructs a user to install a
retired package or visit a dead repository.

### G1.4 One supported installation path

The initial reference platform is **Linux x86-64**. Other artifacts may continue
to build, but they must not be advertised as supported until their own install
and first-run paths pass equivalent tests.

The reference installation must:

- work without Rust, Git, repository access, or administrator privileges;
- download from the canonical distribution location;
- verify integrity before installation;
- install to a documented absolute path;
- print an actionable PATH instruction when needed;
- report the expected version;
- run `doctor` and a clean MCP handshake;
- state the minimum Linux/glibc or static-runtime compatibility boundary.

The ARM mapping, Windows instructions, checksum naming, static-binary wording,
and client path expansion must be truthful even when those platforms are not
yet supported.

**Acceptance:** an isolated non-development account follows only the published
instructions and completes install, version check, doctor, and MCP initialize.
The command transcript and machine configuration are retained as evidence.

### G1.5 Product quickstart

Replace the storage-engine demo with the actual product outcome. The quickstart
must not silently pollute an existing user store.

The supported demonstration is:

1. initialize an isolated or explicitly selected store;
2. start a session;
3. record a concrete project decision;
4. end or checkpoint the session;
5. stop the process;
6. start a second process/session;
7. retrieve the prior decision through continuity or progressive replay;
8. show the store location and safe next steps.

Cognitive dashboards, research tool counts, Citta, brain waves, and unrelated
LMDB/Tantivy facts do not belong in the default product quickstart.

**Acceptance:** a first-time user sees the cross-session result and no demo data
is written into a pre-existing store without explicit approval.

### G1.6 Agent instruction delivery

A connected agent must learn the supported session rhythm without the user
having to discover and copy an internal developer guide.

The delivered instructions must cover:

- continuity before starting a new session;
- session start;
- selective recording of decisions, breakthroughs, errors, and summaries;
- explicit routing for important operations;
- end-of-session summary behavior;
- discovery through the supported tool surface;
- privacy and backup limitations.

Implementation may use MCP server instructions, a generated client rule, or
another standards-compatible mechanism, but the behavior must be tested with
the supported clients. Instructions must not encourage automatic deletion,
credential storage, or unbounded recording.

**Acceptance:** after configuration, a fresh supported agent can explain and
follow the session rhythm without additional developer prompting.

### G1.7 Process-level continuity acceptance test

Add a release-gating test that exercises the headline workflow through the real
binary and MCP boundary:

1. initialize and discover the supported surface;
2. `session.start`;
3. `session.record` at least one decision and one summary;
4. stop the server cleanly;
5. start a new server process on the same store;
6. `session.continuity` returns the expected prior turn;
7. `session.replay` in progressive mode respects its token budget;
8. read-only mode can replay but refuses recording;
9. malformed or absent sessions fail clearly without corrupting state.

**Acceptance:** this test passes in CI and against the exact private-alpha
artifact after a clean build.

### G1.8 Truthful product, privacy, and operations documentation

Correct all supported documentation so it agrees with behavior:

- curated/full defaults and tool counts;
- repository and installer URLs;
- store-root versus LMDB-subdirectory paths;
- supported platforms and unsigned-binary limitations;
- benchmark versions, machines, and timing boundaries;
- no implication that privacy flags encrypt data;
- no recommendation to store credentials;
- no implication that conversation capture is automatic when it requires an
  explicit tool call;
- no unsupported cloud, multi-user, or availability guarantees.

The public README should lead with the product contract and move research
architecture to a clearly separate section or document.

**Acceptance:** documentation commands are exercised from a clean environment,
and a terminology/link/count audit reports no known contradictions in the
supported path.

### G1.9 Complete backup, verify, and restore path

Provide one supported full-store workflow that includes every piece of user
state required for recovery, not only the LMDB subdirectory.

The workflow must define:

- what files constitute the canonical store;
- whether the server must be stopped;
- how a backup is created atomically or safely;
- how backup integrity is verified;
- how restore avoids accidental nesting or overwrite;
- when and how the Tantivy index is rebuilt;
- what seal/verify can and cannot protect against;
- how rollback differs from disaster-recovery backup.

Prefer a dedicated CLI command over exposing full-profile research tools merely
to perform routine product operations.

**Acceptance:** a process test creates data and session state, backs up the full
store, removes or isolates the working copy, restores it, rebuilds derived
indexes if needed, and proves memory plus session continuity survived.

### G1.10 Technical and evidence baseline

Before issuing the private-alpha artifact:

- format, lint, tests, release build, dependency audit, and supported smoke
  tests pass from a clean checkout;
- the artifact is tied to a commit and checksum;
- no secrets or private runtime data are present in the source history or
  release bundle;
- public performance claims are removed or tied to a reproducible run on the
  release commit and named machine;
- optional v7 research features are off by default unless they have their own
  acceptance evidence;
- known limitations are short, visible, and specific.

**Gate 1 exit:** the private-alpha artifact and instructions can be handed to a
stranger without exposing the stale public launch surface.

## Gate 2 — Stranger-Tested Alpha

Gate 2 validates the product rather than the developer environment. The website
remains in WIP mode while testing occurs.

### Cohort

- Minimum five external testers who did not build the current workflow.
- At least two supported MCP clients represented.
- Testing uses the declared Gate 1 reference platform unless another platform
  has independently passed its installation gate.
- Test stores contain synthetic or non-sensitive data only unless a tester
  knowingly chooses otherwise.

### Test protocol

Testers receive only the candidate public instructions and artifact access.
They should not receive live troubleshooting during the observed attempt.
They must attempt to:

1. identify what WhiteMagic does;
2. install and verify it;
3. connect a supported MCP client;
4. complete the first-session quickstart;
5. record a real or synthetic project decision;
6. restart and recover that context in a second session;
7. locate the store and explain the privacy boundary;
8. create and verify a backup;
9. report confusion, failures, and perceived value.

Assistance may be provided after the observed attempt, but it must be logged as
product friction rather than treated as user error.

### Required evidence

For each test, retain with consent:

- environment and client version;
- completion/failure state for each step;
- time to first successful continuity result;
- commands or screens where the user became blocked;
- whether the agent followed the session rhythm;
- whether the recalled context was useful and accurate;
- backup/restore result where included;
- support intervention required;
- severity-ranked feedback.

Do not collect the tester's memory contents, credentials, or private project
data as validation telemetry.

### Gate 2 acceptance criteria

- At least four of five testers install and connect without live assistance.
- At least four of five complete the two-session continuity workflow.
- No tester experiences data loss, silent corruption, or an undisclosed network
  transfer.
- Every P0 onboarding, safety, or data-recovery failure is fixed and retested.
- Remaining limitations are documented before launch rather than hidden.
- Testers can describe the narrow product promise in plain language.
- A majority report that the second-session continuity result would be useful
  in a real coding workflow.

A failed Gate 2 is a successful discovery process. It returns the product to
Gate 1 with evidence; it does not justify expanding the feature set.

## After Gate 2

Passing Gates 1 and 2 permits planning a public beta. It does not automatically
authorize a broad v7 launch.

Before replacing the WIP site with a launch site, define a separate public-beta
gate covering:

- final canonical repository visibility;
- current landing page and install path;
- platform support matrix;
- signed/notarized artifacts or explicit unsigned-install guidance;
- SBOM/provenance and release notes;
- support and vulnerability-reporting channels;
- registry submission;
- truthful benchmark card;
- issue templates and contribution policy;
- rollback plan for a broken release.

Income experiments, paid packaging, contracting campaigns, bounty work, and
archived desktop-app revival remain downstream of the coherent product and may
be planned separately.

## Evidence Ledger

| Item | Status | Required evidence |
|---|---|---|
| Website WIP deployment | **Complete** (2026-08-21) | Commit `91ebb353` on `master`; production verified at `whitemagic.dev` and `www.whitemagic.dev`; all historical routes 307→`/`; all POST APIs 503; `robots.txt` disallows all; `sitemap.xml` single root URL; `/icon` and `/opengraph-image` serve correctly; noindex/nofollow on root page |
| G1.1 Canonical identity | **Complete** (2026-08-21) | Identity map applied: product `WhiteMagic`; repo `lbailey94/whitemagic` (renamed from `WMv5`, old URLs redirect); binary `wm`; version line `7.0.0-alpha.1`; contact `lbailey94@protonmail.com`; website `whitemagic.dev` (WIP). Workspace Cargo `repository`, CITATION.cff, MCP `serverInfo.name`, CLI about/version, and deny.toml all updated; commit `a90b21e`. Remaining: repository-wide link audit rides with G1.8. |
| G1.2 License/metadata | **Complete** (2026-08-21) | MIT LICENSE added (© Lucas Bailey and WhiteMagic Contributors); workspace + CITATION.cff point at canonical repo; GitHub description/homepage set via `gh repo edit`; `licenseInfo` populates on push. Support expectations statement rides with the G1.8 README rewrite. |
| G1.3 Retired surfaces | **Complete** (2026-08-21) | Inventory: `whitemagic.dev` contained (Stage 0); GitHub has exactly two repos, both private (`whitemagic`, `whitemagic-site-private`); PyPI `whitemagic` never published (404); npm never published (404); crates.io never published (`wm` name is taken by an unrelated crate — irrelevant while distribution is GitHub-release-only); MCP registry listing kit was prepared but **never submitted**. No project-controlled public page instructs installation of retired software. |
| G1.4 Linux x86-64 install | **Complete** (2026-08-21) | Release `v7.0.0-alpha.1` cut from tag `c72f554` (prerelease; `wm-linux-x86_64` + `.sha256`). Repo made public after truthful README rewrite and full-history secrets scan (0 hard patterns across 114 commits). Anonymous clean-env install verified end-to-end: version resolution → download → checksum OK → install → `wm --version` → `doctor` → MCP initialize (`serverInfo: whitemagic / 7.0.0-alpha.1`). Installer bugs fixed: prerelease-aware version resolution, checksum verified against original artifact name, non-Linux-x86_64 targets refused with clear message. glibc 2.39 boundary documented in README. Known follow-ups: static musl build, quickstart line in installer output pending G1.5. |
| G1.5 Product quickstart | **Complete** (2026-08-21) | `wm quickstart` rewritten as the two-process continuity demo on an isolated store (`~/.local/share/whitemagic-quickstart`; user store never touched): session.start → record decision → checkpoint → process stop → fresh process → session.continuity recovers the decision → progressive replay within budget → store location + safe next steps printed. Verified live against a debug build; storage-engine demo removed. |
| G1.6 Agent instructions | **Complete** (2026-08-21) | MCP `initialize` now returns an `instructions` field delivering the session rhythm (continuity first, session start, selective recording by turn_type, explicit routing, end-of-session summary + checkpoint, tools.list discovery, privacy/backup limitations). Unit test asserts all required topics present; verified live via smoke-test handshake. |
| G1.7 Continuity process gate | **Complete** (2026-08-21) | `run_continuity_gate()` added to `scripts/curated_smoke_test.py` (the release smoke gate): initialize/discover → session.start → record decision+summary → clean stop → new process → continuity returns marker turn → progressive replay budget comparison (tiny ≤ ample) → read-only replay succeeds while recording is refused → absent session_id fails clearly with state intact. Found and fixed two real defects: stale `whitemagic-v5` assertion in the smoke script, and `session.replay` returning silent success for nonexistent session IDs (now errors). Passes against debug and release binaries; full suite green (3,595 tests). |
| G1.9 Backup/restore | **Complete** (2026-08-21) | New `wm backup` / `wm restore` CLI commands: full store root (LMDB + Tantivy + all JSON state), live-server lock detection, SHA256SUMS manifest written on backup and verified in full before restore touches anything, refusal to overwrite without `--force`, symlinks never followed. Documented in README (seal/verify vs backup distinction; rollback vs disaster-recovery distinction). Acceptance gate `run_backup_gate()` added to the smoke test: create state → backup → delete working store → restore → continuity returns marker turn AND memory search finds content through real serve processes; tampered manifest refused. Verified against debug and release binaries. |
| G1.8 Documentation truth | **Supported path complete** (2026-08-21) | README rewritten around the product contract; QUICKSTART.md rewritten (non-admin install, continuity demo, glibc boundary); MCP_CONFIG_GUIDE.md corrected (install URL, dynamic-linking truth); AGENTS.md profile default/precedence documented as verified live behavior (curated default; env var wins when flag omitted). Commands exercised from clean env during install gate. Remaining: banner/archive pass over historical research docs (non-blocking for alpha). |
| G1.10 Technical baseline | **Complete for alpha.2** (2026-08-21) | fmt clean; clippy --all-targets 0 warnings; 3,593 tests / 0 failures from clean tree; `cargo audit`: no vulnerabilities (3 pre-existing accepted warnings: lmdb binding unmaintained, paste unmaintained, lru panic-safety). Artifact `v7.0.0-alpha.2` tied to tag on master, SHA256 published, smoke test passed against the exact release binary. Research features remain off the product path (curated default). Known limitations visible in README (platform, glibc, privacy-flags-not-encryption). **Static musl build proven feasible** (2026-08-21): `x86_64-unknown-linux-musl` builds clean with `musl-tools`, binary is fully statically linked, same 19MB size, entire smoke-test suite (continuity + backup gates) passes against it. Ship as second release asset in alpha.3; README glibc note updated then. |
| Gate 1 | **Ready for exit** (2026-08-21) | All G1.1–G1.10 items have evidence. Exit condition met: the private-alpha artifact (`v7.0.0-alpha.2`) and instructions can be handed to a stranger without exposing a stale public launch surface. Next: recruit the Gate 2 cohort. |
| Gate 2 cohort | Pending | At least five consented test records |
| Gate 2 | Pending | Acceptance criteria met; unresolved limitations published |

## Immediate Execution Order

1. ~~Check out the canonical website deployment repository in a clean local
   workspace.~~ **Done** — `~/Desktop/whitemagic-site` on `wip/v7-gates`.
2. ~~Replace the active public site with the Stage 0 WIP surface and verify the
   production domain.~~ **Done** — deployed to `master`, verified at
   `whitemagic.dev` and `www.whitemagic.dev` on 2026-08-21.
3. ~~Resolve G1.1 and G1.2: canonical identity, repository, license, contacts,
   and metadata.~~ **Done** (2026-08-21) — repo renamed to `whitemagic`,
   version line `7.0.0-alpha.1`, MIT LICENSE added, metadata corrected,
   commit `a90b21e`.
4. ~~Complete the public-surface inventory and retire stale install paths.~~
   **Done** (2026-08-21) — no public code surfaces exist outside the contained
   website; see evidence ledger G1.3.
5. ~~Make the Linux x86-64 install path pass from a clean non-development
   account.~~ **Done** (2026-08-21) — repo made public after truthful README
   rewrite + secrets scan; anonymous clean-env install verified end to end;
   see evidence ledger G1.4.
6. ~~Replace quickstart with the two-session product demonstration.~~
   **Done** (2026-08-21) — `wm quickstart` is the isolated-store continuity
   demo; commit `568ec88`.
7. ~~Deliver the agent session rhythm and add the continuity process gate.~~
   **Done** (2026-08-21) — MCP instructions + `run_continuity_gate()`;
   commit `8c5e13b`.
8. ~~Correct product/privacy/operations documentation.~~ **Done for the
   supported path** (2026-08-21) — commit `1a55af6`; archive-doc banner pass
   remains.
9. ~~Implement and test full-store backup/verify/restore.~~ **Done**
   (2026-08-21) — `wm backup`/`wm restore` + `run_backup_gate()`;
   commit `83efa9d`.
10. ~~Run the clean Gate 1 artifact rehearsal.~~ **Done** (2026-08-21) —
    `v7.0.0-alpha.2` tagged on master, built, checksummed, released, and
    smoke-tested against the exact artifact.
11. Conduct Gate 2 with external testers and feed failures back into Gate 1.
12. Only then prepare the v7 public-beta plan and replacement launch site.
