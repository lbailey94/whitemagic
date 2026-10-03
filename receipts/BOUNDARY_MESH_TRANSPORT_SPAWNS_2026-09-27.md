# Boundary receipt: mesh transport thread spawns (Article 4 allowlist)

**Date:** 2026-09-27
**Author:** opencode (T4800-S), from the miranda-macbook macOS port report (#304)
**Scope:** `crates/wm-gen3-core/src/mesh.rs` — two `std::thread::spawn` sites
(`listen()` accept loop and per-connection frame handler, ~565/~573)
**Status:** ratified boundary decision (allowlist extension)

## What the gate found

`scripts/check_closures.sh` [3/3] failed at tip `0d1a5c3` on macOS (and Linux):
two spawn sites in `mesh.rs` are outside the single-file allowlist
(`transport.rs`). Article 4 says threads may exist only for physical I/O.

## Decision

`mesh.rs` **is** a physical-I/O transport: a TCP listener accept loop plus one
handler thread per connection doing frame assembly/response. Extend the
allowlist to `crates/wm-gen3-core/src/(transport|mesh).rs` instead of moving
the code, because:

1. The spawns are pure socket I/O — accept, read frames, write frames.
2. Authority cannot cross a spawn: `CommitCapability` is `!Send/!Sync`, so a
   spawned thread cannot hold or obtain mutation authority (the original
   rationale for the single-file rule).
3. The per-connection thread is bounded by `DEFAULT_FRAME_ASSEMBLY_TIMEOUT`
   read/write timeouts and exits with the connection.

## Verification

- `bash scripts/check_closures.sh` → all three scans PASS (Linux, 2026-09-27).
- The macOS seat re-runs the same script from the bundle; the scan is static
  and platform-independent, so the result carries.

## Follow-up

If mesh gains non-I/O work on those threads (retries with state, background
timers), this receipt must be revisited — the allowlist covers I/O, not
cognition.
