# Boundary receipt — wm-node transport thread spawns (2026-10-07)

**Status:** ratified (extension of the mesh transport boundary, 2026-09-27)
**Scope:** `crates/wm-gen3-harness/src/bin/wm_node.rs`

## Decision

`scripts/check_closures.sh` rule [3/3] (Article 4 — no authoritative thread
spawns outside the physical-I/O transport) now permits thread spawns in
`bin/wm_node.rs`, matching the existing allowances for `transport.rs`,
`mesh.rs`, and `mcp_server.rs`.

## Rationale

`wm-node` is the Geth Phase-2 Unix-domain-socket listener (spec:
`planning/AGENTIC_CONSENSUS_NETWORK_GETH_SPEC.md`). Its spawn sites are:

- the accept loop that accepts UDS connections and hands each to a worker
  (`wm_node.rs` ~1036) — physical I/O/listening, same class as the
  `mcp_server.rs` `serve_network` accept loop; and
- the per-connection frame handler (`wm_node.rs` ~1159) — frame I/O, same
  class as `mesh.rs` per-connection handlers.

Neither site can hold mutation authority: connections only enqueue
tuple/signal/proposal messages into in-memory or fixed-file persistence behind
the node's own lock; no `CommitCapability` is constructed off the main thread
(and `CommitCapability` is `!Send`/`!Sync`, so it cannot cross a spawn by
construction).

## Enforcement

The scanner was extended exactly as its own rule requires ("extend this rule
deliberately (with a receipt), not by relaxing the scan"): the allowlist regex
gains `bin/wm_node\.rs` and the header comment names this receipt. Any future
spawn outside the four transport files still fails the scan.

## Evidence

- `wm-node` tests: `cargo test -p wm-gen3-harness --bin wm-node` (9) and
  `--test wm_node_e2e` (4), all green at `feat/geth-node` merge (2026-10-07).
- Closure scan after the extension: `bash scripts/check_closures.sh` → PASS.
- Prior review: adversarial wave-2 review of `wm-node` (socket-path safety,
  frame bounds, double-bind) — must-fixes landed in `209ad8c`.
