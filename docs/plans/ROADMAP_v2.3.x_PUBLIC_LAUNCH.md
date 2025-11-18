# v2.3.x Roadmap: Public Launch
**Q1 2026 - Make WhiteMagic Universal**

## Phase 1: Deploy (v2.3.0)
- Railway + Vercel automated deployment
- Security audit (rate limits, API keys, CORS)
- Rust replaces Python hotspots (search, parse, I/O)
- Haskell exposed via Python FFI
- 100% test coverage
- Import optimization (fix 5s timeout)

## Phase 2: Visualize (v2.3.1)
- Memory graph (D3.js force-directed)
- Diff viewer (side-by-side comparison)
- Memory streaming (SSE real-time updates)
- Dashboard enhancement

## Phase 3: Public (v2.3.2)
- Landing page (whitemagic.dev)
- Documentation site (docs.whitemagic.dev)
- Blog + tutorials
- Playground (try.whitemagic.dev)
- GitHub/PyPI/npm polish
- Hacker News launch

## Phase 4: Extend (v2.3.3-2.3.9)
- Plugin system + marketplace
- Mobile apps (React Native)
- Team features (collab, RBAC)
- AI integrations (Claude, GPT, Gemini)
- Enterprise features

## Performance Strategy
**Graceful degradation**: Rust/Haskell primary, Python fallback
- Fast path: Compiled languages
- Fallback: Python if compilation fails
- Best of all worlds
