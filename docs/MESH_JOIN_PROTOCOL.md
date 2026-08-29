# MESH_JOIN_PROTOCOL — how a device joins the Sangha mesh

**Status:** R0, shipped 2026-08-29 — written from verified behavior, not
aspiration. Every rule below is pinned by a named test (see §9).
**Surface:** `wm serve --mesh` (or `WM_MESH=1`), `crates/wm-sangha/src/
{transport,mesh_node}.rs`, the `sangha.mesh.*` tools (`--profile full`).
**Scope honesty:** this is the two-node, direct-TCP v0. No relay, no
multi-hop routing, no NAT traversal — the two-laptop rehearsal exercises
exactly this surface.

---

## 1. Why a protocol instead of a service

The mesh has no coordinator. Devices discover each other by beacon, bind
each other's identities cryptographically on first contact, and cut off
bad actors locally (the bad-apple rule) rather than trusting a central
board to do it. This is the Tachikoma shape: per-device sovereignty with
discretionary, scoped sharing — nightly *full* sync is the season-1
configuration, and this protocol starts at season 2. See
[`VERIFIABLE_MEMORY.md`](VERIFIABLE_MEMORY.md) §5 for the threat posture.

## 2. Transport and framing

- **TCP JSON-RPC** with length-prefixed framing: `[4-byte BE length][JSON
  payload]`, max 1 MB (`MAX_MESSAGE_SIZE`). Requests carry `method`,
  `params`, `id`; responses carry `result` or `error` + `id`.
- **Default port 7369** (`DEFAULT_PORT`), bind configurable via
  `--mesh-bind` / `WM_MESH_BIND`. A `0.0.0.0` bind announces
  `127.0.0.1:<port>` to peers (the local two-node case works out of the
  box); for cross-host meshes bind to a LAN-reachable address.
- **RPC methods:** `heartbeat` (identity registration), `discover`
  (registry read), `send_chat`, `broadcast_signal`, `acquire_lock`,
  `release_lock`, `sync_hologram`. Unknown methods fail with an error —
  never silence.

## 3. Discovery — beacons are addresses, not identity

Every `beacon_interval_sec` (default 5, `WM_MESH_INTERVAL`) a node
multicasts a `PeerAnnounce { peer_id, tcp_addr, capabilities, timestamp }`
to `224.0.0.69:7369`. Beacons are **unsigned**: they carry *where* a peer
can be reached, never *who it is*. A received beacon puts the address in
the discovery registry — nothing more. Trust comes only from the signed
handshake (§4); the auto-join loop (or an explicit `sangha.mesh.join`)
dials beaconed addresses and upgrades them into bound identities.
Quarantined peers are never auto-dialed.

## 4. Join — the signed heartbeat binds identity

1. **Dial.** The joiner opens TCP to the announced address
   (`connect_to_peer`; connections are keyed `remote:<addr>`).
2. **Announce.** The joiner sends `heartbeat` with its `PeerInfo` signed
   by its Ed25519 key (`PeerInfo::signed`): the payload is the canonical
   JSON of the record minus signature and public key; the public key
   travels inside the record.
3. **Bind.** The receiver verifies the signature and binds the public key
   to the peer ID **on first sight** (`discover_signed`). From then on:
   - a later announcement claiming the same ID with a **different key is
     refused as identity theft**;
   - unsigned or wrongly-signed announcements are refused (the legacy
     unsigned path exists only for in-process, non-mesh use);
   - a **quarantined** peer's re-registration is refused until released.
4. **Read back.** The joiner's `sangha.mesh.join` response carries the
   remote's registry summary after the bind — the proof the other side
   now knows who you are.

