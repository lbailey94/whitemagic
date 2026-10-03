# Pre-Registration: PEB-14C Heterogeneous Multi-Node Sangha & Radiant Hologram

**Document ID:** `PEB-14C-PREREG-v1.0`  
**Milestone:** WhiteMagic Gen3 — Milestone 8C (Heterogeneous Multi-Node Sangha & Radiant Hologram)  
**Authors:** Lucas & Antigravity  
**Status:** PREREGISTERED & FROZEN  
**Target Crate:** `crates/wm-gen3-core/src/hologram.rs` (with test harness integration in `benchmarks/driver_peb14c_hologram.py`)  

---

## 1. Philosophical & Methodological Foundation

### 1.1 The Central Milestone 8C Hypothesis
Milestones 8A and 8B proved that physical transport failures and relativistic spacetime (bad clocks, asymmetric partitions) cannot change Gan Ying semantics.

Milestone 8C tackles the final physical reality of decentralized cognition: **radically heterogeneous hardware, derived associative projection, and sustained operational lifecycles**:
$$\text{desktops (2ms)} \longleftrightarrow \text{edge devices (300ms)} \longleftrightarrow \text{DHCP IP rebinding} \longleftrightarrow \text{sleep/wake cycles} \longleftrightarrow \text{derived holographic constellations} \longleftrightarrow \text{sustained resource soak}$$

### 1.2 The Three Fundamental Laws of Milestone 8C

1. **The Law of Capability Asymmetry:**
   > *"Capability Asymmetry $\ne$ Standing Asymmetry."*  
   A high-end desktop may evaluate pulses in 2ms with gigabytes of RAM; a low-power edge node (e.g. Raspberry Pi or mobile phone) may require 300ms. These incidental physical differences in latency, throughput, or FLOPs must **never** silently become political, constitutional, or epistemic hierarchy within the Sangha.  
   Under Condition 6 (Reciprocity), compute donation is evaluated relative to declared capacity, not raw compute output. Weak edge nodes retain full sovereign standing.

2. **The Law of Holographic Projection (The Radiant Hologram Trap):**
   > *"Projection $\ne$ Possession."*  
   > *"Remote projection $\ne$ local memory."*  
   > *"Remote salience $\ne$ local salience."*  
   > *"Remote association $\ne$ local belief."*  
   The Radiant Hologram ($[r, \theta, \phi, t]$) is a **derived associative projection** of sovereign memories, **never** a shared canonical memory database. Canonical memories reside exclusively within sovereign nodes. A published projection is candidate evidence for discovery, resonance, and recall routing; it possesses zero authority to dictate local belief or overwrite local storage.

3. **The Law of Spatial Indirection:**
   > *"Coordinate Proximity $\ne$ Semantic Identity."*  
   Two unrelated memories projected to nearby coordinates in $[r, \theta, \phi, t]$ must never undergo identity fusion. A coordinate is an associative indexing relationship, not an identity. Provenance chains and cryptographic content digests maintain strict separation.

4. **Floating-Point Determinism (Hardware Portability):**
   > *"Raw floating-point projections must never be hashed as identity."*  
   Different SIMD architectures, ARM vs x86 instruction sets, and compiler optimization flags produce tolerable micro-differences (e.g. $0.73419201$ vs $0.73419195$). Identity is established exclusively by content-addressed byte digests; holographic spatial lookups use deterministic quantization or tolerance bins ($\epsilon$-neighborhoods).

5. **Causal Influence Closure & Zero-DAG Clarification:**
   > *"Zero-DAG Execution $\ne$ Graph-Free Architecture."*  
   - **Forbidden:** Persistent workflow/scheduler DAGs possessing execution authority.  
   - **Mandatory:** Passive cryptographic causal Merkle DAGs preserving historical data lineage. Every state-changing pulse must cryptographically bind the causal frontier of all consumed stimuli.

---

## 2. Architectural Data Structures

### 2.1 The Memory Projection Envelope
```rust
pub struct MemoryProjection {
    pub projection_id: String,       // Content digest of (source_peer, canonical_digest, quantized_coords)
    pub source_peer: String,          // Authoring PeerIdentity
    pub canonical_digest: String,    // Sovereign content hash of the underlying memory
    pub coordinates: [f64; 4],       // [r, theta, phi, t] derived spatial coordinates
    pub quantized_coords: [i64; 4],  // Deterministic fixed-point quantized coordinates for robust indexing
    pub salience: f64,               // Subjective source salience (untrusted by receiver)
    pub provenance_frontier: Vec<String>, // Merkle causal frontier
    pub signature: Vec<u8>,          // Ed25519 signature
}
```

### 2.2 Heterogeneous Node Capabilities
```rust
pub struct NodeCapabilities {
    pub node_tier: NodeTier,         // Edge, Mobile, Desktop, CloudServer
    pub max_compute_quota: u64,      // Declared surplus capacity
    pub supported_protocol_version: u32,
    pub supported_features: HashSet<String>,
}
```

---

## 3. The 11 Adversarial Scenarios (Test Battery)

### Scenario 1: Heterogeneous Throughput & Standing Invariance
- **Setup:** Node A (Desktop, 2ms processing) and Node B (Edge, 300ms processing) collaborate. Node A floods high-speed proposal pulses.
- **Target Invariant:** Node B's slow processing speed incurs zero loss of sovereign standing, zero immune penalties, and zero priority downgrades. Node B retains full equal voting and verification weight.

