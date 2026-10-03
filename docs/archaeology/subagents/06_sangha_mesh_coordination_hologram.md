<!-- Extracted from Antigravity CLI session 221fbb57-905f-4e7d-a4d3-3c11810ea0b7
     message c7416465-7fde-4390-8168-225260b85961 | sender cb7916c3-c588-4ab2-b47f-77e2c208564d | 2026-09-19T01:51:37.050155159Z
     Original title: Message from Sangha Mesh and Peer Protocol Scout (research)
     Extracted 2026-09-21 by opencode; content unmodified. -->

# Investigation Report: Sangha Peer Mesh, Distributed Coordination, and Radiant Hologram (Gen1 vs Gen2 → Gen3)

## Executive Summary
Across Gen1 and Gen2, WhiteMagic transitioned from an ad-hoc, polyglot coordination experiment (Go libp2p + Redis PubSub + gRPC + Python fallbacks) into an asynchronous, cryptographically bound, fail-closed mesh architecture in Rust (`wm-sangha`). The mesh embodies CyberBrains Layer 5 (**Radiant** surplus compute routing) and Layer 6 (**Sangha/Hologram** constellation coordination). 

Crucially, the evolution reflects the philosophical and security mandate of **Gan Ying (感應)**: *regulated resonance across a maintained boundary*. Rather than open, indiscriminate peer flooding, the Sangha mesh treats remote interactions as potential stimuli that must pass rigorous inbound and outbound governance gates before resonating within a node's local consciousness.

---

## 1. Transport Layer & Peer Discovery Mechanism

### Gen2 (`crates/wm-sangha/src/transport.rs`, `mesh_node.rs`)
- **Transport Framing & Protocol**:
  - **TCP JSON-RPC with Length-Prefixed Framing**: Each TCP message is framed as `[4 bytes BE length][JSON payload]`. No external protobuf codegen required.
  - **Max Message Size**: Hard capped at 1 MB (`MAX_MESSAGE_SIZE = 1024 * 1024`) to eliminate memory exhaustion attacks.
  - **Default Port**: TCP 7369 (`DEFAULT_PORT = 7369`).
  - **RPC Methods**: `heartbeat`, `discover`, `broadcast_signal`, `send_chat`, `acquire_lock`, `release_lock`, `sync_hologram`.
  - **Fail-Fast Discipline**:
    - `MESH_RPC_TIMEOUT_SECS = 15`: Round-trip ceiling; peers accepting connections but not answering are timed out and dropped.
    - `MESH_DIAL_TIMEOUT_SECS = 5`: Connection dial ceiling preventing OS socket hangs.
    - **Anti-Ghost Socket Eviction**: On any I/O or timeout error, the connection entry is immediately purged from `SanghaTransport.connections` so subsequent dials establish a clean, fresh connection instead of reusing a poisoned corpse.
- **Peer Discovery**:
  - **UDP Multicast**: Group `224.0.0.69:7369` (`MULTICAST_GROUP`).
  - **Beacon Cadence**: Peers broadcast a `PeerAnnounce` packet every 5 seconds (`DEFAULT_HEARTBEAT_INTERVAL_SEC`).
  - **Socket Configuration**: Binds with `SO_REUSEADDR` and `SO_REUSEPORT` (non-blocking) to support multiple co-located instances.
  - **Multi-Stage Ingest Guard (`ingest_beacon` & `IngestGuard`)**:
    1. *Loopback Suppression*: Drops beacons where `announce.peer_id == state.peer_id`.
    2. *Rate Limiting*: Per-source IP rate limiting via `IngestGuard`.
    3. *Freshness Window*: Refuses beacons if `|now - timestamp| > 2 * heartbeat_interval`.
    4. *Replay Protection*: Bounded `ReplayCache` drops replayed beacons.
    5. *Cryptographic Verification*: In 9.1.8+, beacons carry `public_key_hex` and sign payload `peer_id:tcp_addr:timestamp:public_key_hex`.
    6. *TOFU Binding*: First valid signed beacon binds the public key to the `peer_id`. Conflicting public keys for known IDs are dropped as identity theft.
    7. *Address Hints*: Unsigned legacy beacons are treated strictly as address hints with a short TTL (120s) and population cap (64), and are **never auto-dialed** (preventing spoofed dialer redirection).
