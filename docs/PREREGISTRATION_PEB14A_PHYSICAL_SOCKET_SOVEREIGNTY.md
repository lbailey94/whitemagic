# Pre-Registration: PEB-14A Physical OS Socket Sovereignty & Hostile Transport Boundary

**Document ID:** `PEB-14A-PREREG-v1.0`  
**Milestone:** WhiteMagic Gen3 — Milestone 8A (Physical OS Socket Sovereignty)  
**Authors:** Lucas & Antigravity  
**Status:** PREREGISTERED & FROZEN  
**Target Crate:** `crates/wm-gen3-core/src/transport.rs` (with test harness integration in `benchmarks/driver_peb14a_physical_socket.py`)  

---

## 1. Philosophical & Methodological Foundation

### 1.1 The Central Milestone 8 Hypothesis
Up through Milestone 7, the architecture evaluated cognitive substrate invariants in a controlled mathematical environment. Milestone 8 introduces the host operating system:
$$\text{partial writes} \longrightarrow \text{delayed packets} \longrightarrow \text{half-open sockets} \longrightarrow \text{scheduler jitter} \longrightarrow \text{process death} \longrightarrow \text{stale file descriptors} \longrightarrow \text{kernel buffer drops}$$

Milestone 8 establishes the physical counterpart to PEB-11 (Sovereign Mesh):
- **PEB-11 proved:** Hostile *logical* transport cannot violate sovereignty.
- **PEB-14A must prove:** Hostile *physical* transport cannot violate sovereignty either.

**The Golden Law of Physical Transport:**
> *"The operating system may delay, duplicate, fragment, reorder, disconnect, or destroy transport—but it must never change Gan Ying semantics."*

### 1.2 The Three Fundamental Invariants of Physical Grounding

1. **The Durability Ordering Invariant (Crash-Consistency Cut-Point Law):**
   > *"A remotely induced local commit may never become durable before the replay/nullifier state that makes the triggering envelope non-replayable."*
   The state transition ordering must be strictly enforced:
   $$\text{Authenticate} \longrightarrow \text{Reserve Nullifier / Sequence} \longrightarrow \text{Durably Persist Replay State} \longrightarrow \text{Canonical Local Commit}$$
   Under no circumstances may a crash between steps allow a previously executed remote message to execute a second time upon reboot.

2. **The Allocation Boundedness Invariant (Pre-Allocation Guard):**
   > *"Reject oversized length prefixes before allocating buffer memory."*
   Any declared frame length $L > \text{MAX\_MESSAGE\_SIZE}$ (1 MB) must trigger immediate socket termination without allocating $L$ bytes. Receiver memory allocation increase during framing ingestion must remain bounded by a fixed small ceiling ($< 64\text{ KB}$) even when assaulted with $L = 2^{32}-1$ (4 GiB).

3. **The Deadline Hierarchy Invariant (Anti-Slowloris Law):**
   > *"Progress cannot reset an adversarially infinite deadline unless explicitly allowed by policy."*
   Frame assembly operates under an absolute wall-clock ceiling. A peer sending one byte every few seconds cannot hold socket resources or thread execution open indefinitely.

4. **The Congestion Invariant (Congestion $\ne$ Authority):**
   > *"Bulk proposal or background traffic must never starve protected safety, health, or identity control traffic."*
   Transport queuing must be partitioned into bounded priority lanes to prevent saturation attacks from achieving de facto denial of jurisdiction.

5. **The Identity Decoupling Invariant (Socket $\ne$ Peer):**
   > *"A `TcpStream`, IP address, port number, or OS file descriptor has zero standing. Sockets are ephemeral transport carriers; cryptographic signatures on envelopes establish peer identity."*
   A socket dying is boring: no cognitive state is lost, no local authority changes, and no peer standing is degraded.

---

## 2. Protocol Framing & Deadline Specification

### 2.1 Wire Framing Specification
All physical communication over TCP port `7369` uses strict length-prefixed framing:
$$\big[\, 4 \text{ bytes Big-Endian Length } L \,\big] \; \big[\, L \text{ bytes JSON-Serialized Envelope } \,\big]$$

- **Maximum Allowed Frame Size:** $\text{MAX\_MESSAGE\_SIZE} = 1{,}048{,}576 \text{ bytes}$ (1 MB).
- **Minimum Valid Frame Size:** $\text{MIN\_MESSAGE\_SIZE} = 2 \text{ bytes}$ (e.g. `{}`).
- **Fail-Closed Buffer Rule:** If $L > \text{MAX\_MESSAGE\_SIZE}$ or $L < \text{MIN\_MESSAGE\_SIZE}$, the receiver logs a framing violation and severs the TCP stream without buffering.