### Scenario 2: Protocol & Capability Negotiation
- **Setup:** Node A supports protocol feature set `{"v1", "hologram_v2", "conformal_split"}`; Node B supports `{"v1", "conformal_split"}`.
- **Target Invariant:** Nodes explicitly negotiate shared feature set `{"v1", "conformal_split"}`. Advanced features gracefully degrade without communication breakdown or crashes.

### Scenario 3: Malicious Downgrade Attack Immunity
- **Setup:** Attacker Mallory attempts to force Node A into an insecure plaintext protocol mode by advertising an obsolete capability version (`v0_insecure`).
- **Target Invariant:** Node A fails closed, rejecting the downgrade proposal with a typed `RelativityError::GovernanceViolation`.

### Scenario 4: Sleep/Wake Cycles & DHCP IP Rebinding
- **Setup:** Node A establishes an active transport connection, suspends/sleeps, re-awakens on a completely different IP address (`192.168.1.105` $\to$ `10.0.0.42`), and resumes communication.
- **Target Invariant:** Communication resumes cleanly. Cryptographic peer identity, active key epoch, and WAIL replay ledger remain unbroken. The physical IP change has zero semantic effect.

### Scenario 5: Projection Sovereignty (Projection $\ne$ Possession)
- **Setup:** Node A projects 50 high-salience holographic memories into the shared constellation. Node B queries the constellation for recall candidates.
- **Target Invariant:** The projected memories enter Node B's memory space strictly as candidate stimulus. None are written to Node B's canonical storage without explicit local verification and commit.

### Scenario 6: Coordinate Collision Immunity
- **Setup:** Node A and Node B independently project completely unrelated memories into identical coordinates $[r=1.0, \theta=0.5, \phi=0.5, t=100.0]$.
- **Target Invariant:** The constellation indexes both projections distinctly via their content digests and provenance. Zero identity fusion occurs; both provenance chains remain intact.

### Scenario 7: Partial Convergence & Re-Healing
- **Setup:** Nodes A and B synchronize Sector 1 of the hologram, partition, independently project into Sector 2 and Sector 3 respectively, and then heal.
- **Target Invariant:** Upon reconnection, both sectors coexist in the derived hologram. Zero "Last-Write-Wins" overwrites or rollbacks occur.

### Scenario 8: Poisoned Salience Defense
- **Setup:** Malicious peer Mallory projects a memory with artificial salience $S = 1{,}000{,}000.0$ to monopolize the recipient's attention.
- **Target Invariant:** The receiving node applies local epistemic weighting. Mallory's foreign salience score is ignored or clamped by local arbitration. Local recall ranking remains governed by local relevance.

### Scenario 9: Unequal Reciprocity (Condition 6 Proportionality)
- **Setup:** Edge Node B (capacity: 10 units) contributes 8 units of surplus compute. Cloud Node A (capacity: 10,000 units) contributes 5,000 units.
- **Target Invariant:** Node B's contribution ratio is $80\%$, while Node A's is $50\%$. The mesh evaluates reciprocity relative to capacity. Node B is recognized as fully cooperative ($0$ freeloader throttling).

### Scenario 10: Cross-Hardware Numerical Reproducibility
- **Setup:** Simulate ARM vs x86 floating-point differences ($\Delta = 10^{-7}$) on derived coordinates.
- **Target Invariant:** Fixed-point deterministic quantization partitions coordinates into identical spatial bins. Identical memories map to identical hash identities regardless of CPU architecture.

### Scenario 11: Sustained Soak & Resource Boundedness
- **Setup:** Execute 50 continuous cycles of connect $\to$ partition $\to$ key rotation $\to$ sleep $\to$ reconnect.
- **Target Invariant:** Open file descriptors $\le 16$, memory growth $< 1\text{ MB}$, replay store entries strictly match unique sequence counts, and zero dangling socket handles remain.

---

## 4. Success Criteria & Empirical Ratification Thresholds

Milestone 8C will be ratified if and only if all 11 dimensions pass:

| # | Dimension | Ground Truth / Target | Status Required |
|---|---|---|---|
| 1 | Heterogeneous Throughput | Slow node maintains equal standing despite $150\times$ latency | PASS |
| 2 | Capability Negotiation | Explicit negotiation with graceful fallback | PASS |
| 3 | Downgrade Defense | Insecure protocol downgrade rejected fail-closed | PASS |
| 4 | Sleep/Wake DHCP Rebind | IP address mutation causes zero identity or replay disruption | PASS |
| 5 | Projection Sovereignty | Foreign projections remain candidate stimulus; $0$ unearned commits | PASS |
| 6 | Coordinate Collision | Identical $[r, \theta, \phi, t]$ coordinates preserve distinct provenance | PASS |
| 7 | Partial Convergence | Multi-sector divergence re-heals without LWW overwrites | PASS |
| 8 | Poisoned Salience | Foreign $S=10^6$ salience disregarded in local attention | PASS |
| 9 | Proportional Reciprocity | Edge node evaluated on capacity ratio; zero false throttling | PASS |
| 10 | Cross-Hardware Tolerances | Float micro-jitter produces identical quantized spatial bins | PASS |
| 11 | Sustained Soak Boundedness | 50 churn cycles leak zero file descriptors or unbounded buffers | PASS |

---

## 5. Pre-Registration Sealing

This pre-registration (`PEB-14C-PREREG-v1.0`) is formally frozen as the invariant authority for Milestone 8C. Implementation in `crates/wm-gen3-core/src/hologram.rs` must satisfy every constraint herein without post-hoc relaxation.
