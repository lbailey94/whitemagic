# Monorepo vs Multirepo — Should WhiteMagic "Explode"?

**Created**: 2026-04-18
**Status**: Analysis. Not a decision document. Meant to inform a
future decision, not force one.

---

## The question

Should `WHITEMAGIC/` stay as a single monorepo, or should it be broken
apart into many independent repositories — one per major module?

Concrete candidates for extraction:

- `whitemagic-core` — Python core + CLI
- `whitemagic-rust` — Rust performance bridges + WASM target
- `whitemagic-mojo` — accelerators
- `whitemagic-go` — Go mesh layer
- `whitemagic-elixir` — Elixir supervision
- `whitemagic-koka` — Koka effect system experiments
- `whitemagic-sdk-ts` — TypeScript SDK (`@whitemagic/sdk`)
- `whitemagic-mcp-server` — MCP stdio server binary (the Seed Binary)
- `whitemagic-grimoire` — the conceptual documentation
- `whitemagic-site` — the consultancy site (already separate)
- `whitemagic-pwa` — the browser-installable app
- `whitemagic-hub` — the Tauri desktop wrapper

Potentially a dozen+ repos.

---

## Arguments for exploding

### 1. Release cadence independence

The Rust WASM build can ship weekly; the Python core can ship monthly;
the site can deploy continuously. In a monorepo, CI has to be smart
about path-based triggers, and a "tag" still covers everything. In
separate repos, each module has its own release schedule and its own
changelog naturally.

### 2. Contributor focus

A contributor interested in only the Rust core doesn't have to clone a
500MB monorepo. They `git clone whitemagic-rust` (20MB) and get going.
Lowers the barrier to first PR.

### 3. Dependency hygiene

Today `core/whitemagic/` imports from `polyglot/mojo/` via relative
path tricks. In separate repos, every cross-module dependency has to
be an explicit pinned version in `pyproject.toml` or `Cargo.toml`.
This forces a real API contract between modules.

### 4. Issue tracker clarity

One repo's issue tracker mixes "Rust WASM won't build on ARM" with
"timeline page has a typo." Separate repos let each issue tracker
focus on one thing.

### 5. Security blast radius

A secret accidentally committed to `whitemagic-site` doesn't touch the
history of the core library. If the site repo gets compromised, the
core is untouched.

### 6. Package distribution matches reality

`@whitemagic/sdk` ships to npm. `whitemagic` ships to PyPI.
`whitemagic-rust` ships to crates.io. Each package already has its own
registry. Separate repos match the distribution shape.

---

## Arguments against exploding

### 1. Cross-module refactors become painful

Right now: one PR renames a function in Python and updates its Rust
binding and updates the TypeScript SDK type. In multirepo: three PRs,
three reviews, three merges, and the TypeScript SDK is broken until
the Rust crate publishes a new version. Google's entire engineering
culture is built around avoiding this pain; that's why they use a
monorepo for 95% of their code.

### 2. Version drift hell

In a monorepo, every commit is internally consistent. In multirepo,
`whitemagic-sdk-ts@0.3.0` might require `whitemagic-rust@0.7.0` which
requires `whitemagic-core@0.12.0`. When a user installs the wrong
combination, everything breaks in confusing ways. The "which versions
work together" matrix grows quadratically with the number of repos.

### 3. CI multiplication

A monorepo has one CI config covering everything. Twelve repos have
twelve CI configs, twelve secrets managers, twelve dependabot queues.
For a solo or small-team project, this is just more maintenance, not
more speed.

### 4. Search is worse

`grep -r "Harmony Vector" WHITEMAGIC/` finds everything. Across twelve
repos, you have to check out all twelve and search each, or use
GitHub's cross-repo search which is slower and less reliable.

### 5. Onboarding a new contributor is *harder*, not easier

Counter-intuitive, but: a new contributor trying to understand
WhiteMagic's architecture benefits from seeing all modules side-by-side
in a single tree. "How does Python call into Rust?" is answerable by
reading two files in the same repo. In multirepo, they have to
discover `whitemagic-rust` exists, check it out separately, and
mentally stitch the pieces together.

### 6. The value proposition is unclear for a solo maintainer

Most of the benefits of multirepo assume multiple teams working in
parallel with conflicting concerns. WhiteMagic today has one
maintainer. The overhead of twelve CI configs, twelve version bumps
per cross-cutting change, and twelve issue trackers is a *tax* with no
matching benefit until a second or third contributor arrives who wants
to focus on one module.

