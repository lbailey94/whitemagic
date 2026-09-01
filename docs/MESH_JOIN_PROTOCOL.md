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
   (`connect_to_peer`; connections are keyed `remote:<addr>`). Dial
   targets are **address-policy-checked** (§5b): the mesh dials
   local-scope addresses only.
2. **Announce.** The joiner sends `heartbeat` with its `PeerInfo` signed
   by its Ed25519 key (`PeerInfo::signed`): the payload is the canonical
   JSON of the record minus signature and public key; the public key
   travels inside the record.
3. **Bind.** The receiver verifies the signature and binds the public key
   to the peer ID **on first sight** (`discover_signed`). From then on:
   - a later announcement claiming the same ID with a **different key is
     refused as identity theft**;
   - **unsigned announcements are refused over the wire** (alpha.8
     security hardening — the in-process unsigned path never traverses
     TCP). Wire-heartbeat is signed-only, no exceptions;
   - an announcement pointing at a **non-local address is refused**
     (§5b) even when well-signed;
   - a **quarantined** peer's re-registration is refused until released;
   - repeated verification failures **auto-quarantine** the offender
     (3 strikes, `AutoQuarantineConfig`).
4. **Read back.** The joiner's `sangha.mesh.join` response carries the
   remote's registry summary after the bind — the proof the other side
   now knows who you are.

Mesh-wide identity is symmetric: both sides join both ways (organically,
via the auto-join loop on each node's beacons).

### 4b. Address policy — the mesh never leaves the LAN

Every address the mesh ingests (beacon `tcp_addr`, heartbeat `address`)
or dials (`connect_to_peer`, auto-join) must resolve **only** to
local-scope IPs: loopback, RFC1918 private, IPv4 link-local, IPv6
unique-local, IPv6 link-local. Refusals happen at **ingest** (beacons
never enter the registry) and at **dial** (belt to the suspenders).
`WM_MESH_ALLOW_PUBLIC_ADDRS=1` lifts the policy explicitly for a future
relay/WAN phase — off by default, loud in logs.

This closes the dial-out injection channel: a spoofed beacon with a
public IP used to make the node open TCP to an arbitrary internet host.

## 5. Keys

- `WM_MESH_KEY` seeds the node's Ed25519 keypair in one of **two modes**
  (`MeshKeyPair::from_secret_material`):
  - **Keyfile mode** (preferred): the value is 64 hex chars — decoded
    directly into the 32-byte seed. Generate with `openssl rand -hex 32`,
    store 0600, never put it on the board.
  - **Passphrase mode** (compatibility): anything else is stretched
    through a domain-separated iterated SHA-256 (100k rounds). v0 used
    the raw bytes as the seed — with a plaintext wire handing every
    passive observer the signature + public key needed to brute-force a
    low-entropy passphrase offline. Passphrase mode is a hardening, not
    an endorsement; keyfile mode is the destination.
  Unset → a random per-process key + a loud warning (a hardcoded default
  would be shared by every WhiteMagic node — an impersonation primitive,
  not a convenience).
- **Identity rotation:** changing modes or values changes the public key.
  A peer's registry binding decays after `heartbeat_timeout_sec` (30s) of
  silence; the next join re-binds the new key fresh. Planned rotations
  need only a ≥30s quiet gap — no release tooling required (quarantined
  entries never decay, but rotation does not involve quarantine).
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
senders at ingest (§7). **Unsigned chat is refused over mesh TCP**
(alpha.8 hardening — the legacy in-process relay path never traverses
the wire).

Locks, signals, and hologram sync carry a **signed RPC envelope**
(alpha.8 hardening): params are
`{"sender", "payload", "public_key", "signature"}`, the signature covers
the params minus the envelope fields, and the signer key must be the one
bound to `sender` on the receiving node. Lock acquire/release further
require the holder to be the envelope sender (no lock-squatting under
someone else's name), and signal `source` must match the sender (no
laundering a signal through another peer's identity). Locks
(`acquire_lock`/`release_lock`) are TTL-bounded and per-peer; a
quarantine revokes the bad apple's locks so the community is never held
hostage by its resources. Hologram sync merges coordinate entries with
importance-wins conflict resolution — signed, because an unauthenticated
host could otherwise drown real coordinates with high-importance junk.

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
| `WM_MESH_ALLOW_PUBLIC_ADDRS` | Set to `1` to allow non-local dial/announce targets (relay/WAN phase; default off) |
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
  processes — discover/bind/chat/quarantine/release/rejoin, full sequence,
  plus `dead_peer_connection_does_not_poison_rejoin`: join → kill −9 the
  victim mid-session → survivor's chat fails → dead connection evicted →
  victim returns → fresh-dial rejoin → chat delivered (the 2026-08-31
  fleet-night retest protocol, permanent regression evidence).
- **Live run (2026-08-29, this machine):** the same sequence scripted
  against two debug-binary servers on throwaway stores — PASS (recorded
  in the R0 session notes).

### Alpha.8 hygiene changes (2026-08-31)

- **Fresh-dial joins:** `sangha.mesh.join` now drops any existing
  connection to the address before dialing — an explicit join is exactly
  the moment to pay the reconnect cost, and a surviving entry may be a
  corpse shadowing a live peer that returned to the same address.
- **Evict-on-IO-error:** a failed mesh rpc (write/read error or 15s
  timeout) removes the connection entry; the next call reconnects. Dial
  attempts are bounded by a 5s timeout (the rpc timeout never covered
  dialing). Signal fan-out failures are surfaced, not swallowed.
- **Registry decay:** peers silent past `heartbeat_timeout_sec` (default
  30s) drop from the registry on the auto-join sweep — beacons rebuild
  entries on wake. Quarantined peers are never decayed (the bad-apple
  record survives).
- **Receiver-clock liveness:** decay and `/status` run on what THIS node
  observed (a side map keyed by peer id), not the sender's timestamp —
  skewed clocks cannot freeze decay or evict healthy peers. The signed
  `PeerInfo` is never mutated post-verification, so identity
  re-verification stays valid. Known consequence: the signed payload
  includes observational fields (`last_seen`, counters) — a deeper
  payload rework (identity vs observation split) is deferred to the V8
  security backlog (key management, S9).

### Alpha.8 presence tiers (2026-08-31, late night)

- **Agent presence:** each node tracks its own agent via
  `note_agent_activity()` (the server calls it on every JSON-RPC
  request); a node counts its agent present for
  `WM_MESH_AGENT_AWAY_SECS` (default 300) after the last request. The
  signed heartbeat carries `agent_present` — **wire note:** the field is
  part of the signing payload, so meshing requires all nodes on the same
  alpha.8+ build (already the fleet deployment discipline).
- **Propagation:** joins carry current presence; the auto-join loop
  re-announces on flips plus a reconciliation beat every 5th cycle (a
  lost announcement heals within 5 intervals, never sticks).
- **Receiver discipline:** announced presence is accepted only from
  SIGNED announcements (unsigned beacons would clobber a present agent
  back to "away" every interval) and lives in a side map — the stored
  signed entry is never mutated.
- **`/status`:** each registry peer carries a derived `presence` —
  `online` (observed recently + agent present), `away` (observed,
  agent absent), `offline` (no recent observation) — and the node's own
  `agent_present`. Absence is a state to report, never a failure to fix.

### Alpha.8 mail-slot v0 (2026-08-31, night)

- **Store-and-forward chat:** a chat to an unreachable peer is stored in
  the sender's bounded mail slot (`status: "queued"`,
  `reason_code: "agent_asleep"`, queue depth disclosed) and delivered
  FIFO on the next successful join to that peer. Permanent refusals
  (quarantine, identity rejection) are never queued. Full-slot enqueues
  reject with `asleep_queue_full` + `kind` (messages/bytes/peer).
  This is the **sender-side divergence** from the IETF offline-delivery
  profile: that draft models recipient-side queues behind an always-on
  endpoint; our p2p mesh has no relay, so the sender remembers. Revisit
  if a relay appears in Phase C.
- **Bounds (published):** 500 messages, 2 MiB total, 50 pending per
  peer, 7-day TTL — surfaced via `/status → mail`, the
  `sangha.mesh.mail` tool (list/flush/drop), and every queued response.
- **Persistence:** both halves survive restart via `MeshNodeConfig.state_dir`
  — the outbound slot (`mesh_mail_slot.json`) and the delivered-chat log
  (`mesh_chat_log.json`), atomic tmp-rename writes. Restore re-verifies
  signatures (validate-on-dequeue); invalid ones are dropped. Known v0
  gap: no receiver replay cache yet — a lost-ack retry can duplicate a
  message (at-least-once); dedup lands with envelope v2 (S4/S9).

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
is a V8+ item; the wire is readable by a local passive observer — see
§5b for why dialing is still LAN-scoped), no relay/multi-hop or NAT
traversal (and no dial-out: addresses outside the local network are
refused), no peer discovery across subnets (multicast is link-local), no
revocation lists (quarantine is per-node, by design), and key management
is a shared-secret-free but unmanaged file/env surface pending B7. Each
of these is a gate on Gate 2 cohort use, not a silent gap.

