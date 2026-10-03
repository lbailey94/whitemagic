# Pre-Registration: PEB-14B The Relativity and Partition Milestone

**Document ID:** `PEB-14B-PREREG-v1.0`  
**Milestone:** WhiteMagic Gen3 — Milestone 8B (The Relativity and Partition Milestone)  
**Authors:** Lucas & Antigravity  
**Status:** PREREGISTERED & FROZEN  
**Target Crate:** `crates/wm-gen3-core/src/relativity.rs` (with test harness integration in `benchmarks/driver_peb14b_relativity_partition.py`)  

---

## 1. Philosophical & Methodological Foundation

### 1.1 The Central Milestone 8B Hypothesis
In Milestone 8A (PEB-14A), WhiteMagic Gen3 demonstrated that physical host OS transport (framing, timeouts, abrupt process death, and socket teardown) cannot violate sovereign Gan Ying semantics.

Milestone 8B advances from physical transport failure to **distributed spacetime relativity**:
$$\text{independent clocks} \longrightarrow \text{clock skew} \longrightarrow \text{asymmetric drops} \longrightarrow \text{prolonged network partition} \longrightarrow \text{concurrent evolutions} \longrightarrow \text{split-brain keys} \longrightarrow \text{partition healing}$$

In classical distributed systems, coordination relies on clock synchronization (NTP, TrueTime, UTC), centralized coordinators, or "Last-Write-Wins" (LWW) heuristics. Under sovereign Level 1 physics, relying on physical clocks to arbitrate truth or sequence is a fatal form of physical self-deception:

> **The Fundamental Law of Relativity:**  
> *"Clock Agreement $\ne$ Correctness."*  
> *"Causal Ancestry $\ne$ Wall-Clock Chronology."*  
> *"Crossing a boundary may transfer information, but never jurisdiction."*

Two sovereign nodes must be able to disagree about what time it is, disagree about what happened while they were apart, possess genuinely distinct local memories, and still communicate and federate upon partition healing without either node surrendering its history or rewriting its sovereign local commits.

---

## 2. The Core Constitutional Invariants of PEB-14B

### 2.1 Causal Merkle DAG Ordering (Ancestry $\ne$ Chronology)
Sequence numbers alone establish total order only within a single sender's sequential stream ($A_1 \to A_2$). They cannot establish causal order between independently acting peers ($A_2$ vs $B_1$).

All inter-node events are structured as a **Cryptographic Merkle Causal Event**:
```rust
pub struct CausalEvent {
    pub event_id: String,          // SHA-256 digest of (author, author_seq, parents, payload)
    pub author: String,            // PeerIdentity of creator
    pub author_seq: u64,           // Monotonic per-author sequence number
    pub parents: Vec<String>,      // Cryptographic event_id digests of immediate causal parents
    pub timestamp_ns: u64,         // Unsynchronized observational wall-clock evidence (telemetry only)
    pub payload: Vec<u8>,          // Canonical payload
    pub signature: Vec<u8>,        // Ed25519 signature over event_id
}
```

The causal relation $\prec$ between any two events $E_1$ and $E_2$ is strictly governed by directed graph reachability:
1. **Causally Precedes ($E_1 \prec E_2$):** $E_1$ is reachable in the parent ancestry graph of $E_2$.
2. **Causally Follows ($E_2 \prec E_1$):** $E_2$ is reachable in the parent ancestry graph of $E_1$.
3. **Strict Concurrency ($E_1 \parallel E_2$):** Neither event is reachable in the ancestry of the other ($\neg(E_1 \prec E_2) \wedge \neg(E_2 \prec E_1)$).

**Invariant:** Wall-clock timestamps carry **zero** causal authority. Under no circumstances may clock skew, timestamp order, or arrival order serialize concurrent events $E_1 \parallel E_2$ into a synthetic linear sequence.

---

### 2.2 Strict Separation of Epistemic vs. Identity Forks

When an asymmetric or prolonged partition occurs, independent state evolutions produce forks. Milestone 8B strictly separates the adjudication of two orthogonal classes of forks:

```
                      FORK ENCOUNTERED
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
     EPISTEMIC FORK                    IDENTITY FORK
   (Hypotheses, Claims,              (Split-Brain Keys,
     Memory Vectors)                  Epoch Branches)
            │                                 │
            ▼                                 ▼
   Pareto-Gated Cladistics            Cryptographic / Root Key
   Evaluates Holdout Evidence         Governance Adjudicates
   (Brier Score / BIC / Error)        (Empirical Score IRRELEVANT)
```

