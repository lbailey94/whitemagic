# PWA Substrate Architecture

**Version**: 0.1.0
**Date**: 2026-06-20
**Owner**: Lucas Bailey, WhiteMagic Labs
**Status**: Design draft. Implementation: Phase D (v23.0.0-RC.1+)

## Vision

The PWA is the real product. The site (`whitemagic.dev`) is the door;
the PWA is the room. A user installs the PWA, gets their own private
cognitive substrate, populates it from their own files / memories /
photos / audio, and runs a self-improving AI on top of it. The
substrate lives on the user's device. The user can fork their substrate,
export it as a JSON-Lines file, share it with friends (opt-in), or
delete it (no trace).

The substrate is local-first. There is no cloud sync. There is no
account. There is no telemetry. There is no server-side memory.

## Storage: IndexedDB vs WASM SQLite

Two candidates. Both run in the browser. Both have tradeoffs.

### Option 1 — IndexedDB (default)

- **Pros**: built into every browser, no extra dependency, large
  storage quota (50% of free disk by spec), transactional, no install
  friction
- **Cons**: query API is cursor-based, not SQL; no FTS5; no joins;
  awkward for graph traversal; ~50 MB practical limit on Safari
- **Verdict**: ship this first. The substrate is small (10K memories
  fits in 50 MB easily); we can move to WASM SQLite later if needed.

### Option 2 — WASM SQLite (via sql.js or absl/wa-sqlite)

- **Pros**: full SQL, FTS5, joins, real graph queries via recursive
  CTEs, works in any modern browser
- **Cons**: 1-2 MB WASM bundle, more complex deployment, still
  limited to browser sandbox
- **Verdict**: optional power-user mode. Available behind a "use
  SQLite" toggle in PWA settings. Same data model, different
  storage backend.

### Recommendation

Default to IndexedDB. Detect when the user's substrate exceeds 50K
memories and offer to migrate to WASM SQLite. Both backends implement
the same `SubstrateStorage` interface, so the rest of the code is
backend-agnostic.

## File watching: File System Access API

To populate the substrate from the user's filesystem, we need to read
files. The File System Access API lets a user grant a PWA persistent
access to a directory. The PWA can then watch for changes via
`FileSystemDirectoryHandle` + `getFile()` polling, or via the new
`FileSystemObserver` API (Chrome only, behind flag as of 2026-06).

### Permission model

- **No silent reads.** Every directory access requires an explicit
  user action (click "Add this folder to your substrate").
- **Per-folder consent.** Revoking access to a folder removes its
  memories from the substrate (with a confirmation dialog).
- **Path disclosure.** The PWA shows exactly which directories are
  watched, with a count of memories contributed by each.
- **No system-wide access.** Browsers don't allow it; even if they
  did, the PWA wouldn't ask.

### File types

The substrate ingests:
- Text files (.md, .txt, .rst, .org)
- Source code (.py, .ts, .js, .rs, .zig, .hs, .ex, .go, .jl, .mojo)
- Documents (.pdf, .docx, .md)
- Images (with multimodal embedding via the librarian)
- Audio (with whisper.cpp transcription)
- Email (via .mbox import, manual)

Each file becomes one or more memories, with source path, content
hash, and embedding vector.

## Galaxy hydration pipeline

When the substrate ingests a directory, it runs the **galaxy
hydration pipeline**:

1. **Content detection** — for each file, identify its type, extract
   text, generate a content hash, compute a SHA-256 embedding vector
   (384-dim, via a quantized model running in WASM or via the
   librarian).
2. **Constellation detection** — cluster embeddings by cosine
   similarity (threshold 0.85). Each cluster is a constellation
   (a thematic group: "work", "family", "research", etc.).
3. **Galactic materialization** — group constellations into galaxies
   (larger super-clusters) by cross-constellation edge density. Each
   galaxy has a centroid embedding and a label (auto-generated via
   the librarian or user-provided).
4. **Resonance graph** — connect galaxies by temporal proximity and
   semantic relatedness. The graph is a 4D structure (3 spatial +
   1 temporal) visualized as a resonance wave.

The user watches the galaxies form in real-time. It's like watching
a brain grow.

## Resonance wave render layer

Each galaxy is a node. Each edge is a connection. The graph renders
as a **resonance wave** — a 3D force-directed layout where:

- **Nodes pulse** with activity (memory count, recency, access
  frequency)