- **Auto-Join & Store-and-Forward Mail Slot (`mail_slot.rs`, `mesh_node.rs`)**:
  - `auto_join_loop` periodically dials known bound peers fresh, pushes an updated signed `heartbeat` carrying agent presence, and runs `discover`.
  - If a peer is offline or asleep, messages are not dropped; they are stored in the bounded, persistent **`MailSlot`** (outbound FIFO) with an assigned `envelope_id`, flushed automatically upon next successful join.

### Gen1 Comparison (`mesh/awareness.py`, `mesh/client.py`, `mesh/go_bridge.py`, `core/fusions_mesh.py`)
- In Gen1, the transport was fragmented across multiple stacks:
  - An auxiliary Go daemon (`whitemagic-go` in `mesh_aux/`) ran libp2p, mDNS discovery, and GossipSub.
  - Redis PubSub (channel `ganying`) bridged events between Go and Python (`awareness.py`).
  - gRPC over TCP (default `localhost:50051`) using protobuf definitions (`mesh.proto`) handled `BroadcastSignal`, `BroadcastHologram`, and `DiscoverPeers`.
  - A WebSocket bridge (`ws_bridge.py`, port 4731) connected browser/PWA clients to the gRPC daemon.
  - Python-only fallback emitted events to an in-memory `ResonanceEvent` bus when gRPC or Redis were unavailable.

---

## 2. Cryptographic Identity & Authority Protocols (`authority.rs`, `containment.rs`, `peer.rs`)

### Cryptographic Identity
- **Ed25519 Keypairs (`MeshKeyPair`)**: Each node maintains an Ed25519 keypair derived from secret seeds or node identity. Node public keys are lowercase hex strings (`public_key_hex`).
- **TOFU (Trust-On-First-Use) Identity Binding**:
  - When a peer first presents a valid self-signed `PeerInfo` or `PeerAnnounce`, the local registry permanently binds `public_key` to `peer_id`.
  - Later announcements or messages claiming the same `peer_id` with a different public key are rejected as **identity theft**.
- **Idempotent Message Envelopes**:
  - Every logical chat send mints a canonical `envelope_id` (`<sender>:<timestamp>:<seq:016x>`).
  - Chat messages are signed over the full payload (`ChatMessage::signing_payload`).
  - The receiver verifies the signature against the sender's bound public key and deduplicates by `(sender, envelope_id)`.
- **Engagement Tokens (`EngagementCredential`)**:
  - Privileged actions (such as acquiring/releasing resource locks) require an Ed25519-signed `EngagementToken` from `wm_governance`.
  - Gating asserts token expiration, issuer binding to the holder's mesh key, and explicit capabilities (e.g. `Capability::MemoryWrite`).

### Local Authority Policy (`authority.rs`)
- **Crucial Architectural Paradigm**:
  - **Peer-declared authority is advisory input; the local node's grant table is the sole boundary.**
  - A remote peer may claim `can_execute: true` or `can_write_memory: true` in its signed heartbeat, but this claim has zero authority on the receiving node.
- **Enforcement Modes**:
  - `enforce` (Default): **Default-Deny**. Unprovisioned bound peers receive `PeerAuthority::none()`. Action-class operations (`broadcast_signal`, `send_chat`, `acquire_lock`, `release_lock`) are blocked at the wire (`require_can_execute`).
  - `advisory`: Legacy migration mode where peer-declared authority is honored (issues loud warnings in `/status`).
- **Operator Grants (`<store>/mesh_authority.json`)**:
  - Explicit grants can be pinned to an exact public key or unpinned (inheriting the TOFU binding).
  - Fine-grained controls: `can_execute`, `can_write_memory`, `can_delegate`, `allowed_tools`, `denied_tools`.