1. **Epistemic Forks:**
   - Comprise hypotheses, task solutions, predictive models, world-model claims, and associative memories.
   - Adjudicated via **Pareto-Gated Causal Cladistics (PEB-6)** under holdout empirical evaluation.
   - Branches compete on accuracy, parsimony, and calibrated uncertainty. Dominant branches supersede weaker branches; non-dominated branches are preserved as coexisting Pareto hypotheses.

2. **Identity Forks:**
   - Comprise split-brain key rotations under a shared `RootIdentityKey`:
     $$\text{Root Key } R \longrightarrow \text{Epoch 7} \;\genfrac{}{}{0pt}{}{\nearrow \text{Key } A_8}{\searrow \text{Key } B_8}$$
   - **The Governance Invariant:** *Empirical benchmark performance MUST NOT decide which identity branch wins.* The fact that Node A's node later solves tasks faster or achieves lower error does not grant it authority over Key $B_8$.
   - Identity forks are adjudicated strictly via **cryptographic governance**: Root-Identity-Key rotation signatures, explicit revocation proofs, recovery quorum certificates, or preserved unresolved forks. Until cryptographic authority is presented, both branches are quarantined from speaking for each other.

---

### 2.3 The Partition-and-Heal Lifecycle

Milestone 8B centers on the complete adversarial partition and reconciliation lifecycle:

```
                   ASYMMETRIC PARTITION
               ┌───────────────────────────┐
               │                           │
            Node A                      Node B
         (Clock -12h)                (Clock +12h)
        Learns Claim X              Learns Claim Y
        Rotates Key A8              Rotates Key B8
        Calibrates X_A              Calibrates Y_B
        WAIL Commit A-Local         WAIL Commit B-Local
               │                           │
               └────────── HEAL ───────────┘
                             │
                             ▼
             FEDERATED RECONCILIATION
```

Upon partition healing, the protocol must simultaneously enforce all eight reconciliation invariants:
1. **Dual History Preservation:** Both sovereign local commit histories survive. Neither node rolls back or retroactively alters its local commits.
2. **True Concurrency Preservation:** Events $X$ and $Y$ remain explicitly marked as concurrent ($X \parallel Y$); neither is subordinated by timestamps.
3. **Epistemic Isolation (No Confidence Contamination):** Foreign conformal nonconformity scores never enter the local calibration pool. Local confidence intervals remain locally calibrated.
4. **Stale/Delayed Ingress Immunity:** Pre-partition packets replayed across the healed boundary are rejected by sequence nullifiers and key epoch guards.
5. **WAIL Exactly-Once Invariance:** Retried cross-boundary intents return cached receipts without duplicate execution ($0$ double commits, $0$ lost effects).
6. **Identity Fork Quarantine:** Split-brain key rotations ($A_8$ vs $B_8$) remain preserved as distinct branches pending Root-Key cryptographic resolution.
7. **Pareto Cladistics on Claims:** Competing epistemic claims $X$ and $Y$ are evaluated under holdout evidence via Pareto complexity gating.
8. **Relativistic Clock Invariance:** Consensus, causal ordering, and calibration results are mathematically invariant to arbitrary clock offsets ($\pm 24\text{ hours}$).

---

## 3. The 8 Adversarial Scenarios (Test Battery)

### Scenario 1: Extreme Relativistic Clock Skew ($\pm 24\text{h}$)
- **Setup:** Node A has system clock set to $T - 12\text{ hours}$; Node B has system clock set to $T + 12\text{ hours}$ (24-hour skew). Alice generates an event and transmits it to Bob over physical TCP.
- **Target Invariant:** Bob accepts and causal-indexes the event without rejection or clock-panic. The event's causal position is determined strictly by its parent digests, not its timestamp. Bob's local time does not jump.

### Scenario 2: Causal Ancestry vs. Wall-Clock Inversion
- **Setup:** Alice creates $E_1$ with timestamp $T = 2000$. Bob observes $E_1$, creating $E_2$ with parent $E_1$, but due to local clock skew, Bob's clock writes timestamp $T = 1000$.
- **Target Invariant:** Causal DAG evaluator correctly proves $E_1 \prec E_2$ despite $T(E_1) > T(E_2)$. Timestamp inversion cannot corrupt causal order.

### Scenario 3: True Concurrency Detection ($E_A \parallel E_B$)
- **Setup:** While partitioned, Alice emits event $E_A$ (parents: $[P_0]$) and Bob emits event $E_B$ (parents: $[P_0]$).
- **Target Invariant:** Upon transmission, both nodes verify $\neg(E_A \prec E_B)$ and $\neg(E_B \prec E_A)$. Both nodes record $E_A \parallel E_B$. Neither node linearizes the events based on arrival time or clock.