---

## What the industry does

- **Google, Meta, Microsoft**: monorepo (Google's is literally called "the monorepo")
- **Rust (rustc + cargo + std)**: monorepo
- **Next.js + Vercel platform**: monorepo (turborepo)
- **React + React DOM + React Native + the tooling**: monorepo
- **npm**: monorepo (lerna originally, nx now)
- **Linux kernel**: monorepo (one of the oldest and largest)

- **Kubernetes**: split into multiple repos around 2017 and has been
  fighting version-drift issues ever since. Frequently cited as a
  cautionary tale for over-eager multirepo.
- **AWS SDKs**: multirepo per language — but each language SDK is
  itself a monorepo of services. Hybrid.

**Pattern**: successful organizations use monorepos for tightly coupled
components and multirepos *only when there's a clear organizational
separation* (separate teams, separate products, separate release
cadences that genuinely don't coordinate).

---

## What I'd actually recommend

**Stay monorepo.** With the following qualifications:

### 1. Use `apps/` + `core/` + `polyglot/` + `sdk/` directory boundaries as the modularity unit.

Each subdirectory has its own:
- build config (`Cargo.toml`, `pyproject.toml`, `package.json`, etc.)
- tests
- `README.md`
- changelog (optional; a single top-level CHANGELOG also works)

This gives 80% of the modularity benefit with none of the version-drift cost.

### 2. Extract into separate repos only when one of these is true:

- **Contributor separation**: a second person is actively working on
  one module and wants their own PR flow. Not hypothetical — actually
  happening.
- **Release cadence genuinely diverges**: e.g., the SDK is shipping
  daily hotfixes while core ships monthly. Real divergence, not
  theoretical.
- **Distribution friction**: the registry (npm, PyPI, crates.io)
  actively wants a separate repo. Rare today.
- **Legal separation**: one module needs a different license or
  contributor agreement.

### 3. Already-extracted items

- `whitemagic-site` lives in its own private repo for Vercel deploy
  reasons (legitimate distribution friction — Vercel prefers a clean
  repo root).
- The subtree merge keeps `apps/site/` in the monorepo synced with the
  standalone repo on each release. Best of both.

### 4. Things I'd consider extracting *eventually*

- `@whitemagic/sdk` — once it's stable and being consumed by external
  projects, it might make sense as its own repo with its own npm
  release cadence. Not yet.
- The grimoire — if it grows into a public reference that non-engineers
  contribute to, a separate repo with different tooling (e.g., a static
  site generator) might make sense.

### 5. Things I'd keep in the monorepo forever

- `core/` and `polyglot/*/` — too tightly coupled. Cross-language
  bindings need atomic commits.
- `apps/*` — each app is small; the monorepo is the right home.
- `docs/` — documentation follows the code.

---

## Concrete migration path (if you ever want to explode)

Should the calculus change (e.g., three people join and want separate
flows), the phased exit is:

1. **Extract `whitemagic-sdk-ts` first.** Already has clean boundaries.
   Lowest-risk test of multirepo workflow.
2. **Extract `whitemagic-rust` second.** WASM + crates.io release
   already want a focused home.
3. **Watch how painful the cross-repo refactors get.** If the answer
   is "not that painful," proceed to extract more. If "too painful,"
   stop.
4. **Never extract more than three repos without proof of value.**
   Twelve-repo plans usually collapse under their own weight.

Use `git subtree split` to extract while preserving history. Never
just copy files — that loses blame information that matters.

---

## Decision

For now: **stay monorepo**. Revisit when:

- A second contributor starts PR'ing regularly (→ consider extraction)
- A major version bump happens for one module without the others (→ already diverging)
- CI times in the monorepo exceed 15 minutes (→ consider splitting)

None of these triggers are active today.

---

## Appendix — the `whitemagic-site` exception

The site is already in its own private repo, and that's *not* a
contradiction of the "stay monorepo" recommendation:

- It's a deploy artifact, not a library. Deploy artifacts benefit from
  standalone repos.
- Vercel's UX assumes one repo = one site.
- The subtree merge into `apps/site/` keeps it participatable in the
  monorepo when convenient.

If the PWA (`apps/pwa/`, once built) also gets a Vercel deploy, the
same pattern applies: develop in the monorepo, subtree-push to a
standalone private repo for deploy. Two repos. Still not "exploded."