Mesh-wide identity is symmetric: both sides join both ways (organically,
via the auto-join loop on each node's beacons).

## 5. Keys

- `WM_MESH_KEY` (any non-empty string) seeds the node's Ed25519 keypair;
  set it for a **stable identity across restarts**. Unset → a random
  per-process key + a loud warning (a hardcoded default would be shared
  by every WhiteMagic node — an impersonation primitive, not a
  convenience).
- Peer ID default: `wm-` + first 12 hex chars of the public key.
  `WM_MESH_PEER_ID` overrides with a readable name; identity binding
  still keys on the public key, so names are labels, not credentials.
- Chat messages are signed the same way (canonical payload = serialized
  `ChatMessage` minus signature and public key) and verified on arrival
  against the sender's bound key.
- **v0 limitations (deliberate):** key material handling (0700 files,
  keyring, rotation, revocation) is V8 backlog item 2; `WM_MESH_KEY`
  should be treated as a secret until then.

## 6. Conversation — chat, locks, signals

Signed chat flows over the bound connection: the receiver verifies the
message signature, checks the sender binding, and refuses quarantined
senders at ingest (§7). Unsigned relay over mesh TCP is refused in the
same handler. Locks (`acquire_lock`/`release_lock`) are TTL-bounded and
per-peer; a quarantine revokes the bad apple's locks so the community is
never held hostage by its resources. Hologram sync merges coordinate
entries with importance-wins conflict resolution.

## 7. Quarantine — the bad-apple rule

`sangha.mesh.quarantine` (actions: `quarantine` / `release` / `list`)
cuts a peer off **locally**, which is the only place trust lives:

1. Registry quarantine with a recorded reason — re-registration refused
   (rejoin path dead until release).
2. Chat messages from the sender purged; further signed chat **refused at
   ingest**, even over a connection it opened before the quarantine.
3. Resource locks revoked.
4. The node's own connection to the peer is dropped; the auto-join loop
   never re-dials a quarantined peer.

Release (`release`) restores the join path; the next signed heartbeat
re-binds (same key required — the binding survives the quarantine).

## 8. Surface

| Knob / route | Meaning |
|---|---|
| `wm serve --mesh` / `WM_MESH=1` | Enable the transport (strict `1`, mirrors `WM_LANDLOCK`) |
| `--mesh-bind` / `WM_MESH_BIND` | TCP bind (default `0.0.0.0:7369`) |
| `WM_MESH_KEY` | Identity seed (stable across restarts) |
| `WM_MESH_PEER_ID` | Readable node name |
| `WM_MESH_INTERVAL` | Beacon + auto-join cadence (seconds) |
| `sangha.mesh.status` | Node identity, connections, registry, chat/lock summaries |
| `sangha.mesh.join` | Dial + bind (§4) |
| `sangha.mesh.chat` / `.read` | Signed chat send / receive |
| `sangha.mesh.quarantine` | Bad-apple governance (§7) |
| `/status` → `mesh` | Non-blocking node disclosure (null when `--mesh` off) |

Mesh startup failures degrade loudly and non-fatally (a bad bind logs a
WARN and the server continues unmeshed — the Landlock doctrine). The
`sangha.mesh.*` tools live on the **full** profile; on a curated server
the transport can run but the tools are filtered out — start mesh servers
with `--profile full`.

## 9. Verified behavior (evidence)

- **Unit (`wm-sangha`, `mesh_node` tests):** join binds both registries;
  signed chat delivered and verified; quarantine refuses chat + rejoin,
  release restores; strict flag parse; announce normalization; sync status.
- **Containment (`transport.rs` containment_tests):** forged chat
  rejected, identity theft refused at registration and at re-announce.
- **E2E (`wm-mcp/tests/mesh_serve_e2e.rs`):** two real `wm serve --mesh`
  processes — discover/bind/chat/quarantine/release/rejoin, full sequence.
- **Live run (2026-08-29, this machine):** the same sequence scripted
  against two debug-binary servers on throwaway stores — PASS (recorded
  in the R0 session notes).

## 10. Threat-model mapping (MAESTRO)

Per the strategy doc's V8 backlog, the join protocol is the reference
implementation surface for the CSA MAESTRO agentic layers:

- **Model layer** — signed payloads mean a compromised peer cannot forge
  another peer's statements (Ed25519 binding, §4–5).
- **Tool-integration layer** — mesh-received content never writes the
  store directly in v0; chat/locks live in mesh state, and peer-scoped
  store projections (per-peer compartments with mesh provenance + trust)
  are the V8 federation path.
- **Orchestration layer** — no coordinator exists to capture; quarantine
  is a local community decision with a recorded reason (auditability).
- **Environment layer** — TCP/UDP are the only open surfaces; a bad bind
  fails loud, message size is capped, and unknown RPC methods fail
  closed.

## 11. What v0 does not do

Honest list, so nobody assumes otherwise: no encryption in transit (TLS
is a V8+ item; the wire is readable by a local passive observer), no
relay/multi-hop or NAT traversal, no peer discovery across subnets
(multicast is link-local), no revocation lists (quarantine is per-node,
by design), and key management is a shared-secret-free but unmanaged
file/env surface pending B7. Each of these is a gate on Gate 2 cohort
use, not a silent gap.
