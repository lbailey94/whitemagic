# Two-Laptop Rehearsal — install-gate evidence runbook

> **Stranger runs:** for a faithful first-contact simulation (agent or
> human stranger, minimal supervision), follow
> [`docs/STRANGER_SIMULATION_SCRIPT.md`](STRANGER_SIMULATION_SCRIPT.md)
> instead — it is the pre-committed protocol and scoring rubric for
> that mode. This runbook remains the developer-mode install-gate
> evidence procedure.

**Consumes:** the `v7.0.0-alpha.6` release (or the current Latest).
**Produces:** dated friction logs + pass/fail evidence per machine, filed
as Gate 2 kit input. The rehearsal is a *gate*, not a demo: every friction
point is evidence, including the ones that pass.

Run the steps in order on each laptop; record every deviation honestly in
`~/whitemagic-rehearsal/<date>-<machine>.md` (template at the bottom).
Read-only laptops (older Linux): use the **musl** asset — it is the static
build and the supported path across glibc boundaries; the gnu asset is
expected to need a recent glibc (documented at G1.4).

## 1. Install path (the gate proper)

1. Download the release asset for the machine in a **clean browser** (no
   pre-authenticated helpers): `wm-linux-x86_64-musl` (Zorin/older Linux)
   or `wm-macos-aarch64` (Apple Silicon).
2. Verify the checksum the way a stranger would:
   - Linux: `sha256sum -c wm-linux-x86_64-musl.sha256`
   - macOS: `shasum -a 256 -c wm-macos-aarch64.sha256` (or compare against
     the `.sha256` file contents manually)
3. Install:
   - Linux: `chmod +x wm-linux-x86_64-musl && sudo cp wm-linux-x86_64-musl
     /usr/local/bin/wm`
   - macOS: `chmod +x wm-macos-aarch64 && sudo cp wm-macos-aarch64
     /usr/local/bin/wm` — expect **Gatekeeper**: the binary is unsigned
     (honest interim per V7_PRODUCT_READINESS). Record the exact refusal
     wording, then clear it with `xattr -d com.apple.quarantine
     /usr/local/bin/wm` (or right-click → Open on first launch). The
     friction itself is the evidence — signed/notarized artifacts are
     deferred to the public-beta gate.
4. `wm --version` → must print the released version.
5. `wm doctor` on a fresh store (or default path) → must be truthful:
   `[FAIL] LMDB store not found` before first serve is CORRECT behavior —
   record it, then re-run after step 2.

## 2. First-run + MCP handshake

1. `wm quickstart` — the two-process continuity demo must complete on its
   own. Note wall-clock time and any stderr noise.
2. `wm serve --profile curated` in one terminal; drive it from a supported
   MCP client (or raw stdio JSON-RPC: `initialize` → `tools/list` →
   `memory.create` → `memory.search` for the created content). The
   `initialize` instructions must disclose mode/project/store.
3. `wm doctor` again → sections render `[OK]`.
4. **macOS-only:** confirm `wm doctor` does NOT attempt Landlock (it is
   Linux-only — the doctor should show the platform-honest path, not a
   failure).

## 3. Cross-host mesh proof (optional but Gate-2-valuable)

The laptops on the same LAN run the first real cross-machine mesh
(`docs/MESH_JOIN_PROTOCOL.md` §3–4; beacons are link-local, so same
Wi-Fi/subnet qualifies).

**Per-machine prereqs (all three matter — most mesh failures are one of these):**

- Bind the **LAN IP**, not the wildcard: `--mesh-bind 192.168.x.y:7369` — a
  `0.0.0.0` bind announces `127.0.0.1` to peers and cross-host dial-back fails.
- UDP **and** TCP 7369 open (multicast discovery + RPC). If the AP blocks
  multicast (IGMP snooping is common), explicit `sangha.mesh.join` by IP is
  the fallback — log it as friction, it is evidence.
- `--profile full` (the `sangha.mesh.*` tools live there), plus a distinct
  `WM_MESH_KEY` and `WM_MESH_PEER_ID` per machine.

**Two-node sequence:**

1. Laptop A: `WM_MESH_KEY=<shared-secret-length-string> WM_MESH_PEER_ID=zorin
   wm serve --profile full --mesh --mesh-bind <A-LAN-IP>:7369`
2. Laptop B: same with its own peer id and `<B-LAN-IP>:7369`.
3. From A: `sangha.mesh.join {address: "<B-LAN-IP>:7369"}` → the response's
   `remote_registry.peer_count >= 1` proves B registered A's signed
   identity across machines.
4. `sangha.mesh.chat` A→B, `sangha.mesh.read` on B — verified delivery.
5. `sangha.mesh.quarantine` on B for A, then A `join` again → refused;
   release → rejoin works. File the transcript.
6. Firewall note: UDP 7369 (multicast) + TCP 7369 must be open; record any
   OS prompt. **No WM_MESH_KEY set? Expect the random-identity warning —
   that is the protocol working, not a bug.**

**Three-node extension (full-mesh = three joins):** C repeats the B steps
with its own key/peer id/binding; A then joins C. The mesh proof at n=3:
every node's `sangha.mesh.status` shows the other two in `peers`, a chat
sent on one node is read on both others, and a quarantine on any node is
visible in every `list`. Expected timing: discovery-only convergence
within `3 × WM_MESH_INTERVAL` seconds; explicit joins are immediate.
Real-time sharing scope: signed chat/signals/locks sync across machines;
**memory stores never replicate** — per-device sovereignty is the design,
not a gap (V8 peer-scoped projections are the store-sharing path).

## 4. Evidence filing

For each machine, one dated markdown file with: asset name + checksum
result, every command + timestamped outcome, verbatim error text for every
failure/prompt, wall-clock durations (download → install → first serve),
and a one-line verdict per section (pass/fail/blocked). File the files
with the Gate 2 kit; failures feed back into Gate 1 per the readiness
plan.

## Rehearsal log template

```markdown
# Rehearsal — <date> — <machine>

- Asset: <name> (sha256: <result>)
- OS: <distro/version or macOS version>
- Verdict: install <pass/fail> · first-run <pass/fail> · mcp <pass/fail> · mesh <pass/fail/n-a>

## Timeline
<command → outcome, with verbatim errors and wall-clock times>

## Frictions (each one is evidence)
<numbered list, severity, workaround used if any>
```
