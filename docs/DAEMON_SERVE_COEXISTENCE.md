# Daemon × serve coexistence — decision (2026-09-13)

**Status:** decided, implemented as documentation + existing behavior.
**Scope:** one store, multiple WM processes (`wm daemon`, writable `wm serve`,
`--readonly` serve, CLI writes, gateway).

## The invariant

**One Tantivy writer at a time.** `SearchEngine::open` takes the exclusive
`IndexWriter` (`crates/wm-memory/src/search.rs:409`); a second writer fails
with `format_writer_lock_error` (`search.rs:263-275`), whose message already
tells the operator to use `--readonly` or stop the other process. LMDB is not
the blocker — it is MVCC and read-only environments coexist freely
(`store.rs:355-359`); the exclusive resource is the search index writer.

Support facts:

- Writable construction: `wm serve` (no `--readonly`) and `wm daemon` both
  build `SearchEngine::open` (`wm-mcp/src/server.rs:754-765`).
- Read-only construction: `--readonly` opens `SearchEngine::open_readonly`,
  which creates **no writer** (`search.rs:431`, `:451`).
- `store_busy` is advisory preflight only — "not a lock: the actual writer
  lock remains Tantivy's" (`store_busy.rs:12-14`), and it exempts
  read-only serves (`:169-174`).

## Decision

**Option 3 — the read-only split with documented turn-taking — is the
supported mode today.** Option 1 (daemon-hosted MCP) is the intended
long-term architecture but needs a concurrency design first. Option 2 (lock
arbitration / serve queues writes into the daemon) is rejected.

### Supported operating modes

| Mode | Processes | Use when |
|---|---|---|
| **Writable window** | exactly one of `wm serve` (writable) **or** `wm daemon` | interactive writes, ingest, agent sessions |
| **Read alongside daemon** | `wm daemon` + any number of `--readonly` serves | steady-state dogfooding (VM pattern) |
| **Read-only tools** | `wm stats`, `wm doctor`, recall CLIs | always; they open read-only by design |

Rules of the road:

1. **Never start a writable serve while the daemon runs.** If the daemon owns
   the store, use `--readonly` for MCP surfaces or run writes through the
   `wm` CLI (which does not need the search writer for session/record paths).
2. **Read-only serves are snapshots.** `open_readonly` does not reload after
   open (`search.rs:433-439`; `search_opt` never calls `reload()`), so writes
   made after the serve started are invisible to it until restart. Restart
   the read-only serve after a write window to refresh.
3. **Turn-taking is explicit, not implicit.** To write, stop the daemon
   cleanly (`systemctl --user stop whitemagic-daemon` / graceful VM path),
   run the writable serve, then hand the store back.

### Option 1 — daemon hosts MCP (intended next)

The daemon already owns the writer; hosting an MCP surface removes the
coexistence question entirely. What it needs, per the code survey:

- A transport entry that does not own `&mut McpServer` for its lifetime:
  `run_sse`/`run_async` are infinite `&mut self` loops
  (`server.rs:1620`, `:1788`), while the daemon loop calls `&mut server` at
  29 sites (`daemon.rs:218`+) and sleeps on a 1 s cadence (`daemon.rs:427`).
- A concurrency design for that shared handle (`Arc<Mutex<_>>` or splitting
  cycle state from request state) with a watchdog-aware scheduler: a long
  dream/consolidation phase must not stall MCP requests past the daemon
  watchdog (`daemon.rs:406-424`), and MCP load must not starve cycles.
- Non-loopback auth before any of this is reachable off-host (the current
  gateway is loopback-only; see `ops/systemd/README.md`).

Acceptance for Option 1: one process serves MCP **and** runs cycles; writes
from MCP are visible to the same process's reads without a reload; shutdown
is single-path; a cycle stall is bounded and disclosed.

### Option 2 — lock arbitration (rejected)

Queueing serve writes into the daemon requires Option 1's transport plus a
new write-forwarding protocol (idempotency, backpressure, stale reads,
auth). It duplicates the hardest part of Option 1 while contradicting the
documented turn-taking doctrine (`docs/INGEST_COEXISTENCE.md:11-14`,
`docs/MULTI_LAPTOP.md:71`). Revisit only if Option 1 is abandoned **and**
the daemon can never host a transport.

## Current deployments

- **Host fleet:** writable serves per store, no daemon (daemon unit disabled).
- **MandalaOS VM:** `whitemagic-daemon` owns the store; `wm-mcp-readonly`
  serves on 28795; writes are `wm` CLI over SSH (verified working with the
  daemon active, e.g. `session record`).

## Host fleet topology and client patterns (2026-09-14)

Ten long-lived loopback processes: nine `wm-serve@<name>` units (all with
`--max-requests 0`) plus the federated gateway.

| Unit | Port | Store | Mode |
|---|---|---|---|
| `wm-serve@valkyrie` | 18785 | `~/.local/share/whitemagic` | curated, writable (device-local sanctuary; deliberately not federated) |
| `wm-serve@vault` | 18789 | `projects/vault` | curated, read-only |
| `wm-serve@wmv9` | 18790 | `projects/wmv9` | full, writable |
| `wm-serve@neon` | 18791 | `projects/neon` | curated, writable |
| `wm-serve@default` | 18792 | `projects/default` | curated, read-only scratch |
| `wm-serve@site` | 18793 | `projects/whitemagic-site` | curated, writable |
| `wm-serve@planning` | 18794 | `projects/planning` | curated, writable |
| `wm-gateway` | 18795 | (federation: wmv9, planning, vault, default) | `--federate`, no store |
| `wm-serve@heritage` | 18797 | `projects/heritage` | curated, writable |
| `wm-serve@opencode` | 18799 | `projects/opencode` | curated, writable |

Client rules learned the hard way (2026-09-14):

1. **Connect to the serve; never spawn a per-session stdio server against a
   served store.** A per-session `wm serve --store <served store>` takes the
   Tantivy writer and fails LockBusy against the unit — opencode's local MCP
   showed "inactive" in every session while a stale stdio holder owned the
   opencode store. If a store is served, clients point at its port
   (remote HTTP/SSE), and exactly one process owns the writer.
2. **CLI write paths contend too.** Session import/write CLIs against a
   served store need a maintenance window (stop the unit) or the MCP route;
   LMDB's MVCC does not exempt the Tantivy writer.
3. **`--max-requests 0` on long-lived shared serves.** The default
   per-connection cap (10,000) is sized for short-lived clients; a multiplexed
   desktop client exhausted it mid-day (2026-09-14) and every subsequent call
   failed until reconnect. Rate limits (`--rate-limit`,
   `WM_DISPATCH_TOOL_RPM` / `_GLOBAL_RPM` / `_BURST`) remain the runaway
   guard; the lifetime cap is the wrong tool for persistent connections.

## References

- `crates/wm-memory/src/search.rs` — writer lock + read-only semantics
- `crates/wm-mcp/src/store_busy.rs` — advisory preflight (not a lock)
- `crates/wm-mcp/src/daemon.rs` — cycle loop and watchdog
- `docs/INGEST_COEXISTENCE.md` — turn-taking doctrine
- `docs/MCP_CONFIG_GUIDE.md:78-94` — operator guidance ("add --readonly")
