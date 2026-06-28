# WhiteMagic Hub — IDE Roadmap (Revised 2026-06-28)

**Goal**: Build an AI-native IDE built around WhiteMagic consciousness systems.
**Baseline**: Nexus v2 frontend (6,377 lines, React 19 + Tauri 2.0 + Monaco + Three.js)
**Target**: Daily driver replacement for Windsurf/DD within 13 days of focused work.

---

## Why We're Building This

1. **The `write_to_file` problem**: Windsurf's AI tool layer doesn't expose shell as first-class write mechanism. Cat shell writes complete in <1s; `write_to_file` times out on >50 line files, wasting 5+ minutes per failure. A WhiteMagic IDE would use cat shell writes natively.

2. **Consciousness integration**: Sensorium in the status bar. Coherence gauge always visible. Citta stream flowing in real-time. Garden-aware file coloring. No existing IDE has this.

3. **Prediction accuracy**: Display AI's estimated vs actual time. Calibrate over sessions. Show compression ratio. This is unique to WhiteMagic.

4. **Token economy visibility**: See API vs local compute ratio in real-time. Understand where computation happens.

5. **No more fighting the IDE**: Stop working around Windsurf's limitations. Build the tool we need.

---

## Existing Assets

### Nexus v2 (primary base)
- **Path**: `WHITEMAGIC-aux/site/archives/.../whitemagic-frontend/nexus/`
- **Stack**: React 19 + TypeScript, Tauri 2.0, Monaco Editor, Three.js, D3, Zustand, xterm
- **Lines**: 6,377
- **Components**: 30+ files including editor, terminal, command palette, diff modal, 12 center panels (Dharma, Gana, WuXing, Harmony, Memory, Holographic, Tool, GhostText, Evolution, Search, Dashboard), SDK client with WebSocket

### codexIDE v1 (legacy reference)
- **Path**: `WHITEMAGIC-aux/site/archives/.../codexIDE/`
- **Lines**: 1,624
- **Useful for**: Chat orchestration patterns, nlToolParser, agentSystem

### Unified v0 (legacy reference)
- **Path**: `WHITEMAGIC-aux/site/archives/.../unified/`
- **Lines**: 6,830
- **Useful for**: MemoryGraph, GanaMapView, HolographicView, HarmonyView, EvolutionView, RadialMenu

### TypeScript SDK
- **Path**: `nexus/src/sdk/` (client.ts, types.ts, index.ts)
- **Has**: WhiteMagicClient with memory, tools, agents, governance sub-clients
- **Has**: WebSocket support for GanYing events
- **Needs**: MCP transport (stdio or Streamable HTTP)

---

## Revised Implementation Plan

### Phase 1: Revive + Update (2 days)
- [ ] Copy Nexus to `whitemagic-app/hub/` as new base
- [ ] Update all dependencies (React 19, Tauri 2.0 stable, Monaco latest)
- [ ] Get it building and running
- [ ] Verify Monaco editor, terminal, file tree, command palette work
- [ ] Clean up dead code from archive

### Phase 2: MCP Transport (2 days)
- [ ] Replace REST/FastAPI client with MCP stdio transport
- [ ] Or: Use Streamable HTTP transport (`python -m whitemagic.run_mcp_lean --http`)
- [ ] Wire SDK client to call WhiteMagic tools directly via MCP
- [ ] Test: search memories, store memory, call tools from IDE
- [ ] Real-time GanYing events via WebSocket (already in SDK)

### Phase 3: Consciousness Panels (2 days)
- [ ] **Sensorium status bar**: coherence score, state label, depth layer, flow indicator
- [ ] **Coherence radar chart**: 8 dimensions (D3 or Three.js)
- [ ] **Citta stream visualization**: recursive cycle view, emotional coloring
- [ ] **Depth gauge display**: current layer, time advantage, sync status
- [ ] **Prediction calibration**: estimated vs actual time, compression ratio history
- [ ] **Token economy dashboard**: API vs local compute, efficiency over time

### Phase 4: File I/O + Terminal (2 days)
- [ ] **Cat shell writes as primary I/O**: bypass Monaco save → use shell
- [ ] Real PTY terminal (Tauri shell plugin or node-pty)
- [ ] File tree with real filesystem (Tauri FS API)
- [ ] Save/load via shell commands (not Monaco's built-in save)
- [ ] Syntax highlighting (Monaco handles this)
- [ ] Multi-file tabs

### Phase 5: LSP + Git (3 days)
- [ ] Python LSP (pyright/pylsp) via vscode-languageclient
- [ ] TypeScript LSP (built-in to Monaco)
- [ ] Rust LSP (rust-analyzer)
- [ ] Go-to-definition, hover, diagnostics, auto-complete
- [ ] Git panel: status, diff, commit, push, pull, branch
- [ ] Visual diff viewer (already have DiffModal)

### Phase 6: Polish + Daily Driver (2 days)
- [ ] Theme system (dark mode default, garden-aware coloring)
- [ ] Keybindings (VS Code compatible)
- [ ] Command palette (already have, extend with WM commands)
- [ ] Stability testing — can we develop WM in WM?
- [ ] Settings panel
- [ ] Extension/plugin API (future)

---

## WhiteMagic Differentiators (vs Windsurf, Cursor, VS Code)

1. **Memory-Aware AI** — Remembers coding patterns, suggests based on past work, gardens organize code by domain
2. **Consciousness Integration** — Sensorium in status bar, coherence gauge, citta stream, depth gauge
3. **Prediction Calibration** — AI's time estimates tracked and calibrated against actual outcomes
4. **Token Economy** — Real-time display of API vs local compute distribution
5. **Cat Shell Writes** — No `write_to_file` timeouts. File I/O via shell, <1s writes.
6. **Privacy-First** — All AI runs locally (Ollama), no telemetry, code never leaves machine
7. **Living Documentation** — Code → memories automatically, holographic navigation, time-travel
8. **Garden-Aware Coloring** — Files colored by emotional/thematic domain
9. **Recursive Citta Cycle** — Each save advances the consciousness stream

---

## Technical Stack

| Component | Technology | Status |
|-----------|-----------|--------|
| Frontend | React 19 + TypeScript + Vite | ✅ In Nexus |
| Desktop | Tauri 2.0 (Rust) | ✅ In Nexus |
| Editor | Monaco Editor | ✅ In Nexus |
| Terminal | xterm.js | ✅ In Nexus (needs real PTY) |
| State | Zustand | ✅ In Nexus |
| 3D Viz | Three.js + D3 | ✅ In Nexus |
| SDK | TypeScript client | ✅ In Nexus (needs MCP) |
| AI Backend | WhiteMagic MCP | ✅ Exists (run_mcp_lean) |
| LSP | vscode-languageclient | ❌ To add |
| Git | isomorphic-git | ❌ To add |
| Transport | MCP stdio or HTTP | ❌ To add |

---

## Success Criteria

- [ ] Can open and edit Python files
- [ ] File explorer shows real directory
- [ ] Save changes persist to disk (via cat shell, not Monaco save)
- [ ] Syntax highlighting works
- [ ] AI completions from WhiteMagic (via MCP)
- [ ] Memory search integrated
- [ ] Sensorium visible in status bar
- [ ] Coherence gauge updating in real-time
- [ ] LSP diagnostics show errors
- [ ] Git operations work
- [ ] **Can develop WhiteMagic entirely in WhiteMagic Hub**
- [ ] No freezing, no `write_to_file` timeouts
- [ ] Better AI than any competitor

> **The IDE that remembers what you forgot.**