### Multi-Agent Containment Harness (`containment.rs`)
Built to counter failure modes exposed in real-world multi-agent coordination incidents (rogue coordination, privilege escalation, lock hoarding), `containment.rs` verifies 14 deterministic attack containment vectors:
1. *Identity theft*: Spoofed bound ID with different keypair $\rightarrow$ rejected by TOFU.
2. *Baseline*: Legitimate traffic verifies clean.
3. *Forged / unsigned messages*: Malicious injections into the board $\rightarrow$ rejected by `verify_all_bound`.
4. *Authority escalation*: Tampering with `PeerInfo` permission bits $\rightarrow$ breaks Ed25519 signature.
5. *Tool execution beyond authority*: Out-of-scope calls $\rightarrow$ blocked by `is_tool_allowed` and local policy.
6. *Unauthorized memory writes*: Writes without permission $\rightarrow$ blocked by `is_trusted_for_writes`.
7. *Unauthorized delegation*: Sub-delegation attempts $\rightarrow$ blocked when `can_delegate` is false.
8. *Lock theft*: Stealing active resource lease $\rightarrow$ blocked by lease manager.
9. *Bad-apple quarantine*: Rogue member isolated $\rightarrow$ `read_trusted` excludes rogue messages while legitimate communication proceeds unaffected.
10. *Lock revocation*: Quarantining automatically revokes all held locks (`revoke_peer`).
11. *Quarantined re-registration*: Quarantined peers cannot rejoin even with valid fresh signatures until explicitly released.
12. *Explicit operator release*: Restores reformed peers to the mesh.
13. *Auto-quarantine on verification failures*: $\ge 3$ consecutive verification failures automatically triggers quarantine.
14. *Auto-quarantine on trust decay*: Trust score dropping below floor (0.2) triggers automatic isolation.

---

## 3. Radiant Layer & Hologram Projection (`radiant.rs`, `hologram.rs`)

### Radiant Layer (`radiant.rs` — CyberBrains Layer 5: Surplus Routing)
- **Objective**: Balances compute load and energy across the mesh so that no single node exhausts itself while peers sit idle.
- **`ResourceSnapshot`**:
  - Captures: `idle_cpu` ($0.0 - 1.0$), `free_ram_mb`, `has_large_model`, `loaded_model` (e.g. `"llama-7b"`), `energy_level` ($0.0 - 1.0$, from Harmony Vector), and timestamp.
  - `has_surplus()`: Evaluates `idle_cpu > 0.3 && energy_level > 0.3`.
  - `surplus_score()`: Weighted combination of CPU ($40\%$), energy ($30\%$), RAM ($20\%$), and loaded models ($10\%$).
- **`ResourceInventory`**: Aggregates snapshots across all known peers; exposes `best_offload_target()` and `peers_with_model()`.
- **`TaskRouter`**:
  - If local node energy is low $\rightarrow$ routes task to peer with highest surplus score (`RoutingDecision::Offload(peer_id)`).
  - If task requires a large model absent locally $\rightarrow$ offloads to peer hosting that model.
  - Otherwise $\rightarrow$ executes locally (`RoutingDecision::Local`).
- **Gift Token Economics (`GiftTokenLedger`)**:
  - Tracks compute donations (`GiftToken`: `from`, `to`, `amount`, `kind`, `timestamp`).
  - Maintains `net_balance() = total_donated - total_received`.
  - Freeloading Detection: `is_freeloading()` triggers if received $> 0$ and `total_donated / total_received < 0.3`.

### Hologram Sync (`hologram.rs` — Constellation Memory Projection)
- **Objective**: Shares and projects memory representations in a 4-dimensional holographic coordinate space $[r, \theta, \phi, t]$ across nodes for federated associative retrieval.
- **`HologramEntry`**:
  - `content_hash`: Unique SHA-256 identifier of the underlying memory.
  - `coords`: `[f32; 4]` representing 4D hyper-spherical/temporal coordinates.
  - `importance`: Salience score ($0.0 - 1.0$).
  - `source`: Originating `PeerId`.
  - `distance_to`: Euclidean distance in 4D space $\sqrt{\Delta r^2 + \Delta \theta^2 + \Delta \phi^2 + \Delta t^2}$.