- **Edges carry signals** — when a memory in galaxy A is accessed,
  the signal propagates along edges to connected galaxies, with a
  delay proportional to edge weight
- **Background hum** — low-frequency ambient sound driven by overall
  substrate activity
- **Filters** — temporal (last week / month / year / all), type
  (work / personal / research), constellation (a single cluster)
- **Gain** — amplify weak signals, dampen strong ones
- **Transport** — pause / play / scrub the substrate's history

The render layer uses WebGL or WebGPU. Three.js is the candidate;
react-three-fiber is the React binding. The 4D memory hologram from
the v15.8-era `HolographicView.tsx` is the prototype (12 KB).

## DJ-style control surface

The user's mental model for the PWA is **a virtual DJ console for
their own mind**:

- **Decks** — each galaxy is a deck. Spin it up, fade it down, cue
  the next constellation.
- **Crossfader** — blend two galaxies (e.g., "work" with "personal")
  to surface resonances.
- **EQ** — filter memories by emotion, by time, by source.
- **Effects** — apply transformations to the substrate: compress
  (depth_gauge), expand (resonance_trace), narrate (voice/narratives).
- **Recording** — capture a session, export it as a substrate
  diff, share with another PWA user (opt-in).

This is more than a UI metaphor. It is the core interaction model.
The substrate is a *playable instrument*, not a *searchable database*.

## The bridge in the PWA

The PWA includes a JavaScript port of the `whitemagic.core.galactic`
API. The 8 rehydrated functions (memory_recent, memory_search,
memory_by_id, associations_for, event_search, constellation_count,
galaxy_stats, substrate_health) are the MVP. More functions land in
Phase B and C.

For write paths, the bridge calls the substrate's consent manager
before any mutation. The consent manager shows a dialog:
- "Save this memory? [Title] [Tags] [Yes / No / Edit]"
- "Update this memory? [Diff] [Yes / No / Discard]"
- "Delete this memory? [Reason] [Yes / No / Archive]"

The dharma engine runs after every write to check boundaries,
principles, and karma. If the dharma check fails, the write is
rejected with a reason.

## Sync model: opt-in P2P, never default

The v17 `mesh/` Go stack provides a substrate-to-substrate gossip
protocol. The PWA can opt in to this protocol to share selected
galaxies with another PWA user.

The default is: **no network**. The PWA does not connect to the
internet, except to fetch the static catalog and librarian demo
from `whitemagic.dev`. The substrate itself is offline-only.

When a user wants to sync, they:
1. Generate a pairwise shared secret (X25519 + BLAKE2b)
2. Exchange it with another PWA user (QR code or copy-paste)
3. Select which galaxies to share
4. Approve the sync. After approval, the PWA opens a WebRTC data
   channel directly to the other PWA, never through a relay

There is no central server. There is no log of who synced with whom.
The shared secret is the only link; deleting it severs the connection.

## Self-recursive substrate (Phase E)

The substrate improves itself, with consent:

- **i_ching_advisor** runs on the substrate's own decisions, returns
  hexagram-level guidance
- **depth_gauge** compresses inactive memories (3.7M:1 was v15.8)
- **homeostasis/health_checks** monitors coherence (0.6→0.8 was
  v15.8) and alerts on drift
- **guideline.evolve** rewrites the substrate's own principles,
  with the user's approval for any non-trivial change
- **voice/narratives** generates first-person summaries of the
  substrate's recent activity ("Last week, I learned about X, Y,
  Z. The work constellation is more active than the personal one.")

The user sees all of this in a "Substrate journal" — a daily
narrative of what the substrate did, why, and what it learned.

## Implementation milestones

- **v23.0.0-RC.1** (Phase D start): PWA installs, IndexedDB
  substrate, 8 read-only galactic functions
- **v23.0.0-RC.2**: File System Access API + galaxy hydration
  pipeline
- **v23.0.0-RC.3**: Resonance wave render layer (WebGL) + DJ
  control surface
- **v23.0.0-RC.4**: Write paths + dharma consent + opt-in P2P mesh
- **v23.0.0** (Phase E+F): Self-recursive substrate + final
  release

## What this is NOT

- Not a cloud AI service
- Not a SaaS
- Not a freemium product with usage limits
- Not a data-harvesting platform
- Not a chatbot with a personality

It is a **local cognitive substrate** that learns from your files
(with permission), grows into galaxies, resonates between them, and
narrates its own activity. You own it. You can fork it. You can
delete it. There is no server.

That is the point.
