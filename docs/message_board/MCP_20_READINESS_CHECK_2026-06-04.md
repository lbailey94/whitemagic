# MCP 2.0 Readiness Check — PRAT Gana Meta-Tools

**Date**: 2026-06-04
**MCP spec target**: 2026-07-28 Release Candidate (published May 21, 2026)
**WhiteMagic surface**: `run_mcp_lean.py` (28 Gana meta-tools) + classic MCP (`run_mcp.py`, 479 tools)

---

## Current State

WhiteMagic runs two MCP server surfaces:

| Surface | Transport | Tools | Status |
|---------|-----------|-------|--------|
| **Lean** (`run_mcp_lean.py`) | stdio + Streamable HTTP (`--http`) | 28 PRAT Ganas | Active, primary |
| **Classic** (`run_mcp.py`) | stdio + HTTP+SSE | 479 native tools | Legacy, still works |

Both use the Python `mcp` SDK (version pinned in `core/pyproject.toml`).

---

## MCP 2.0 Gap Checklist

### 🔴 Critical (blocks MCP 2.0 client compatibility)

| Requirement | Current | Gap |
|---|---|---|
| **Stateless core** — no session stickiness | `state_board` uses mmap shared memory; `_result_cache` is in-process | `state_board` breaks horizontal scaling; `_result_cache` is per-instance |
| **`_meta` on every request** with protocol version + client info | Not sent | All tool calls need `_meta` wrapper |
| **`server/discover` method** | Not implemented | Replaces `initialize`/`initialized` handshake |
| **OAuth 2.1 + PKCE** | `.env` API keys only | No OAuth flow; blocks managed gateway integration |

### 🟡 Medium (limits operability / registry listing)

| Requirement | Current | Gap |
|---|---|---|
| **`Mcp-Method` / `Mcp-Name` headers** | Not sent | Needed for load-balancer routing without body inspection |
| **`ttlMs` + `cacheScope` on `tools/list`** | Not sent | Clients can't cache tool lists safely |
| **Server Cards (`.well-known` dynamic)** | `agent.json` is static | Needs dynamic generation from loaded tools + OAuth metadata |
| **Extensions negotiation** | Not implemented | PRAT Ganas are hardcoded; should be advertised as extensions |
| **Feature lifecycle awareness** | Not implemented | No deprecation tracking for old tool signatures |

### 🟢 Low (nice-to-have, no urgency)

| Requirement | Current | Gap |
|---|---|---|
| **MCP Apps (server-rendered UI)** | Dashboard exists in Flask | Not packaged as sandboxed iframe templates |
| **Tasks extension protocol** | Slow Ganas marked `taskSupport=TASK_OPTIONAL` | Not using formal `tasks/get`/`tasks/update`/`tasks/cancel` lifecycle |
| **W3C Trace Context in `_meta`** | OTEL integration exists | Not wired into MCP envelope |

---

## PRAT Gana Meta-Tools: Extension vs. Core

MCP 2.0's Extensions framework (SEP-2133) is the formal path for new capabilities. PRAT Ganas predate this but map cleanly:

| PRAT Gana | MCP 2.0 extension ID | Extension type |
|---|---|---|
| `gana_horn` — Session Initiation | `ext.prat.session` | Lifecycle |
| `gana_neck` — Memory Creation | `ext.prat.memory` | Data |
| `gana_winnowing_basket` — Search/Recall | `ext.prat.memory` | Data |
| `gana_star` — PRAT Illumination (tool routing) | `ext.prat.dispatch` | Control |
| `gana_ghost` — Introspection | `ext.prat.telemetry` | Observability |
| `gana_dipper` — Governance | `ext.prat.governance` | Control |
| `gana_three_stars` — Wisdom Council | `ext.prat.reasoning` | Reasoning |
| `gana_void` — Galaxy/Namespace mgmt | `ext.prat.memory` | Data |

**Recommendation**: Do not refactor 28 Ganas into 7 extensions immediately. Instead, add an `extensions` map to the Server Card advertising PRAT as a single experimental extension (`ext.prat.gana-v1`) with delegated documentation. This preserves the existing surface while signaling MCP 2.0 awareness.

---

## Immediate Fixes (1–2 days)

1. **Update `agent.json`** version to `22.2.0`, correct tool count to 479 / 28, add `mcp` compatibility fields
2. **Add `WM_MCP_STATELESS=1` mode** — skip `state_board` mmap, use pure JSON-RPC per-request state
3. **Add `_meta` wrapper** to `call_tool` response with `protocolVersion`, `serverInfo`, `clientInfo`
4. **Add `server/discover` handler** — return capabilities + extensions map

## Short-term Fixes (1–2 weeks)

5. **Dynamic Server Card** — generate `.well-known/agent.json` from `tool_surface` at server boot
6. **OAuth placeholder** — add `authorization` section to Server Card with `oauth2.1` + PKCE metadata even if not yet implemented
7. **`ttlMs` on `tools/list`** — compute from `_result_cache` freshness or set conservative default (60s)
8. **Extensions negotiation stub** — advertise `ext.prat.gana-v1` in `server/discover`

## Not Yet Needed (wait for final spec, Jul 28)

9. MCP Apps iframe templates
10. Full Tasks extension lifecycle
11. W3C Trace Context propagation

---

## Test Strategy

| Test | Command | Pass criteria |
|---|---|---|
| MCP 1.0 backward compat | `python -m whitemagic.run_mcp_lean` with Claude Desktop | 28 tools listed, calls succeed |
| Stateless mode | `WM_MCP_STATELESS=1 python -m whitemagic.run_mcp_lean --http` | Two server instances behind nginx round-robin serve same request |
| Server Card valid | `curl /.well-known/agent.json \| python -m json.tool` | Valid JSON, correct version, tools array present |
| `server/discover` | Custom MCP 2.0 client test | Returns capabilities with `extensions` map |

---

## Risk Assessment

| Risk | Severity | Mitigation |
|---|---|---|
| MCP 2.0 clients reject WM server due to missing `_meta` | 🔴 High | Add `_meta` wrapper before Jul 28 |
| Registry delisting for static Server Card | 🟡 Medium | Make dynamic within 2 weeks |
| `state_board` mmap prevents cloud deployment | 🟡 Medium | Add `WM_MCP_STATELESS=1` mode |
| OAuth requirement blocks enterprise adoption | 🟡 Medium | Add OAuth metadata stub, implement flow in Q3 |

---

*Status: Audit complete. No code changes yet. Ready for prioritization against grant/publication sprints.*