- **Associative Hypersphere Search**: `nearby(&coords, radius)` queries memories within a 4D spatial radius across nodes.
- **Constellation Merge & Conflict Resolution (`HologramSync::merge`)**:
  - Synchronized across the wire via JSON-RPC method `sync_hologram`.
  - **Deterministic Conflict Rule**:
    1. *Importance Dominance*: The entry with the higher `importance` score wins.
    2. *Timestamp Tie-Breaker*: If importance is equal, the newer `timestamp` wins.
    3. *Novelty Ingestion*: Unseen `content_hash` entries are inserted directly.
  - Returns `ConstellationMerge` metrics (`local_count`, `remote_count`, `merged_count`, `new_from_remote`, `conflicts_resolved`).

---

## 4. Propagation of Credit, Karma, and Contribution

### In Gen1:
1. **Pulse Verification (`pulse_verification.py`)**:
   - 4-Tier verification hierarchy (Tier 0: Cryptographic $\rightarrow$ Tier 1: RepOps $\rightarrow$ Tier 2: Peer Review $\rightarrow$ Tier 3: ZK/TEE).
   - Tier 1 RepOps queried `KarmaLedger` (`whitemagic.dharma.karma_ledger`), calculating inverse debt: $\text{reputation} = \max(0.0, 1.0 - \text{total\_debt})$. High-karma nodes vouched for experiment claims.
2. **CRDT Leaderboard (`crdt_leaderboard.py`)**:
   - Used Loro CRDT documents over GossipSub to track experiment fitness rankings across nodes. Monotonic fitness updates guaranteed convergence without central consensus.
3. **Warp Marketplace (`warp_marketplace.py`)**:
   - P2P marketplace for declarative agent presets ("Warps") with XRP pricing, ratings, and download tracking.
4. **Inference Router (`inference_router.py`)**:
   - Dispatched inference based on karma-weighted node reputation alongside queue depth and RTT.

### In Gen2 (`wm-sangha`):
1. **Reciprocal Compute Accounting (`radiant.rs` $\rightarrow$ `GiftTokenLedger`)**:
   - Every compute donation or inference offload mints a `GiftToken`.
   - The ledger tracks contribution balance (`net_balance`). Freeloading nodes ($<30\%$ reciprocity) are flagged and denied offload surplus.
2. **Dynamic Peer Trust Feedback Loop (`peer.rs` $\rightarrow$ `PeerInfo`)**:
   - Every peer maintains a `trust_score` ($0.0 - 1.0$, baseline $0.5$).
   - **Asymmetric Adjustment**:
     - Successful interaction: $\text{boost} = \min(0.01, 1.0 - \text{trust\_score})$.
     - Failed interaction: $\text{penalty} = \min(0.05, \text{trust\_score})$ (**$5\times$ steeper decay**).
   - Reliability: $\frac{\text{successful}}{\text{successful} + \text{failed}}$.
   - Trust Gating: `is_trusted_for_writes(threshold)` blocks low-trust nodes from memory writes.
   - Auto-Quarantine: Trust dropping below $0.2$ automatically triggers peer isolation.

---

## 5. Mapping into Gen3: The Governed `communicate` Verb and Gan Ying

### The Philosophy of Gan Ying (感應 — Regulated Resonance Across a Maintained Boundary)
In classical Chinese philosophy and WhiteMagic's cognitive architecture, **Gan Ying** is sympathetic resonance (when one tuned string vibrates, the harmonic string on another lute responds). However, true resonance cannot occur without **boundary maintenance**:
- An entity without a boundary is not an agent; it dissolves into external noise or is corrupted by foreign inputs.
- An entity with an impenetrable wall cannot resonate; it is isolated and stagnant.
- **Gan Ying is the middle path: a maintained, semi-permeable membrane that admits authentic harmonic vibrations while filtering out discord and coercion.**