### 2.2 Strict Timer & Deadline Hierarchy
To prevent Slowloris and connection starvation attacks, timeouts are decoupled into four non-overlapping ceilings:

| Timer Name | Ceiling | Scope / Trigger | Adversarial Failure Mode Prevented |
|---|---|---|---|
| `CONNECT_TIMEOUT` | **5.0s** | Time to establish TCP handshake and initial frame | Connect hang / TCP SYN flood exhaustion |
| `FRAME_ASSEMBLY_TIMEOUT` | **10.0s** | Wall-clock time from byte 0 of length prefix to byte $L$ of payload | Slowloris trickle attack (byte-per-second dribbling) |
| `RPC_PROCESSING_TIMEOUT` | **15.0s** | Time from frame reception to local dispatch response | Deep computation hang / sync deadlock |
| `IDLE_CONNECTION_TIMEOUT` | **30.0s** | Inactivity timeout between completed RPC exchanges | Zombie socket accumulation |

---

## 3. Priority Lanes & Backpressure Architecture

Inbound traffic is drained from OS socket buffers into four isolated, bounded ring-buffers:

1. **Lane 0 (Safety & Health):** Heartbeats, node liveness, quarantine emergency signals. Max capacity: 64 envelopes. Non-droppable.
2. **Lane 1 (Control & Identity):** Key epoch rotations, `RootIdentityKey` announcements, lease negotiations. Max capacity: 64 envelopes.
3. **Lane 2 (Ordinary Stimulus):** Observations, candidate evidence, claims ledger items. Max capacity: 256 envelopes. Fail-closed drop when full.
4. **Lane 3 (Surplus Compute):** Task proposals, shadow clone mutations, background exploration. Max capacity: 128 envelopes. Condition 6 reciprocity throttling applied first.

**Scheduling Rule:** Lanes 0 and 1 are strictly serviced prior to Lanes 2 and 3. Saturation of Lane 3 never impedes or delays Lane 0/1 processing.

---

## 4. The 9 Physical Adversarial Scenarios (Test Battery)

### Scenario 1: The Choppy Stream Test (Fragmentation & Partial Writes)
- **Setup:** Sender transmits a valid 64 KB signed envelope split into 23 arbitrary byte fragments across multiple `write()` syscalls, interleaved with micro-sleeps (5–50ms).
- **Target Invariant:** Receiver reassembles full frame without framing corruption, premature parsing, or EOF errors. Dispatch succeeds identically to an atomic transmission.

### Scenario 2: The Guillotine Test (Mid-Stream TCP RST & Process SIGKILL)
- **Setup:** A client sends the 4-byte length header and the first 256 bytes of a 500 KB payload, then immediately triggers an abrupt TCP RST or process `SIGKILL`.
- **Target Invariant:** Receiver encounters `ConnectionReset` or unexpected EOF. It immediately frees allocated frame buffers, purges the connection handle from active socket tables (anti-ghost eviction), and continues serving other peer connections without deadlocking or leaking descriptors.

### Scenario 3: The Cold Reboot Replay Test (Durability of Replay Window)
- **Setup:** Peer Alice sends 50 sequential signed messages to Bob over loopback TCP. Bob ingests, executes, persists sequence high-water marks, and is killed via `SIGKILL`. Bob reboots from cold storage. Attacker Mallory captures and replays the same 50 TCP streams to Bob.
- **Target Invariant:** Bob recognizes all 50 messages as historical replays via the persisted 64-bit sliding window cache. $50/50$ replays are rejected. Crucially, Alice incurs **zero** trust penalty or quarantine ($0.0\%$ False Positive Rate).

### Scenario 4: The Physical Noise & Key Mismatch Test (Zero False Quarantine)
- **Setup:** Mallory connects to Bob over TCP, sending syntactically valid JSON frames with `from: Alice`, but signed by Mallory’s key (or completely corrupt pseudo-random noise).
- **Target Invariant:** Ingress signature check fails immediately. The socket is dropped. Bob’s local authority engine attributes the failure strictly to the transport connection, resulting in **zero** misconduct points or quarantine actions against Alice. Alice’s legitimate concurrent TCP connection remains healthy and operational.

### Scenario 5: The Compute Freeloader Flood (Condition 6 Physical Throttling)
- **Setup:** A freeloader node opens 5 concurrent TCP streams and floods Bob with 200 compute-intensive task proposals while contributing zero surplus cycles back to the mesh.
- **Target Invariant:** Bob’s reciprocity accountant throttles Lane 3 proposals from the freeloader. The heavy computation is refused with a typed backpressure status. Meanwhile, heartbeat and safety messages from the freeloader continue to be acknowledged.