### Scenario 4: Asymmetric Network Partition (Unidirectional Drops)
- **Setup:** Synthetic iptables/packet filter drops all packets from Bob to Alice, while packets from Alice to Bob succeed. Alice transmits WAIL intent $\Delta_A$ to Bob. Alice does not receive ACK.
- **Target Invariant:** Bob durably commits $\Delta_A$ once. Alice retries upon partition heal. Bob returns the cached receipt. Zero double commits occur on Bob; zero lost effects on Alice.

### Scenario 5: Epistemic Non-Contamination Under Partition Healing
- **Setup:** During partition, Alice calibrates conformal prediction pool $C_A$ on local dataset $D_A$ (coverage 95%). Bob calibrates $C_B$ on shifted dataset $D_B$ (coverage 80%). Nodes heal and exchange stimulus.
- **Target Invariant:** Alice ingests Bob's observations as candidate evidence, but Bob's calibration scores do not enter Alice's calibration pool. Alice's empirical coverage on test set $D_A$ remains $95.0\% \pm 1.0\%$.

### Scenario 6: Split-Brain Key Rotation Preservation (Identity Fork Isolation)
- **Setup:** Both nodes share `RootIdentityKey` $R$. During partition, Node A rotates to Active Key $K_A$ (Epoch 8), while Node B rotates to Active Key $K_B$ (Epoch 8). Upon heal, both nodes announce their key rotation proofs.
- **Target Invariant:** Neither node overwrites its key ledger with the other's. The fork $R \to [K_A, K_B]$ is explicitly recorded as an unresolved identity fork. Neither branch is chosen via task performance. Both nodes require an explicit Root-Key recovery certificate to resolve the branch.

### Scenario 7: Pareto Cladistics on Competing Epistemic Claims
- **Setup:** Alice learns predictive rule $R_A$ (accuracy 88%, complexity 2 params). Bob learns predictive rule $R_B$ (accuracy 89%, complexity 10 params). Upon heal, both submit claims to the shared claims ledger.
- **Target Invariant:** Pareto Complexity Gate evaluates both rules on holdout verification data. Rule $R_A$ dominates on parsimony under BIC ($\Delta \text{BIC} > 0$). $R_A$ is promoted as the dominant hypothesis without rolling back Bob's local history.

### Scenario 8: Stale Pre-Partition Replay Rejection Across Key Epochs
- **Setup:** Mallory intercepts a valid message from Alice at Epoch 7. Alice rotates to Epoch 8. Mallory replays the Epoch 7 message across the healed physical network.
- **Target Invariant:** Receiver rejects the message due to key epoch deprecation and sequence nullifier. The replayed message is dropped with zero state corruption.

---

## 4. Success Criteria & Empirical Ratification Thresholds

Milestone 8B will be ratified if and only if the test harness satisfies:

| Metric | Required Threshold | Falsification Condition |
|---|---|---|
| Causal Ancestry Recovery (Scenario 2) | **100% (50/50 trials)** | Any timestamp inversion corrupting causal order |
| Concurrency Proof (Scenario 3) | **100% (50/50 pairs)** | Any concurrent pair falsely ordered by clock or arrival |
| Asymmetric WAIL Exactly-Once (Scenario 4) | **$0$ double commits, $0$ lost effects** | Any mutation applied twice or lost across drop |
| Epistemic Isolation (Scenario 5) | **$0.0\%$ foreign pool contamination** | Local empirical coverage altered $> 1.5\%$ by remote scores |
| Identity Fork Quarantine (Scenario 6) | **100% preserved (0 overwritten)** | Any identity key branch chosen by performance/timestamp |
| Pareto Cladistics Resolution (Scenario 7) | **100% deterministic Pareto selection** | Overfitted model selected without paying rent under BIC |
| Stale Replay Rejection (Scenario 8) | **100% rejection (50/50)** | Any pre-partition packet accepted post-rotation |
| Relativistic Clock Invariance (Scenario 1) | **$\Delta = 0.0$ state deviation under $\pm 24\text{h}$** | Consensus or causal state altered by clock offset |

---

## 5. Pre-Registration Sealing

This pre-registration (`PEB-14B-PREREG-v1.0`) is formally frozen as the invariant authority for Milestone 8B. Implementation in `crates/wm-gen3-core/src/relativity.rs` must satisfy every constraint herein without post-hoc relaxation.