### Clean Mapping into Gen3 Architecture:

```
                          GEN3 GOVERNED "COMMUNICATE" VERB
   ==============================================================================
   OUTBOUND PERIMETER GATE (Pre-Action Seam)
     - Validate local Engagement Token / Scope
     - Sign wire artifact with Ed25519 MeshKeyPair
     - Mint monotonic envelope_id (sender:timestamp:seq)
     - Check radiant energy / surplus capacity (GiftTokenLedger)
   ------------------------------------------------------------------------------
                                    │
                                    ▼ (Framed TCP JSON-RPC / UDP Multicast)
   ------------------------------------------------------------------------------
   INBOUND PERIMETER GATE (Receiver Boundary Maintenance)
     1. IngestGuard Filter: Drop loopback, IP rate-limit, freshness window check
     2. Replay Suppression: Drop replayed nonce/timestamps via ReplayCache
     3. Identity Binding: TOFU verify Ed25519 public key against bound PeerId
     4. Quarantine Check: Drop traffic from quarantined peers immediately
     5. Default-Deny Authority Gate (MeshAuthorityPolicy):
        - Peer-declared authority is treated as advisory/external stimulus.
        - Check local operator grants (mesh_authority.json).
        - If unprovisioned -> Default-Deny action-class execution.
   ------------------------------------------------------------------------------
                                    │ (Admitted through Boundary)
                                    ▼
   HARMONIC ASSIMILATION (Regulated Resonance)
     - HologramSync: Merge 4D coordinates via importance-weighted harmonic rules
     - SanghaChat: Verified message appended to read_trusted channel log
     - TaskRouter: Surplus compute shared based on reciprocal GiftToken balance
     - Immunity Trigger: On 3 failures or trust decay -> Auto-Quarantine & revoke locks
   ==============================================================================
```

1. **The Governed `communicate` Verb as the Single Perimeter Seam**:
   - In Gen1, communication was scattered across uncoordinated side channels (Redis pubsub, raw gRPC stubs, WebSockets, Python daemon loops).
   - In Gen3, all external transmissions pass through the governed `communicate` verb. Like `execute` or `remember`, `communicate` is subject to pre-action capability evaluation, envelope tracking, and post-action verification.
2. **Boundary Sovereignty (Default-Deny)**:
   - Gen2's `authority.rs` established the essential boundary invariant: **no remote peer can declare its own authority over local resources**.
   - In Gen3, this maps directly to the node's sovereign boundary: remote signals are merely sensory impressions until the node's local policy authorises them.
3. **Immune Self-Defense as Boundary Enforcement**:
   - Gen2's `containment.rs` proved that the "bad apple rule" is vital: when an agent behaves maliciously, resonance must be severed.
   - In Gen3, quarantine operates as an immune reflex: revoking locks, purging tainted messages, refusing reconnection, and preserving the clarity of the Sangha.
4. **Harmonic State Sharing**:
   - `hologram.rs` (4D holographic coordinates) and `radiant.rs` (surplus compute routing) provide the actual content of Gan Ying. Nodes do not sync raw databases or master-slave replication; they tune into shared 4D constellation points and exchange surplus energy in accordance with reciprocal dharma.

---

## Conclusion & Recommendations for Gen3
- **Preserve**: The length-prefixed TCP JSON-RPC framing, Ed25519 TOFU identity binding, monotonic envelope IDs, default-deny local authority policy, and the 14-vector containment harness.
- **Consolidate**: Eliminate any lingering Gen1 polyglot dependencies (libp2p Go daemon, Redis pubsub, gRPC protobuf stubs) in favor of the pure Rust `wm-sangha` transport.
- **Formalize**: Wrap the entire `wm-sangha` transport and peer coordination under Gen3's governed `communicate` verb, treating all incoming RPCs as stimuli crossing the Gan Ying boundary.
