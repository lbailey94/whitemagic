# Web Research Backends — Reference (v2 heritage → 2026 $0 stack)

**Prepared:** 2026-08-30 (early AM, session `ddbebecf`)
**Status:** Reference doc for the v7.x/v8 web-surface revival. Companion to
`MEMORY_TYPOLOGY_V8.md` §10. Sources: C1 heritage survey (og_whitemagic v2
core, `gardens/browser/web_research.py` + `tools/handlers/web_research.py`),
live tools.list on 18790, C3 backend research (2026-08).

## 1. What exists today (live binary, verified on the fleet)

`web.fetch` (clean text) · `web.deep_fetch` (200K chars) · `web.search`
(Bing HTML) · `web.search_and_read` · `research.topic` (search → fetch top N
→ synthesize) · `research.repo` (README deep-read) · `research.rabbit_hole`
(recursive: search topic → each term → fetch top). Three-tier architecture
(fetch / search / orchestrate) survived every version — **not** exposed in
the curated opencode-facing profile, so harness users fall back to opencode's
own webfetch/websearch (Exa-bundled).

**Regressions vs v2:** search is Bing-HTML-only (v2: DuckDuckGo scrape +
optional Brave API fallback + category/batch variants); the result cache
(v2 `web_cache_list/clear`) was lost; no `parallel_reason` / batch search.

## 2. v2 heritage fleet (the sophistication to recombine)

15 handlers: web_fetch, web_search, web_search_category, web_search_batch,
web_fetch_enhanced, deep_fetch, research_url, research_topic,
rabbit_hole_research, parallel_reason, web_cache_list, web_cache_clear,
browser_session_status (+ Gan Ying `WEB_FETCH` resonance events on the bus).
Dependencies: httpx + html2text + bs4 (graceful optional). Zero API keys by
design — v2 docstrings state it was built to *replace* external search MCP
tools like Exa. A v26-era Chromium/ARIA browser integration was planned
(`staging/v26-heritage/aria/20260516_i70_CHROMIUM_ARIA_INTEGRATION_PLAN_*.md`)
but never shipped; keep headless-first, add an optional Playwright lane only.

## 3. The 2026 $0 backend landscape (burst-scale: 1,000s of queries/fetches)

| Backend | Hosting | True cost at burst scale | Notes |
|---|---|---|---|
| **SearXNG (private)** | self-host | **$0** | JSON off by default; limiter cap 4/hr/IP — bypass via `pass_ip`/loopback. Engines: duckduckgo + brave + mojeek + bing stable at thousands/day with 2–3s pacing. **Never enable Google/Startpage** (CAPTCHA suspends the instance 1d–15d). Monitor `/stats/errors`. |
| 4get | self-host | $0 | Proxy rotation built in; fewer engines |
| Whoogle | — | **dead** (archived Jul 2026) | Google killed no-JS SERPs |
| Crawl4AI v0.9.2 | pip in-process | $0 + RAM (200–500MB when rendering) | ~11–19 pages/s; built-in cache; use for JS-heavy pages only |
| Firecrawl OSS | self-host | heavy (Postgres+Redis+RabbitMQ) | laptop-hostile, skip |
| Jina Reader | hosted | 500 RPM free; 10M tokens one-time (~2K pages) | fallback lane only |
| Exa | hosted | $20 signup + $10/mo ≈ 1–2K searches/mo | semantic queries only, never bulk |
| Tavily | hosted | 1K credits/mo free (~3% of need) | Nebius acquisition Feb 2026 |
| Brave API | hosted | free 2K/mo tier **retired Feb 2026** | card wall — the old cost trap, confirmed |
| Keyless verticals | hosted | $0, effectively unlimited | HN Algolia 10K/hr · arXiv 1/3s · Crossref 3/s polite · OpenAlex ~100K credits/day · Wikipedia/Wikidata · Semantic Scholar (free key, 1 RPS) · GitHub search |
| Parallel MCP | hosted | free, anonymous caps | emergency no-signup overflow |

## 4. The burst-discipline layer (what actually makes $0 work)

1. **Hash-keyed fetch + search cache** with TTLs by content volatility
   (restore v2's cache; most "fetches" become hits). URL-dedup **before**
   any fetch.
2. Query-result cache ≥5 min; concurrency ≤2–4; exponential backoff on 429;
   robots.txt respected; a search failure is an empty result, never a
   retry-storm against a blocked engine.
3. Pacing (2–3s inter-query) inside rabbit_hole loops — the recursion is the
   CAPTCHA-trap; pace at the orchestrator, not per-fetch.

## 5. Target architecture (v8, PRAT discipline)

Surface as **three meta-tools** with sub-routing (the 28-Gana compression
law — PRAT, "Polymorphic Resonant Adaptive Tools", verified in
`prat_router.py`):

- `web` — fetch / deep_fetch / search (SearXNG primary, keyless verticals
  routed by domain, Jina fallback lane)
- `research` — topic / repo / rabbit_hole (paced, cached, memory-persisted)
- `cite` — provenance enforcement: every fact carries url + quote; extractions
  persist as `knowledge`-class memories, fetch outcomes as `telemetry`

Config: `WM_WEB_SEARXNG_URL` (loopback), `WM_WEB_CACHE_DIR` +
`WM_WEB_CACHE_TTL`, `WM_WEB_VERTICALS` (domain→API routing table), optional
`WM_WEB_RENDER` (Crawl4AI lane for JS pages).

## 6. Sequencing

- **v7.x quick wins** (before v8): re-expose `web.*`/`research.*` in the
  curated profile (or document the full-profile flag); restore the fetch
  cache; add DuckDuckGo + Mojeek engines alongside Bing.
- **v8**: SearXNG primary backend + vertical routing + `cite` provenance
  tool + telemetry-classed fetch logs (feeds the typology, not the noise).

## 7. References

C3 wave report (session `ddbebecf`, 2026-08-30): apiserpent.com SearXNG
self-host tests (Jul 2026); ssdnodes SearXNG rate-limit guide (Aug 2026);
conselara engine-selection notes (May 2026); parallel.ai free-API survey
(Aug 2026); jina.ai/reader docs; github.com/benbusby/whoogle-search archive
notice; docs.crawl4ai.com self-hosting; docs.firecrawl.dev self-host;
hn.algolia.com/api; benchlm.ai pricing stats. Heritage: og_whitemagic v2
core (`web_research.py` ~1100 ln, handler fleet ~390+ ln), PRAT router.
