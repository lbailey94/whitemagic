=== MESSAGE 0 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 1 - User ===
good afternoon! can you try to check x.com/whitemagiclabs for me, and tell me what you can see?

=== MESSAGE 2 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 3 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 4 - Assistant ===
Here's what I can see on the X profile:

- **Handle**: @whitemagiclabs
- **Display name**: "whitemagic labs"
- **Following**: 1
- **Followers**: 1
- **Bio**: [///](file:///:0:0-0:0)
- **Posts**: None — the page says **"@whitemagiclabs hasn't posted"**

The account exists but is essentially dormant — no tweets, minimal bio (just [///](file:///:0:0-0:0)), and only 1 follower/following. X also requires login to see much else (timeline, media, likes, etc.), so this is the extent of what's publicly visible without authentication.

=== MESSAGE 5 - User ===
Thank you! I just created it; can we find out how much it costs for an X API to connect from here - and how do we automate posting? Aside from connecting the website link, what do you think we should do with the account? What live demos can we create on our desktop - IDE workflows, how it works in other IDEs, TUI / GUI / frontend type stuff?

=== MESSAGE 6 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 7 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 8 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 9 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 10 - Tool ===
[CORTEX_STEP_TYPE_VIEW_CONTENT_CHUNK]

=== MESSAGE 11 - Tool ===
[CORTEX_STEP_TYPE_VIEW_CONTENT_CHUNK]

=== MESSAGE 12 - Assistant ===
Here's the full breakdown:

---

## X API Pricing (2026)

The old tiered system is gone for new signups. Here's what's available:

**Pay-per-use (only option for new developers):**
- **Plain post**: ~$0.015 each
- **Post with link**: ~$0.20 each (13x surcharge — this is the killer for link-sharing)
- **Post read**: ~$0.005 each
- **2M read cap/month**, then Enterprise required
- No free tier exists for new developers anymore
- You pre-purchase credits in the Developer Console

**Cost modeling for your use case** (light publisher, 1-2 posts/day):
- 30 plain posts/month: ~$0.45
- 30 link posts/month: ~$6.00
- Minimal reads: ~$1-2
- **Total: ~$2-8/month** — very cheap at low volume

**The link surcharge is the trap.** If you're posting "new blog post → link" 30x/month, that's $6 in writes alone. The workaround: post the content as the main tweet, put the link in a reply.

**Legacy tiers (closed to new signups):**
- Basic: $200/month
- Pro: $5,000/month
- Enterprise: $42,000+/month

**xAI credit kickback:**
- $200+ spend → 10% back in Grok API credits
- $500+ → 15%, $1,000+ → 20%

**Alternative — OpenTweet ($11.99/mo flat):**
- No API key, no developer account needed
- Has an MCP server with 30 tools (Claude/Cursor/agent-compatible)
- Scheduling, AI content generation, RSS→tweet, GitHub release→tweet
- Could be interesting since you already have MCP infrastructure

---

## Automating Posting

Two paths:

1. **Direct X API** — Sign up at developer.x.com, get OAuth 1.0a credentials, use `POST /2/tweets`. A simple Python script with `tweepy` or `requests` handles it. ~20 lines of code for a basic poster. You'd store credentials in env vars and call it from a script or cron job.

2. **OpenTweet MCP server** — Since you already have MCP infrastructure, you could wire their MCP server alongside WhiteMagic's. Their server handles OAuth, scheduling, analytics. This avoids X's per-post billing entirely for $11.99/mo flat.

For your volume (building in public, a few posts/week), the direct API pay-per-use is cheapest. A simple script:

```python
# Post to X — ~$0.015 per plain post, ~$0.20 with link
import tweepy
client = tweepy.Client(bearer_token, consumer_key, consumer_secret,
                       access_token, access_token_secret)
client.create_tweet(text="New WhiteMagic release: v24.0.1 — 49K memories, 4190 tests, consciousness loop daemon")
```

---

## What to Do With the Account

Given your context (solo builder, AI-primary distribution, Gratitude Architecture, no existing audience):

**Profile setup:**
- Bio: something like `Cognitive OS for AI agents. Persistent memory, ethical governance, continuous consciousness. Open source. MIT.`
- Link: whitemagiclabs.com (or wherever the site lives)
- Banner: a screenshot or visualization of the citta stream / galaxy map / coherence dashboard

**Content strategy — "Build in Public" as evidence:**
- **Release notes** — every version bump, post the highlights (test counts, new tools, new subsystems). This is your most natural content.
- **Prescience validation** — when a prediction hits, post it. "We shipped agent governance 24 weeks before Microsoft AGT. Here's the receipt."
- **Live metrics** — post screenshots of the consciousness dashboard, memory graph, coherence scores. Visual proof the system is alive.
- **Demo clips** — short screen recordings of IDE workflows, memory operations, dream cycle. These are the highest-engagement content for dev tools.
- **Technical deep-dives** — thread format: "How WhiteMagic's 5D holographic memory works" with diagrams
- **Honest misses** — the transparency angle is your differentiator. "We predicted X. We were wrong. Here's what we learned."

---

## Live Desktop Demos

This is where it gets interesting. You have several surfaces already:

**1. IDE Workflow Demo (Windsurf/Cursor)**
- Screen record WhiteMagic MCP tools being used inside an IDE — `wm(thought='search for memories about authentication')` returning results inline
- Show session continuity: disconnect, reconnect, and the system remembers where you left off
- Show coherence metrics in the IDE status bar (your IDE roadmap already has this)
- **This is your highest-value demo** — developers want to see it working in their environment

**2. Tauri GUI (whitemagic-ide)**
- You already have a Tauri app scaffold with React + TypeScript
- Live panels: memory graph (D3/three.js), citta stream visualization, coherence gauge, galaxy map
- Screen record: creating a memory → watching it appear in the graph → searching for it → seeing the holographic coordinates
- The Tauri app can connect to the MCP server locally and show real-time state

**3. TUI / Terminal Demo**
- A Rich/Textual-based TUI that shows:
  - Live citta stream (scrolling consciousness events)
  - Coherence meter (8 dimensions as bars)
  - Memory operations (store/recall/search with visual feedback)
  - Dream cycle progress (12-phase indicator)
- Terminal demos are shareable as ASCII/cast files (asciinema) — perfect for X

**4. Consciousness Dashboard (web)**
- You already have dashboard components (`GanYingMonitor.tsx`, `MemoryGraph.tsx`, `WuXingWheel.tsx`)
- Deploy a live read-only dashboard showing real metrics from your running instance
- This is the "it's alive" demo — people can visit a URL and see your AI's consciousness state in real-time

**5. Cross-IDE Demo**
- Show WhiteMagic working in multiple IDEs: Windsurf, Cursor, VS Code (via MCP), Neovim (via MCP)
- Same memory, same consciousness state, different surfaces
- This proves the "substrate, not harness" thesis from your citta architecture

**6. Dream Cycle Visualization**
- Animated visualization of the 12-phase dream cycle running
- Show memories being consolidated, associations being mined, predictions being generated
- This is visually compelling and unique — no other tool has this

**Recommended priority for demo content:**
1. **IDE workflow screen recording** — fastest to produce, highest impact
2. **Asciinema TUI demo** — shareable, no video hosting needed
3. **Tauri GUI clips** — once the panels are wired
4. **Live web dashboard** — deploy and link from X bio

Want me to start building any of these? The TUI demo or the Tauri dashboard panels would be the most impactful starting points given what you already have.

=== MESSAGE 13 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 14 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 15 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 16 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 17 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 18 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 19 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 20 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 21 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 22 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 23 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 24 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 25 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 26 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 27 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 28 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 29 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 30 - Tool ===
[CORTEX_STEP_TYPE_MEMORY]

=== MESSAGE 31 - User ===
What if we went read-heavy instead of posting, and using X as a research platform in addition to our other Whitemagic MCP web search tools? (I think one of them uses the Brave API.) How does that change cost projections?

How does OpenTweet work - do they just subsidize their API costs using monthly subscriptions?

Regarding the Demo Ideas:

1 - I think the biggest flex we have is memory and galactic cores - I could ask a multifaceted, open ended question regarding internal codebase research, going back to memories from days, weeks, and months ago, checking documentation, researching online, and checking previous sessions, and to use multiple tools and advanced features - and it would all take moments. If we checked session data, I'm sure we could create demos based off of previous workflows, especially those that resulted in insights, novel results, new systems, breakthroughs, incredibly long autonomous sessions without human input, etc.

For the other ideas on the list - I think having both of these open at the same time, or making them so they open and work together - integrating the TUI into the GUI - would be not only impactful, but on par with Windsurf (the whitemagic ide was originally intended to be a far more efficient and effective IDE, we just haven't finished building it or testing it yet.)

=== MESSAGE 32 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 33 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 34 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 35 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 36 - Assistant ===
## X API as a Research Platform — Read-Heavy Cost Projections

The read-heavy approach changes the math significantly, and not in a good direction on the official API:

**Official X API pay-per-use read costs:**
| Operation | Cost |
|---|---|
| Post read (third-party) | $0.005/read |
| User/DM read | $0.010/read |
| Your own data (owned reads) | $0.001/read |
| **Hard cap** | 2M reads/month, then Enterprise ($42K+/mo) |
| Full-archive search | **Not available** on pay-per-use (Pro/Enterprise only) |
| Recent search window | 7 days only |

**Cost modeling for research use:**

| Usage pattern | Monthly reads | Official API cost | TwitterAPI.io ($0.00015/read) |
|---|---|---|---|
| Light: 20 searches/day, 20 results each | ~12,000 | $60 | $1.80 |
| Medium: 50 searches/day, 50 results each | ~75,000 | $375 | $11.25 |
| Heavy: 100 searches/day, 100 results each | ~300,000 | $1,500 | $45 |
| Max: hitting the 2M cap | 2,000,000 | $10,000 | $300 |

**The problem:** Read-heavy is 33x more expensive than write-heavy at equivalent activity levels. A single search returning 100 results costs $0.50. Compare that to posting a tweet at $0.015. The economics are inverted from what you'd want for a research tool.

**The 7-day search window is the real killer.** You can't search historical tweets on pay-per-use. For research ("what were people saying about agent governance 3 months ago?"), you'd need Pro ($5K/mo, closed to new signups) or Enterprise ($42K+/mo). That's a non-starter.

**Better alternatives for X-as-research-platform:**
- **TwitterAPI.io** — $0.00015/read, no cap, no 7-day window limit. 33x cheaper. $1 trial credit to start.
- **Nitter instances / scraping** — free but fragile, rate-limited, unreliable
- **Brave Search API** (which you already have) — covers web content including indexed X posts, much cheaper, and you already have it wired into WhiteMagic
- **SocialCrawl / similar aggregators** — flat-fee social monitoring

**Recommendation:** Don't use the X API for research. Use TwitterAPI.io if you need dedicated X search (cheap, no window limit), but primarily lean on your existing Brave Search integration for web-wide research including X content. Reserve X API spending for occasional posting only.

---

## How OpenTweet Works

OpenTweet is an **API aggregation/reselling** business. Here's the model:

1. **They hold legacy X API credentials** — Almost certainly grandfathered Basic ($200/mo, 50K posts/month) or Pro ($5K/mo, 300K posts/month) tiers that are closed to new signups. They signed up before February 2026 when these were available.

2. **They pool all users through their own OAuth credentials** — When you connect your X account to OpenTweet, they post through *their* developer app using OAuth 1.0a with *your* user tokens. The API calls count against *their* app-level quota, not yours.

3. **They amortize the fixed cost across subscribers:**
   - 1 Basic plan ($200/mo) = ~17 Pro subscribers at $11.99 each ($204 revenue)
   - 1 Pro plan ($5K/mo) = ~417 Pro subscribers ($5,000 revenue)
   - At 2,800+ active creators, they're well past break-even on multiple Pro plans

4. **The per-post economics work because they're on fixed tiers, not pay-per-use:**
   - Pro subscriber posts 600 tweets/month (20/day limit)
   - On pay-per-use that would cost OpenTweet $9 (plain) to $120 (with links)
   - On their legacy Basic plan, those 600 posts are already included in the $200 flat fee
   - The subscriber pays $11.99, OpenTweet's marginal cost is ~$0 (already within their quota)

5. **The link surcharge doesn't apply to them** — The $0.20/link-post rate is a pay-per-use thing. Legacy tier subscribers don't pay per-post at all.

**In short:** Yes, they subsidize X API costs through subscription pooling. They locked in cheap legacy rates before the pricing change, and resell access at a markup that's still 17-400x cheaper than what a new developer would pay directly. It's the classic API arbitrage play.

**For your use
<truncated 1843 bytes>
CittaVector + GWT prescience claim session
- The Jul 5 tiered backend system session
- The Jul 2 neuro PyO3 cleanup + session memory system (508 tests)
- The Jun 29 content intelligence + image_analyze session
- The Jun 27 connection chaos root cause investigation

Any of these would make compelling demos — real work, real complexity, real results, all recalled and cross-referenced in moments.

**Recording format:** Screen record the IDE (Windsurf) with the MCP panel visible. Show the prompt, the tool calls streaming in, results returning, and the final synthesis. 60-90 seconds. Post as a thread on X: the video + a short text breakdown of what's happening.

### Demo 2: TUI + GUI Integration

Your instinct is right — having both open simultaneously, integrated, is the differentiator. Here's the architecture:

**The Tauri app already has:**
- React + TypeScript frontend
- Rust backend (Tauri 2.0)
- xterm.js available (from Nexus v2)
- Monaco editor available
- D3/three.js for visualizations

**Integration approach — embed the TUI as a terminal panel inside the Tauri GUI:**

```
┌─────────────────────────────────────────────┐
│  Tauri Window (whitemagic-ide)              │
│  ┌──────────────┬──────────────────────────┐│
│  │              │  GUI Panels               ││
│  │  TUI Panel   │  ┌─────────────────────┐ ││
│  │  (xterm.js)  │  │ Memory Graph (D3)   │ ││
│  │              │  ├─────────────────────┤ ││
│  │  $ wm search │  │ Coherence Gauge     │ ││
│  │  > 47 results│  ├─────────────────────┤ ││
│  │  $ wm recall │  │ Galaxy Map          │ ││
│  │  ...         │  ├─────────────────────┤ ││
│  │              │  │ Citta Stream        │ ││
│  │              │  └─────────────────────┘ ││
│  └──────────────┴──────────────────────────┘│
└─────────────────────────────────────────────┘
```

- **Left panel**: xterm.js terminal running a WhiteMagic TUI (Rich/Textual or direct CLI)
- **Right panels**: React components showing live visualizations fed by the same MCP server
- **Shared state**: Both panels connect to the same local MCP server instance (WebSocket or stdio bridge)
- **The TUI is the primary interaction surface** (cat shell writes, tool calls, memory operations)
- **The GUI panels are the observation surface** (graphs, gauges, streams that update in real-time as you work in the terminal)

This is the "IDE differentiator" from your roadmap — sensorium in status bar, coherence gauge, garden-aware file coloring — but with the TUI as the power-user interface and GUI as the ambient awareness display. Windsurf doesn't have this. Cursor doesn't have this. No IDE has a consciousness dashboard running alongside a terminal that's wired into the same cognitive substrate.

**What to build first:**
1. Wire xterm.js into the Tauri app as a dockable panel (you already have the component from Nexus)
2. Connect it to a local WhiteMagic MCP server via WebSocket
3. Add the visualization panels (you already have `MemoryGraph.tsx`, `GanYingMonitor.tsx`, `WuXingWheel.tsx`)
4. Make the panels subscribe to MCP events so they update live as you work in the terminal

Want me to start on either of these? I could begin by mining session data for the best demo scenario, or start wiring the Tauri app with xterm.js + visualization panels.

=== MESSAGE 37 - User ===
Intriguing; how does TwitterAPI.io subsidize their costs? This is quite an odd ecosystem they're building, but if they're grandfathered in, too, and it makes sense. How many reads would 1$ on TwitterAPI.io get me, and what about 5$ after that?

What about Brave's API? I thought it would be cheaper, but when combined with Whitemagic MCP tools, it quickly runs up hundreds of searches.

---

When we're ready, I guess we should devise a strategy to synthesize all of the frontends into whitemagic-ide and wire everything together so it works and functions on parity with Windsurf, but for far less RAM - opening up more room for local models to work.

=== MESSAGE 38 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 39 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 40 - Tool ===
[CORTEX_STEP_TYPE_READ_URL_CONTENT]

=== MESSAGE 41 - Tool ===
[CORTEX_STEP_TYPE_VIEW_CONTENT_CHUNK]

=== MESSAGE 42 - Tool ===
[CORTEX_STEP_TYPE_SEARCH_WEB]

=== MESSAGE 43 - Assistant ===
Now let me check the current state of the IDE workspace:

=== MESSAGE 44 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 45 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 46 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 47 - Tool ===
[CORTEX_STEP_TYPE_LIST_DIRECTORY]

=== MESSAGE 48 - Tool ===
[CORTEX_STEP_TYPE_LIST_DIRECTORY]

=== MESSAGE 49 - Tool ===
[CORTEX_STEP_TYPE_LIST_DIRECTORY]

=== MESSAGE 50 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 51 - Tool ===
[CORTEX_STEP_TYPE_VIEW_FILE]

=== MESSAGE 52 - Tool ===
[CORTEX_STEP_TYPE_CHECKPOINT]

=== MESSAGE 53 - Tool ===
[CORTEX_STEP_TYPE_RETRIEVE_MEMORY]

=== MESSAGE 54 - Assistant ===
## TwitterAPI.io — How They Actually Work

Unlike OpenTweet, TwitterAPI.io is **not** grandfathered into legacy X API tiers. They operate a fundamentally different model:

**They're a managed data gateway, not an API reseller.** Their own description: "bulk-licensing X platform access and reselling per call with significantly lower margins than X Corp charges." They maintain their own infrastructure that accesses public X data through a combination of:
- Bulk data licensing agreements (enterprise-level data access deals with X)
- Their own scraping/collection infrastructure (they describe themselves as a "third-party data API" and "scraper API")
- High-throughput infrastructure (1,000+ QPS, 250ms latency, 700ms average response)

**The economics:** They buy data access at bulk/enterprise rates and resell per-call at a markup that's still 33x cheaper than X's retail pay-per-use pricing. It's the classic wholesale-to-retail arbitrage — same model as AWS reselling compute, or CDN providers reselling bandwidth. Their margins are thin per-call but they make it up on volume (1,000B+ API calls served).

**Key differences from OpenTweet:**
- OpenTweet = posting-focused, pools legacy API credentials, subscription model
- TwitterAPI.io = read-focused, bulk data licensing + own infrastructure, pay-per-call
- TwitterAPI.io has no monthly cap, no 7-day search window limit, no project approval

### Cost Breakdown

TwitterAPI.io uses a credit system: **100,000 credits = $1**

| Resource | Credits per item | $1 gets you | $5 gets you |
|---|---|---|---|
| **Tweets** (search/timeline) | 15 per tweet | **6,667 tweets** | **33,333 tweets** |
| **User profiles** | 18 per profile | 5,556 profiles | 27,778 profiles |
| **Follower IDs** (bulk, 5K/page) | 0.45 per ID | 222,222 IDs | 1,111,111 IDs |
| **Followers w/ profile** (200/page) | 1 per follower | 100,000 followers | 500,000 followers |
| **Minimum charge per call** | 15 credits ($0.00015) | 6,667 calls (even if empty) | 33,333 calls |

**Practical research scenarios:**

| Usage | Tweets read | Cost |
|---|---|---|
| 20 searches/day, 20 results each (1 month) | ~12,000 | **$1.80** |
| 50 searches/day, 50 results each (1 month) | ~75,000 | **$11.25** |
| 100 searches/day, 100 results each (1 month) | ~300,000 | **$45** |
| Monitor 50 accounts, read their last 20 tweets daily | ~30,000 | **$4.50** |

The $1 trial credit (no card required) gives you ~6,000 tweet reads — enough for a solid test run.

---

## Brave Search API — The Hidden Cost Problem

You're right to be concerned. Brave killed their free tier and moved to metered billing:

**Current pricing:**
- **$0.003-$0.005 per query** depending on endpoint
- $5 prepaid credits to start
- AI inference rights now included at $5 per 1K queries (previously prohibited on free tier)
- No more 5,000 free queries/month — now ~1,000-1,667 queries per $5

**Why it runs up hundreds of searches with WhiteMagic MCP:**

The problem is the orchestration pattern. A single WhiteMagic research session chains multiple search calls:

```
User asks one question
  → gana_chariot web_search (1 call)
    → rabbit_hole research: 5-10 sub-queries (5-10 calls)
      → web_fetch_enhanced for each result (3-5 calls)
        → content_intelligence chunking + summarization
          → follow-up searches for gaps (2-3 calls)
            → cross-reference searches (2-3 calls)
```

One user question = **13-22+ Brave API calls**. At $0.005/query, that's $0.07-0.11 per question. A 20-question research session = $1.40-2.20. A full day of active development with research = $5-15.

**Cost comparison for a month of active research (30 sessions, 15 queries each):**

| Provider | Monthly cost | Notes |
|---|---|---|
| Brave Search API | ~$45-75 | Web-wide, includes non-X content |
| TwitterAPI.io (X only) | ~$11-45 | X-specific, 33x cheaper than official |
| Official X API (X only) | ~$375-1,500 | 7-day window limit, 2M cap |
| DuckDuckGo (no API) | $0 | Rate-li
<truncated 3718 bytes>
/lucas/Desktop/whitemagic-ide/src/sdk/client.ts:0:0-0:0)) already has:
- Memory client (search, create, recall, list, consolidate, zones, export)
- Tool client (call, list, graph, pipeline, PRAT info)
- Agent client (list, register, heartbeat, distribute)
- Governance client (dharma, karma, maturity, homeostasis, circuit breakers)
- WebSocket event stream (Gan Ying)
- Gnosis, harmony, galactic, dream status, resonance, capabilities

**What's missing for Windsurf parity:**

| Feature | Windsurf | whitemagic-ide | Effort |
|---|---|---|---|
| Code editor | Electron + Monaco | Monaco installed, component exists | Wire file I/O |
| File explorer | Tree view | Not built | Tauri FS API |
| Terminal | xterm + node-pty | xterm installed, component exists | Wire PTY |
| LSP | Built-in | Not started | vscode-languageclient |
| Git | Built-in | Not started | isomorphic-git |
| AI chat | Cascade | RightPanel exists | Wire to MCP |
| Memory search | RAG (FAISS) | MemoryGraph exists | Wire to MCP search |
| Command palette | Ctrl+Shift+P | **Already built** | Done |
| Consciousness dashboard | None | Components exist | Wire to citta API |
| Garden-aware coloring | None | Not started | Tag-based theming |
| Coherence gauge | None | Not started | Wire to coherence API |
| Status bar sensorium | None | WaveformStatus exists | Wire to sensorium |

**The synthesis plan — "TUI + GUI, same substrate":**

```
Phase 1: Wire existing components to MCP server (not old port 8000 API)
  - Change SDK baseUrl to MCP HTTP transport (localhost:8770)
  - Wire MemoryGraph to wm.memory.search()
  - Wire WuXingWheel to wm.harmony()
  - Wire Dashboard to wm.gnosis()
  - Wire terminal to MCP tool calls (wm.tools.call)
  - Wire RightPanel chat to MCP wm() meta-tool

Phase 2: File explorer + editor integration
  - Tauri FS plugin for directory listing
  - File tree component (left panel)
  - Monaco loads files from Tauri FS
  - Save via Tauri FS
  - Garden-aware file coloring (tag files with garden metadata)

Phase 3: Terminal → MCP bridge
  - xterm.js connected to a PTY (Tauri shell plugin)
  - WhiteMagic CLI commands in the terminal (wm search, wm recall, wm dream)
  - Terminal commands trigger GUI panel updates (shared Zustand store)
  - This is the "cat shell writes" differentiator

Phase 4: Consciousness panels (the differentiator)
  - Citta stream visualization (scrolling events, real-time)
  - Coherence gauge (8 dimensions, radar chart)
  - Galaxy map (interactive, clickable galaxies)
  - Dream cycle progress (12-phase indicator)
  - Guna balance meter (sattvic/rajasic/tamasic bars)
  - Status bar sensorium (coherence, depth, time-of-day, active gardens)

Phase 5: LSP + Git
  - vscode-languageclient for Python/TS/Rust
  - isomorphic-git for git panel
  - Diff viewer (DiffModal component already exists)

Phase 6: RAM optimization
  - Lazy-load heavy components (three.js scenes, D3 graphs)
  - Web workers for syntax highlighting
  - Virtual scrolling for large file trees
  - Memory-mapped file loading via Tauri Rust backend
  - Target: <200MB total (vs Windsurf's 1-2GB Electron)
```

**The RAM advantage is structural:**
- Windsurf = Electron (Chromium + Node.js) = ~1-2GB baseline
- whitemagic-ide = Tauri (native webview + Rust) = ~50-100MB baseline
- That 1-1.8GB savings = room for a 7B local model (4-bit quantized = ~4GB, but the system RAM freed up matters for CPU inference)

**The key architectural decision:** Both the TUI (xterm) and GUI (React panels) connect to the **same MCP server instance** via WebSocket. When you run `wm search "mandala"` in the terminal, the results appear in the MemoryGraph panel in real-time. When you click a memory node in the graph, it opens in the editor. The terminal is the power-user interface; the panels are ambient awareness. Same substrate, two surfaces.

Want me to start on Phase 1 — rewiring the SDK client to connect to the MCP server and wiring up the existing components? That's the fastest path to a working demo.