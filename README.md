# whitemagic.dev

Marketing + services site for WhiteMagic Labs (Lucas).

## Stack

- Next.js 15 (App Router) + React 19
- TypeScript strict
- Tailwind CSS 3
- MDX for long-form writing

## Develop

```bash
npm install
npm run dev            # http://localhost:3000
```

## Build

```bash
npm run build
npm run start
```

## Structure

```
app/                App Router pages
components/         Reusable UI
content/            MDX content (writing, case studies)
lib/                Helpers
public/             Static assets (video, fonts, og images)
```

## Phase

Phase 0–1 complete (scaffold + real pages). Phase L.2 complete
(site-wide tool-using Librarian + public Karma ledger). See
`PHASE_ROADMAP.md` in this directory and `docs/message_board/SESSION_STATE.md`
for current state.

## Deploy

Self-hosted on Hetzner (Next.js `output: 'standalone'` → systemd →
Caddy → Cloudflare). Walkthrough: `docs/deploy/HETZNER_DEPLOY.md`.
Rationale: `docs/architecture/INFRASTRUCTURE_DECISION.md`.
