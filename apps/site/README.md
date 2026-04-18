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

Phase 0 scaffold — minimal landing page. Real copy, service pages, and
case studies land in Phase 1. See `../whitemagic-frontend/PHASE_0_PLAN.md`
for the full plan.
