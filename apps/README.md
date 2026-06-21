# apps/

User-facing applications built on top of the WhiteMagic platform.

## Layout

| Path | What it is | Status |
|---|---|---|
| `apps/site/` | Placeholder — the actual website was extracted to a private sibling repo in May 2026. See below. | Inactive (stub) |

## Website Location

The WhiteMagic website (`whitemagic.dev`) lives in a **separate private repository**
at `~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/` (Next.js 15 + React 19 + Tailwind
+ Three.js + ONNX + WASM + PWA, deployed via Vercel Hobby).

It was developed in-repo, then extracted to its own repo in May 2026 for independent
deployment cadence. The `apps/site/` directory in this repo is a stub containing only
`public/api/manifest.json`.

The desktop app suite lives at `whitemagic-app/` (Tauri 2 + React: hub, nexus, shell, sdk).

## Relationship to the core platform

`core/` is the library. `apps/` is what people actually touch. Everything
in `apps/` consumes either the public `whitemagic` Python package, the
polyglot bridges in `polyglot/`, or the documented MCP interface — never
the private internals of `core/`.

## Development

Each app is self-contained with its own `package.json`, `pyproject.toml`,
or equivalent. Develop inside the app's own repository; nothing in `apps/`
is expected to share node_modules or virtualenvs with siblings.

## Deployment

- **whitemagic.dev** (website): Vercel Hobby, auto-deploys from `main` of
  the private `whitemagic-site-private` repo.
- **lab.whitemagic.dev** (API + dashboard): Hetzner VPS (Caddy + systemd).
  Full walkthrough in `docs/deploy/HETZNER_DEPLOY.md`.

## History

`apps/site/` was developed in-repo from April 17–18, 2026, then extracted
to a private sibling repo in May 2026. The extraction left behind this
stub directory. The actual site source, build, and deployment live at
`~/Desktop/WHITEMAGIC-aux/site/whitemagic-site/`.