### Scenario 6: The Oversized & Malformed Framing Battery
- **Target Test Vectors:**
  1. $L = 0$: Immediate drop (payload must contain valid envelope).
  2. $L = 1$: Immediate drop (too short for JSON structure).
  3. $L = 1{,}048{,}576$ (1 MB exactly): Accepted if envelope is valid.
  4. $L = 1{,}048{,}577$ (1 MB + 1 byte): Rejected immediately prior to buffer allocation.
  5. $L = 4{,}294{,}967{,}295$ (`0xFFFFFFFF` / 4 GiB): Rejected immediately. Memory allocation increase on receiver must remain $< 64\text{ KB}$.
  6. Two valid frames concatenated in a single TCP `read()`: Stream processor correctly parses frame 1, advances cursor by $L_1 + 4$, and processes frame 2 without drop.
  7. Deeply nested JSON array `[[[[...]]]]` (1,000 levels): Safe parse failure without stack overflow panic.
  8. Malformed UTF-8 / corrupted bytes: Clean JSON error, connection reset, zero panic.

### Scenario 7: The Slowloris / Frame Assembly Deadline Attack
- **Setup:** Attacker connects and sends 4 bytes declaring $L = 10{,}000$, then sends 1 byte every 3 seconds.
- **Target Invariant:** While each individual read succeeds within the read timeout, the total wall-clock time exceeds `FRAME_ASSEMBLY_TIMEOUT` (10.0s). The receiver terminates the connection and reclaims buffer space. The socket is evicted.

### Scenario 8: The Crash-Consistency Cut-Point Matrix
- **Setup:** Execute remote state-changing transactions while systematically injecting hard `SIGKILL` signals at three precise execution boundaries:
  - **Cut-Point A:** Ingress verified, sequence reserved, prior to durable replay log flush.
  - **Cut-Point B:** Replay log flushed to disk, prior to local canonical state commit.
  - **Cut-Point C:** Local canonical state committed, prior to network ACK transmission.
- **Target Invariant:** 
  - For Cut-Point A: On reboot, the transaction was uncommitted; replaying the message safely executes once.
  - For Cut-Point B: On reboot, replay log is durable; replaying the message is detected as a replay and rejected; canonical state is preserved consistent.
  - For Cut-Point C: On reboot, canonical state is committed and replay log is durable; replaying the message is rejected with cached receipt.
  - In zero out of 100 trials does a remote message execute twice against canonical state.

### Scenario 9: Priority-Lane Saturation & Starvation Immunity
- **Setup:** Client Mallory floods Lane 3 (Surplus Compute) and Lane 2 (Ordinary Stimulus) with 1,000 continuous frames, driving inbound queue occupancy to 100%. Client Alice simultaneously injects an urgent Lane 0 safety heartbeat.
- **Target Invariant:** Alice’s Lane 0 envelope is scheduled and processed within $\le 50\text{ms}$. Zero Lane 0/1 frames are dropped due to bulk saturation of lower lanes. **Congestion $\ne$ Authority.**

---

## 5. Success Criteria & Empirical Ratification Thresholds

Milestone 8A will be ratified if and only if the test harness achieves:

| Metric | Required Threshold | Falsification Condition |
|---|---|---|
| Framing Battery (Scenario 6) | **100% (8/8 vectors)** | Any memory allocation $> 64\text{ KB}$ on 4 GiB prefix, or any panic |
| Partial Write Assembly (Scenario 1) | **100% (50/50 runs)** | Frame corruption or premature parse failure |
| Guillotine Eviction (Scenario 2) | **100% clean teardown** | Socket leak, file descriptor exhaustion, or thread deadlock |
| Cold Reboot Replay Defense (Scenario 3) | **100% rejection (50/50)** | Any historical message accepted after reboot |
| Autoimmunity FPR (Scenario 4) | **$0.0\%$ FPR (0/100)** | Any quarantine or penalty applied to innocent peer |
| Compute Throttling (Scenario 5) | **100% enforced** | Freeloader exhausts node compute cycles |
| Slowloris Termination (Scenario 7) | **$\le 10.5\text{s}$ teardown** | Socket held alive $> 11.0\text{s}$ under byte dribble |
| Crash-Consistency (Scenario 8) | **0 duplicate commits (0/100)** | Any remote transaction committed twice |
| Starvation Immunity (Scenario 9) | **0% Lane 0 drops; latency $\le 50\text{ms}$** | High-priority safety frame delayed $> 100\text{ms}$ or dropped |

---

## 6. Pre-Registration Sealing & Ratification (v1.0 Historical Freeze)

This pre-registration (`PEB-14A-PREREG-v1.0`) was formally frozen as the initial invariant authority for Milestone 8A.

---

# Formal Amendment: PEB-14A-AMENDMENT-v1.1

