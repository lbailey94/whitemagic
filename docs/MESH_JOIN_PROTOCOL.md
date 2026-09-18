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

## 3. Discovery — signed beacons, bound on first sight

Every `beacon_interval_sec` (default 5, `WM_MESH_INTERVAL`) a node
multicasts a `PeerAnnounce { peer_id, tcp_addr, capabilities, timestamp,
signature, public_key_hex }` to `224.0.0.69:7369`. Since 9.1.8 beacons are
**signed and carry the signer's public key**; the signed payload binds all
fields (`peer_id:tcp_addr:timestamp:public_key_hex`), so a captured beacon
cannot be relocated or re-keyed. Ingest policy:

- **Freshness:** `|now − timestamp| ≤ 2 × interval`; stale beacons are dropped.
- **Rate limit:** a per-source budget (8 per interval) suppresses floods.
- **Replay:** a bounded replay cache records verified `(peer_id, timestamp)`
  observations; a replay inside the window is dropped. Only
  signature-verified observations are recorded — a forged beacon cannot
  consume the replay slot of the genuine one.
- **Binding:** a signed beacon is **TOFU-bound** to its peer ID on first
  sight; a later beacon for the same ID announcing a different key is
  refused as identity theft (the binding follows stale eviction, so an
  upgraded node rebinds after its old entry ages out).
- **Legacy beacons** without a key remain address hints (for peers whose key
  is already bound, they must be signed by that key). **Unbound address
  hints are discovery input, not identity:** they expire on the shorter hint
  TTL (`hint_ttl_sec`, default 120 s; bound peers keep the heartbeat
  timeout), are capped (`max_hint_peers`, default 64 — a signed identity
  may displace the oldest hint), and are **never auto-dialed** (HG-S1-7:
  a spoofed unsigned announcement must not turn a node into a dialer).
  Signed beacons bind identities directly; an explicit join by address
  remains available. Quarantined peers are never auto-dialed.

## 4. Join — the signed heartbeat binds identity

1. **Dial.** The joiner opens TCP to the announced address
   (`connect_to_peer`; connections are keyed `remote:<addr>`).
2. **Announce.** The joiner sends `heartbeat` with its `PeerInfo` signed
   by its Ed25519 key (`PeerInfo::signed`): the payload is the canonical
   JSON of the record minus signature and public key; the public key
   travels inside the record.
3. **Bind.** The receiver verifies the signature and binds the public key
   to the peer ID **on first sight** (`discover_verified` after
   `verify_identity`). From then on:
   - a later announcement claiming the same ID with a **different key is
     refused as identity theft**;
   - **freshness + replay (S1 phase 2):** the signed heartbeat is windowed
     to the registry heartbeat timeout (`heartbeat_timeout_sec`, default
     30 s) and replay-cached by `(peer_id, last_seen)`. A stale record is
     refused (`stale heartbeat rejected`); a fresh-verified record is
     bound; a replay inside the window is answered
     `{"status":"ok","replayed":true}` **without** binding or refreshing
     liveness (a captured heartbeat cannot move an address or fake
     presence). **Ordering matters:** the receiver runs `verify_identity`
     (signature), then the check-only binding policy
     (`verify_binding`: key change / quarantine), and only then the replay
     insert — all pre-replay checks are mutation-free, so a forged
     self-signed heartbeat for a bound victim id cannot consume the
     victim's replay slot for that timestamp and suppress its liveness for
     the window. The binding policy is re-applied to a replay as
     defense-in-depth: an identity change or a quarantined peer is refused,
     never acknowledged. `last_seen` is second-resolution, so two
     heartbeats from the same peer in the same second count as one
     observation;
   - **unsigned announcements are address hints for unknown peers only** —
     an unsigned heartbeat for an already-bound peer is refused
     (`unsigned heartbeat rejected`), so it cannot relocate a bound
     identity;
   - a **quarantined** peer's re-registration is refused until released.
4. **Read back.** The joiner's `sangha.mesh.join` response carries the
   remote's registry summary after the bind — the proof the other side
   now knows who you are.

