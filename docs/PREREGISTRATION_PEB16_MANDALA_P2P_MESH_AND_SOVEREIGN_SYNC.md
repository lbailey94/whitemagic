# Pre-Registration: PEB-16 Mandala P2P Mesh & Sovereign Synchronization

**Document ID:** `PEB-16-PREREG-v1.0`  
**Milestone:** WhiteMagic Gen3 — Milestone 10 (Mandala P2P Mesh & Sovereign Synchronization)  
**Public Release Target:** `v10.0.0-alpha.2` (Internal Codename: `Milestone 10`)  
**Authors:** Lucas & Antigravity (with Sangha Peer Review)  
**Status:** PREREGISTERED & FROZEN  
**Target Modules:** `crates/wm-gen3-core/src/mesh.rs`, `crates/wm-gen3-core/src/transport.rs`, and `crates/wm-gen3-harness/src/bin/wm.rs`  

---

## 1. Philosophical & Methodological Foundation

### 1.1 The Decentralized Inflection Point
Milestones 0 through 9 established the single-node sovereign substrate:
* **Milestone 9 Gate 9A–9D:** Zero-DAG compilation, verified sweep transactions, Gana transform policies, conformal forgotten diamonds, cut-point crash consistency (CP1–CP5), forensic quarantine isolation, and high-volume sovereign migration.
* **Scale Validation:** Verified 10,356 memories consolidated in 40 MB disk space, 5,318 dedup/sec, sub-millisecond core query latency, and 100% byte integrity across NVMe and SD Card stores.

Milestone 10 answers the distributed architectural question:
> *"How do multiple sovereign WhiteMagic instances (laptop, desktop, phone, server, or offline media) synchronize memories without centralized coordination, cloud vector silos, or loss of local jurisdiction?"*

### 1.2 The Core Invariants of Sovereign P2P Synchronization

```
================================================================================
                    THE SOVEREIGN P2P MESH INVARIANTS
================================================================================
1. Zero-Bypass Remote Ingress:
   Remote sync data enters strictly as `RemoteStimulus`. A remote peer CANNOT
   directly execute writes or issue a local `CommitCapability`.
   All remote records pass through local pulse compilation and deduplication.

2. Physical Socket Decoupling:
   IP addresses, TCP connections, and socket file descriptors carry ZERO standing.
   Peer identity is established exclusively by Ed25519 root public keys via TOFU.

3. Ancestry Over Chronology:
   Wall-clock timestamps carry ZERO causal authority.
   Divergence and reconciliation are governed strictly by Merkle causal ancestry
   and monotonic epoch progression.

4. Partition-Healing Dual-Preservation:
   When two nodes evolve independently during a network partition ($A \parallel B$),
   neither node's history is rewritten or discarded. State deltas are merged
   idempotently, preserving both provenance lineages.

5. Sneakernet Portability (Air-Gapped Sovereignty):
   P2P synchronization must operate identically over live TCP sockets (port 7369)
   or offline signed sync bundles (`.wmpack`) transferred via SD cards or USB.
================================================================================
```

---

## 2. Wire Protocol & Sync State Machine

### 2.1 Protocol Framing (`mandala.mesh.v1`)
All mesh communication runs on the length-prefixed framing established in PEB-14A:
$$\big[\, 4 \text{ bytes Big-Endian Length } L \,\big] \; \big[\, L \text{ bytes JSON Envelope } \,\big]$$

### 2.2 Core Message Actions
1. **`mesh.ping` / `mesh.pong`:** Node liveness, round-trip latency, and health telemetry.
2. **`mesh.handshake`:** Mutual exchange of:
   * `node_id`: Human/agent-readable node identifier (e.g. `laptop-alpha`, `phone-pixel`).
   * `public_key`: 32-byte Ed25519 verifying key.
   * `epoch`: Current local store epoch.
   * `record_count`: Number of active records in local substrate.
   * `head_hash`: SHA-256 digest of the latest committed state.
   * `capabilities`: Declared `NodeCapabilities` (Tier, protocol version).
3. **`mesh.sync_request`:** Request for records where `epoch > last_seen_epoch` (or since a specific head hash).
4. **`mesh.sync_response`:** Batch of signed `SyncRecord` objects containing:
   * `record_id`: Record index.
   * `content`: Text payload.
   * `source`: Provenance attribution.
   * `kind`: Epistemic kind (`reported`, `system`, `simulated`).
   * `sha256`: Cryptographic content digest.
   * `epoch`: Epoch at which the record was committed on authoring node.
5. **`mesh.gossip_record`:** Proactive push of a newly recorded memory to connected peers for near-realtime cross-agent awareness.

---

## 3. Sneakernet Offline Sync Bundles (`.wmpack`)

For air-gapped or intermittently connected nodes (such as SD card `/media/lucas/SD_CARD1`):
* **Export:** `wm mesh export --out <path.wmpack> [--since-epoch <N>]`
  * Emits a self-contained bundle containing:
    * `header`: Format version (`WM-PACK-v1`), timestamp, author node ID, author public key.
    * `epoch_range`: `[from_epoch, to_epoch]`.
    * `records`: Array of canonical records.
    * `merkle_root`: Merkle root of all included record digests.
    * `signature`: Ed25519 signature by author node over the bundle header and Merkle root.
* **Import:** `wm mesh import --in <path.wmpack>`
  * Verifies signature and integrity against known peer public keys (or prompts TOFU registration).
  * Executes atomic deduplication and pulse commit into the local SubstrateStore.
  * Emits a signed `BundleImportReceipt`.

---

## 4. Formal Acceptance Hypotheses

| Hypothesis | Condition | Target Metric | Falsification Threshold |
|---|---|---|---|
| **H10-1: Live P2P Handshake & Ping** | Two nodes over loopback TCP | Authenticated handshake + round-trip ping | Unauthenticated handshake admitted or ping failure |
| **H10-2: Delta Sync Fidelity** | Node B syncs delta from Node A | 100% of Node A's new records present in Node B | Any record missing or corrupted |
| **H10-3: Strict Idempotent Deduplication** | Re-syncing identical store | 0 new records written, 0 epoch advance | Any ghost write or epoch increment |
| **H10-4: Air-Gapped Sneakernet Bundle** | Export to `.wmpack` and import into cold store | 100% byte fidelity, valid Ed25519 verification | Corrupted bundle accepted or valid bundle rejected |
| **H10-5: Tamper Defense** | Injected bitflip in `.wmpack` | Fail-closed rejection before store mutation | Any mutation occurs on tampered bundle |
| **H10-6: Non-Bypassable Local Authority** | Malicious peer sends malformed/unearned claims | Local pulse compiler filters noise, preserves local law | Remote peer forces state mutation |
