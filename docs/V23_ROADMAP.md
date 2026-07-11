# v23 Roadmap

**Version**: 1.0.0
**Date**: 2026-06-20
**Owner**: Lucas Bailey, WhiteMagic Labs
**Status**: v23.0.0-alpha.1 SHIPPED; v23.0.0-alpha.2-WIP in progress

## Why v23

v22.x built the discovery surface: 151 bridge functions, A2A Agent Card,
librarian chat, A2A agent directory. The substrate was barely touched
(5% rehydrated). v23 is the **substrate-first** era. The principle:
**memory sovereignty is foundational**. The substrate runs on the
user's device (PWA, IndexedDB or WASM SQLite). The site is a door, not
a host. Cross-substrate sync is opt-in P2P, never default.

## Phases (successive, but parallel streams within each)

### Phase A — Galactic rehydration ✅ DONE (alpha.1, 2026-06-20)

Rehydrate the v15.8-era substrate data into the v22-era SQLite store.
- 35,053 rows migrated in 1.7s
- 8 new `whitemagic.core.galactic` functions (read-only)
- 8 bridge functions wired to the site
- 12,636 memories, 21,087 associations, 12,686 embeddings
- 35,060 dharma audits (was 7)
- Substrate level: 5% → 10%

### Phase B — Visualization + write paths (alpha.3 → beta.1)

Port the v15.8-era visualizations to the site. Add memory-write paths
to the bridge. The site becomes a *read/write* substrate mirror.
- Port `MemoryGraph.tsx` (d3 force-directed) from `dashboard-app` to
  `app/memory/page.tsx`
- Port `GanaActivityHeatmap.tsx` (d3) to `app/ganas/page.tsx`
- Port `HolographicView.tsx` (three.js 4D) from `hub` to
  `app/hologram/page.tsx`
- Add `memory_create`, `memory_update`, `memory_delete` to the bridge
- Add `dharma_evaluate_ethics` and other dharma engines (currently 6 in
  Python, 0 in catalog)
- Wire `dharma_check_boundaries` to fire on every memory write
- Substrate level: 10% → 25%

### Phase C — Polyglot restoration (beta.2 → beta.4, ~2-3 weeks)

Restore the 11-language runtime from v17. The substrate's pattern
analysis engines are written in Rust, Zig, Haskell, Elixir, Mojo, Go,
Julia, and TypeScript — the Python bridge is just the orchestrator.
- Restore Zig, Haskell, Elixir, Mojo, Go, Julia, TS runtimes
  (currently only Rust is wired)
- Port the 18 pattern analysis engines (none in current 151-fn catalog)
- Port the v15.8 activation sequence (9-step runner)
- Run on the live substrate; surface patterns; persist dream insights
- Substrate level: 25% → 50%

### Phase D — PWA + Ollama (RC.1 → RC.3, ~1-2 weeks)

The substrate is no longer a dev tool; it's a product. Ship the PWA.
Self-host the librarian on Hetzner. Wire Ollama to the librarian.
- PWA substrate in IndexedDB (or WASM SQLite) — same data model as
  `whitemagic.core.galactic`, different storage backend
- Service worker for offline catalog + librarian
- Hetzner CCX23 (€17/mo) + Ollama 8B + nginx shared-secret proxy
- Wire `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`
- Memory export/import to fork cognitive state
- Per-user dharma consent UI
- Substrate level: 50% → 75%

### Phase E — Self-recursive simulation (final, ~1 week)

The substrate is self-improving on the user's device, with consent.
- Port `i_ching_advisor` (real, not shim) — 119 oracle casts
- Port `depth_gauge` dream layer (compression up to 3.7M:1 was v15.8 peak)
- Port `voice/narratives` self-narration
- Port `homeostasis/health_checks` (coherence 0.6→0.8 was v15.8)
- Wire `guideline.evolve` to run on the substrate's own guidelines
- Run 1 dream insight per day, detect 1 constellation convergence/week
- Substrate level: 75% → 100%

### Phase F — v23.0.0 final release

- Remove WIP mode
- Rewrite marketing copy to match actual product
- Final A2A card posture (data_residency, pwa_installable, sync_model)
- llms-full.txt refreshed
- Catalog-impl consistency check: 151+ → ?
- All tests green (target: 2000+)
- Substrate level: 100%, self-improving

## Parallel streams (anytime)

These are not blocked by phases; they happen in parallel:

- **Substrate work**: new modules in `whitemagic.core/`, more bridge
  functions, more tests
- **Site work**: new visualization routes, A2A card expansions,
  llms-full.txt enrichment
- **Docs work**: chronology updates, AGENTS.md updates, examples,
  runbooks

## Substrate level timeline

| Date | Phase | Level | What's live |
|---|---|---|---|
| 2026-06-20 | A | 10% | Rehydrated v15.8 substrate, read-only |
| ~2026-06-27 | B | 25% | + visualizations, + write paths |
| ~2026-07-15 | C | 50% | + polyglot, + pattern engines |
| ~2026-07-29 | D | 75% | + PWA, + Ollama, + Hetzner |
| ~2026-08-05 | E | 100% | + self-recursive, + dream layer |
| ~2026-08-12 | F | shipped | v23.0.0 final |

## Success criteria for v23.0.0 final

- [ ] Substrate is self-improving on a user's device, with consent
- [ ] PWA installs and runs offline
- [ ] Bridge catalog has 250+ functions (was 151)
- [ ] A2A Agent Card reflects PWA-installable posture
- [ ] llms-full.txt is the canonical everything file (1000+ lines)
- [ ] All tests pass (2000+)
- [ ] Catalog-impl consistency: 250+ / 250+ / 250+
- [ ] No `Path.home()` outside `whitemagic.config.paths`
- [ ] Dharma fires on every memory write
- [ ] Memory sovereignty is the headline, not a footer

## Risks

- **Hetzner cost**: €17/mo is sustainable; €77/mo for 70B models
  needs funding
- **PWA storage limits**: IndexedDB has 50% of disk by spec; WASM
  SQLite is unlimited but requires user permission for File System
  Access API
- **Cross-substrate mesh**: P2P gossip is unproven; defer to v24
- **Vercel Hobby ToS**: any spike in traffic could trigger a review;
  PWA routes are static; only the librarian is dynamic
- **Self-recursive simulation risk**: a self-improving substrate
  could optimize for the wrong objective; dharma guardrails +
  coherence ceiling are the safeguards

## After v23

When v23.0.0 ships, choose the strategic path:

1. **Open-source substrate / community path**: release the PWA,
   grow the community, accept donations, no commercial product
2. **Research lab / grants path**: write the academic paper, apply
   for ARPA-H / NSF / EU Horizon, publish findings
3. **Consulting / private AI deployment path**: deploy WhiteMagic
   on customer infra (Hetzner, on-prem, sovereign cloud)
4. **The 4th option** — local-first PWA + cognitive substrate
   visualization + self-recursive substrate — fused because the
   substrate is local and the visualization is part of the product

The 4th option is the most aligned with the v23 work. Decide after
shipping.