Mesh-wide identity is symmetric: both sides join both ways (organically,
via the auto-join loop on each node's beacons).

## 5. Keys

- `WM_MESH_KEY` (64 hex chars recommended) is **root key material**: since
  9.1.8, purpose-scoped subkeys are derived with HKDF-SHA256
  (`info = "wm/mesh-identity/v1"` for the mesh identity,
  `"wm/record-attestation/v1"` for creation attestations; the release
  manifest reserves `"wm/release-signing/v1"`). The canonical root is the
  hex-decoded key; creation attestations require that canonical form (a
  non-hex key yields a mesh identity only — an honest negative, never an
  off-contract root). Set it for a **stable
  identity across restarts**. Unset → a random per-process key + a loud
  warning (a hardcoded default would be shared by every WhiteMagic node —
  an impersonation primitive, not a convenience).
- **Migration (one release, dual-verify):** the pre-9.1.8 XOR-fold identity
  derivation is still accepted (`MeshKeyPair::accepts_identity`,
  `verify_signature_all_eras`); beacons advertise the derived key. A peer
  that has not upgraded keeps working; a peer that upgrades rebinds after
  its old registry entry ages out (or is re-joined). The legacy arm drops
  in the release after 9.1.8.
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

Signed chat flows over the bound connection: the receiver **requires the
sender to be identity-bound** (no `is_none_or` fallback), verifies the
message signature against the bound key, checks freshness (a message more
than 5 minutes from the receiver's clock is refused `stale chat
rejected`), refuses quarantined senders at ingest (§7), and enforces the
**locally provisioned** `can_execute` authority before the message enters
the channel log. **Unsigned relay over mesh TCP is refused** — there is no
unsigned path on the mesh transport.

**Envelope id (S1 phase 2):** every chat sent by a node carries an
`envelope_id` (sender + millisecond + process sequence) beside the
signature. The field is skipped in serialization when empty, so the
signing payload of an envelope-less message is byte-for-byte the legacy
shape and pre-envelope signatures still verify (**one-way wire note:** an
upgraded receiver accepts old messages unchanged; an old receiver simply
ignores the extra field). The receiver stores a non-empty envelope once
**per `(sender, envelope_id)` pair** and answers a repeat from the *same
sender* with `{"status":"ok","duplicate":true,...}` — the dedup key is
the pair, so one sender cannot predict and occupy a victim's next id to
suppress the victim's genuine message; the sender's flush treats
`duplicate:true` as delivery, so a lost ack plus retry cannot store a
message twice (at-least-once delivery, at-most-once storage). The id is
minted once per logical chat, persisted with the mail-slot entry (a
legacy entry without one mints a fallback at flush and persists it for
retry reuse), and reused across flush retries.

Locks (`acquire_lock`/`release_lock`) are TTL-bounded and per-peer; after
the engagement-token check they gate on the holder's **local authority
grant**, and a quarantined holder is refused outright. A quarantine revokes
the bad apple's locks so the community is never held hostage by its
resources. Signals (`broadcast_signal`) gate on the effective authority of
`signal.source` and refuse a quarantined source.

**Authority is locally provisioned (W1, 2026-09-18):** `PeerAuthority`
inside a heartbeat is **peer-declared** — integrity-protected by the
sender's own signature, but not a boundary. The boundary is this node's
grant table in `<store>/mesh_authority.json` (path override
`WM_MESH_AUTHORITY_FILE`; mode override `WM_MESH_AUTHORITY=enforce|advisory`):

- a bound peer with **no local grant is denied** action-class traffic
  (chat, signals, locks) — *default-deny*. Discovery still works: hints and
  binds are not authority;
- a grant may pin `public_key` (applies only while the bound key matches)
  or omit it (the grant follows the TOFU binding);
- `mode: "advisory"` restores the legacy peer-declared behavior for a
  migration window; it is logged loudly at start and disclosed in
  `/status` under `authority.mode`;
- the file is read at node start (edit + restart to change policy); a
  malformed file **fails closed** (enforce, no grants) with an error log.

Gate errors name the class: `not identity-bound` (no signed heartbeat bound
a key), `not provisioned on this node` (default-deny), or `provisioned
without can_execute authority`. Locks and signals are still
**claimed-identity** checks in one respect — `holder` and `source` are wire
strings, and the gate enforces the *claimed* peer's effective authority;
only an engagement token, when required, cryptographically binds the holder
(token issuer key must equal the holder's bound mesh key). **Signal caveat
(unchanged):** signals carry no signature at all, so `source` is a claim;
the gate does not prove who sent the frame. Hologram sync merges coordinate
entries with importance-wins conflict resolution and is **not yet gated**
(read-class merge, deliberately deferred).

```json
{
  "mode": "enforce",
  "grants": {
    "wm-0a1b2c3d4e5f": {
      "public_key": "…hex…",
      "can_execute": true,
      "can_write_memory": false,
      "can_delegate": false
    }
  }
}
```

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

### S1 mesh phase 2 (2026-09-18)

- **Heartbeat replay + signed-only binding:** `PeerDiscovery::verify_identity`
  is the verification seam; a bound peer's unsigned heartbeat is refused;
  signed heartbeats are freshness-windowed to `heartbeat_timeout_sec` and
  replay-cached by `(peer_id, last_seen)`, with identity + binding verified
  **before** the replay insert (a forgery cannot consume the genuine
  peer's slot). Unit tests:
  `heartbeat_unsigned_for_bound_peer_is_rejected`,
  `heartbeat_replay_is_acknowledged_without_rebinding` (a replay cannot move
  the address), `heartbeat_stale_signed_is_rejected`,
  `signed_heartbeat_identity_rejection_is_labelled`,
  `forged_heartbeat_cannot_consume_bound_victims_replay_slot`.
- **Chat ingest gates:** unsigned chat refused; unbound sender refused as
  `not identity-bound`; signature + bound-key verification; quarantine
  unchanged; `can_execute` authority gate; ±5-minute freshness. Unit tests:
  `chat_unsigned_is_rejected_over_the_mesh_transport`,
  `chat_from_unbound_sender_is_rejected`, `chat_stale_is_rejected`,
  `chat_authority_is_enforced`, `signal_authority_is_enforced`,
  `lock_authority_is_enforced`, `quarantined_holder_cannot_acquire_or_release_locks`,
  `quarantined_source_cannot_broadcast_signals`, and the TCP round-trip
  `e2e_tcp_chat_and_signal` (bind → signed chat → envelope dedup → signal).
- **Envelope dedup:** keyed on `(sender, envelope_id)` — a predicted id
  from a different sender stores both; signing payload unchanged for empty
  ids (legacy signatures verify); `inject_signed` returns
  `Stored`/`Duplicate`; the mail slot persists the id and every flush —
  including the fallback minted for a legacy entry — reuses it; wire ids
  saturate instead of overflowing. Unit tests:
  `empty_envelope_serializes_like_the_legacy_payload`,
  `inject_signed_dedups_by_envelope_id`,
  `inject_signed_dedups_by_sender_and_envelope_id`,
  `envelope_id_roundtrips_and_legacy_entries_default_empty`,
  `set_envelope_persists_fallback_for_retry_reuse`,
  `mail_envelope_id_survives_queue_and_flush`,
  `legacy_mail_entry_reuses_persisted_fallback_envelope_on_retry`,
  `max_wire_id_saturates_instead_of_overflowing`,
  `restore_from_saturates_on_max_wire_id`.
- **Raw-frame E2E (`wm-mcp/tests/mesh_serve_e2e.rs`, unix):**
  `raw_frame_heartbeat_replay_and_chat_dedup` (replay ack, stale refusal,
  unsigned refusal, duplicate:true) and `raw_frame_binding_and_authority_gates`
  (not-bound vs lacks-authority, lock + signal gates) against a real
  `wm serve --mesh` listener over the length-prefixed TCP framing.

### 9.1.8 mesh ingest hardening (2026-09-15)

- **Signed-only discovery:** `PeerAnnounce` carries the signer's public key;
  the signed payload binds it. Unit tests: stale beacon dropped; TOFU binding
  of the announced key; key change for a bound peer refused (address
  unchanged); per-source flood rate-limited; replay of a verified
  `(peer_id, timestamp)` dropped; migration-tolerant verification accepts the
  legacy payload shape.
- **Replay cache:** `ReplayCache` (bounded, windowed) + `IngestGuard`
  (freshness + per-source rate + verified-only replay recording); the
  same-second denial-of-service (forged beacon blocking the genuine one) is
  pinned by test.
- **Key separation:** HKDF-SHA256 with versioned info strings; RFC 5869
  vector test; domain-separation test (`derive(mesh) ≠ derive(attestation)`);
  attestation subkey signs and verifies against its recorded pubkey.
- **No regression:** the existing two-process e2e
  (`mesh_serve_e2e.rs`) passes unchanged; full `wm-sangha` suite green.

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
  signatures (validate-on-dequeue); invalid ones are dropped.
- **Envelope dedup (S1 phase 2):** each queued entry carries the chat's
  `envelope_id` across restarts; the receiver's channel log drops a
  repeated non-empty envelope id (`duplicate:true` in the RPC response,
  which the flush counts as delivered) — so a lost ack plus retry lands
  once. Entries restored from a pre-envelope file have no id and mint a
  fallback at flush time. `sangha.mesh.mail list` discloses each entry's
  `envelope_id`.

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
by design), key management is a shared-secret-free but unmanaged
file/env surface pending B7, and signed chat is freshness-windowed to
±5 minutes with envelope storage dedup keyed on `(sender, envelope_id)`
(S1 phase 2, 9.1.10) — the live replay cache covers **beacon ingest**
(phase 1) and **signed heartbeats** (phase 2; identity + binding before
the replay insert), while chat is covered by freshness plus envelope
dedup rather than a timestamp replay cache. `PeerAuthority` is
peer-declared inside the self-signed `PeerInfo` and is **not an
authorization boundary yet** — local authority provisioning is queued,
and locks/signals are claimed-identity checks in permissive mode (only
engagement tokens, when required, bind the holder cryptographically).
Signals are not signed (source is a claim), hologram sync is not gated,
and only `can_execute` is enforced live (`allowed_tools` /
`can_write_memory` / `can_delegate` remain declarative). Each of these
is a gate on Gate 2 cohort use, not a silent gap.