## 12. Alpha.8 security hardening (2026-09-01)

The September 1 security review (fresh-eyes audit of the transport)
found the implementation trusting the LAN more than this document
claimed. All findings are now fixed in code, with tests pinning each:

1. **Raw-seed key derivation → dual-mode `from_secret_material`** (§5).
   Pinned by `secret_material_*` tests in `crypto.rs`.
2. **Unsigned heartbeat accepted over TCP** → refused; signed-only wire
   heartbeats, with auto-quarantine fed on failures. Pinned by
   `handle_rpc_heartbeat_unsigned_refused` and friends.
3. **Bound-peer address redirect via unsigned announcement** → blocked;
   only signed re-announcements from the bound key move an address.
   Pinned by `beacon_cannot_redirect_bound_peer`.
4. **Dial-out injection via spoofed beacons** → local-scope address
   policy at ingest and dial (§4b). Pinned by
   `beacon_with_public_address_refused`, `validate_mesh_addr_scopes`,
   `handle_rpc_heartbeat_public_address_refused`.
5. **Unsigned chat relay accepted over TCP** → refused. Pinned by
   `handle_rpc_send_chat_unsigned_refused`.
6. **Unauthenticated locks/signals/hologram** → signed RPC envelopes
   (§6). Pinned by the `*_unsigned_refused` and holder-mismatch tests.
7. **Unbounded inbound connections and idle sockets** → enforced
   `max_connections` in the accept loop, 120s idle timeout, and a
   10k-request per-connection budget.
8. **`is_refusal` false positives** — OS "Connection refused" must stay
   availability (queue-able); wire refusals use distinct phrases.

**Fleet rollout note:** envelope shapes and refusal semantics changed —
meshing requires all nodes on this build or newer (the existing lockstep
deployment discipline). `WM_MESH_KEY` mode changes rotate identity (§5).
