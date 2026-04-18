# apps/

User-facing applications built on top of the WhiteMagic platform.

## Layout

| Path | What it is | Status |
|---|---|---|
| `apps/site/` | WhiteMagic Labs consultancy site (whitemagic.dev) — Next.js 15 + Tailwind + MDX, deployed on Vercel. | Active, shipping April 2026. |

## Relationship to the core platform

`core/` is the library. `apps/` is what people actually touch. Everything
in `apps/` consumes either the public `whitemagic` Python package, the
polyglot bridges in `polyglot/`, or the documented MCP interface — never
the private internals of `core/`.

This keeps the consultancy site (and any future installable browser app,
agent demo, or SDK playground) honest: if an app can't be built against
the published surface, the surface isn't done yet.

## Development

Each `apps/<name>/` is self-contained with its own `package.json`,
`pyproject.toml`, or equivalent. Develop inside the subdirectory;
nothing in `apps/` is expected to share node_modules or virtualenvs
with siblings.

## Deployment

`apps/site/` deploys from this monorepo to Vercel. The Vercel project
is configured with **Root Directory: `apps/site`** and the Next.js
framework preset. DNS: `whitemagic.dev` → Vercel.

## History

`apps/site/` was developed briefly as a standalone repo at
`~/Desktop/whitemagic-site/` from April 17–18, 2026 to prove the
concept fast, then folded into this monorepo via `git subtree add`
once the shape was clear. Its commit history is preserved in
the squashed merge commit.