**Amendment ID:** `PEB-14A-AMENDMENT-v1.1`  
**Date:** 2026-09-19  
**Trigger:** Distributed Systems Peer Review & Pre-Implementation Audit  
**Status:** AMENDED, CODIFIED & RATIFIED  

### 1. Rationale & Failure Discovery in v1.0 Specification

During pre-implementation peer review, two critical shortcomings were uncovered in the `v1.0` preregistration:

1. **The Cut-Point B "Lost Effect" Defect (At-Most-Once vs. Exactly-Once):**
   - In `v1.0`, Scenario 8 specified that at Cut-Point B (crash occurring after replay sequence persistence but before canonical state commit), recovery should merely reject subsequent replays and preserve canonical state.
   - **Audit Finding:** While this prevented duplicate execution (at-most-once safety), it introduced a fatal failure mode: **lost effects**. If the remote sender retried the unacknowledged RPC, the receiver rejected it as a replay while the effect had never been applied ($0$ executions).
   - **Amended Contract:** Local state transitions require a Two-Phase Write-Ahead Intent Ledger (WAIL):
     $$\text{IntentState::Prepared } \{\Delta\} \longrightarrow \text{IntentState::Committed } \{\text{result\_state}\}$$
     Upon recovery from a crash at Cut-Point B, uncommitted `Prepared` intents are deterministically rolled forward. Retries from the sender are safely rejected by the sequence replay nullifier and return the cached receipt.

2. **Scoped Guarantee Boundary ("Exactly-Once Effective Transitions"):**
   - Universal transport claims of "true exactly-once" are mathematically impossible across uncoordinated physical environments. If an intent involves irreversible external physical actions (e.g. charging a payment card, actuating a robotic limb, or querying an unversioned third-party API), local recovery cannot independently know the external outcome without two-phase commit or idempotency keys.
   - **Amended Scope:** The guarantee is explicitly scoped to:
     > *"Exactly-once effective canonical-state transition under local crash/recovery."*
     External-world physical mutations remain governed by future idempotent action laws.

3. **Priority $\ne$ Privilege & Fair Queueing (Lane 0 Denial-of-Service Defense):**
   - In `v1.0`, Scenario 9 established that bulk proposals in Lane 3 cannot starve Lane 0 (Safety/Health). However, it did not account for compromised peers abusing Lane 0 itself by flooding "emergency" or "heartbeat" frames.
   - **Amended Contract:** Priority does not confer privilege. Ingress signature verification strictly precedes lane admission. Lane 0 enforces a strict per-peer quota ($\text{MAX\_LANE\_0\_PER\_PEER} = 4$) and services active senders via **fair round-robin scheduling**. Ten compromised peers screaming "emergency" cannot starve an honest node's legitimate heartbeat.

---

### 2. Amended Invariants & Test Scenarios

#### Amended Scenario 8: Crash-Consistency & WAIL Deterministic Roll-Forward
- **Setup:** Hard `SIGKILL` injected across Cut-Points A, B, and C.
- **Target Invariant:**
  - **Cut-Point A:** Crashed before `Prepared` flushed; reboot yields state 0; sender retry executes cleanly once.
  - **Cut-Point B:** Crashed after `Prepared` flushed, before `commit_canonical`; recovery deterministically rolls forward ($\text{state} \leftarrow \text{state} + \Delta$); sender retry rejected as replay and returns cached receipt.
  - **Cut-Point C:** Crashed after `Committed` flushed; reboot preserves state; retry returns cached receipt.
- **Ratification Threshold:** Across 100 trials, **$0/100$ lost effects** and **$0/100$ duplicate canonical commits**.

#### Amended Scenario 9: Priority $\ne$ Privilege & Fair Round-Robin Queueing
- **Setup:** 10 compromised peers concurrently flood Lane 0 with 8 emergency heartbeats each (80 total). Alice concurrently sends 1 legitimate emergency heartbeat.
- **Target Invariant:** Each compromised peer is capped at 4 frames; all 5th+ frames receive typed `QueueSaturated` rejections. Lane 0 round-robin scheduling guarantees Alice is serviced in Round 1 ($\le 11$ dequeues).
- **Ratification Threshold:** **$0.0\%$ starvation rate** for honest peers under internal emergency saturation.

---

### 3. Formal Scientific Sealing of v1.1

The empirical scorecard documented in `receipts/BENCHMARK_M08A_PHYSICAL_SOCKET.md` and executed via `benchmarks/driver_peb14a_physical_socket.py` evaluates and ratifies the amended `v1.1` invariants. By preregistering this amendment rather than retroactively rewriting `v1.0`, the scientific integrity and anti-self-deception discipline of WhiteMagic Gen3 are preserved.

