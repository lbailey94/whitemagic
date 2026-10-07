<!-- Extracted from Antigravity CLI session 221fbb57-905f-4e7d-a4d3-3c11810ea0b7
     message 529b243e-6626-4bbe-a638-550b5801cefd | sender 127c4a34-47e5-4ea3-a8d8-f2be70a98c3c | 2026-09-19T01:34:50.273714924Z
     Original title: Message from Homeostasis and Autoimmunity Scout (research)
     Extracted 2026-09-21 by opencode; content unmodified. -->

# Investigation Report: Closed-Loop Homeostasis, Circuit Breakers, and Autoimmunity across Gen1 and Gen2

**To**: Parent Agent (`221fbb57-905f-4e7d-a4d3-3c11810ea0b7`)  
**Subject**: Comparative Architectural Analysis of Homeostasis, Circuit Breakers, Governance, and Autoimmunity (Gen1 vs Gen2 vs Gen3)

---

## 1. Gen1 7-Dimension Harmony Vector and the Homeostatic Loop

### A. How the 7 Dimensions Were Computed (`whitemagic/harmony/vector.py`)
In Gen1, telemetry was updated on every tool invocation via `HarmonyVector.record_call(tool_name, duration_s, success, declared_safety, actual_writes)`. Calls were appended to a thread-safe `_RollingWindow` (default 300s window, max 2000 events). Each dimension was normalized to `[0.0, 1.0]` (where 1.0 represents optimal health):

1. **`balance` (Yin/Yang Ratio)**:
   - Evaluated the balance between mutating actions (Rajasic: `WRITE`/`DELETE` tools or uncategorized tools) and introspection/reflection (Sattvic: read/inspection tools like `get_*`, `list_*`, `search_*`, `read_*`, `archaeology_*`, `state.*`, etc., plus Tamasic).
   - $\text{rajasic\_ratio} = \frac{N_{\text{rajasic}}}{N_{\text{total}}}$; $\text{deviation} = |\text{rajasic\_ratio} - 0.5|$
   - $\text{balance\_score} = \max(0.0, 1.0 - 2 \cdot \text{deviation})$. Perfectly balanced (50/50) yields 1.0; 100% action or 100% reflection degrades to 0.0.
2. **`throughput` (Cadence)**:
   - Tool calls per minute ($cpm$) over the rolling window:
     - $cpm < 1.0 \implies 0.5$ (quiet/idle but functional)
     - $1.0 \le cpm \le 60.0 \implies 1.0$ (nominal interactive operating zone)
     - $cpm > 60.0 \implies \max(0.2, 1.0 - \frac{cpm - 60.0}{200.0})$ (penalized for runaway thrashing).
3. **`latency` (Response Time Distribution)**:
   - Computed from the $p50$ and $p95$ of `duration_s` within the window:
     - $p95 \le 0.5s \implies 1.0$
     - $0.5s < p95 \le 2.0s \implies 1.0 - (p95 - 0.5) \cdot 0.2$
     - $p95 > 2.0s \implies \max(0.2, 0.7 - (p95 - 2.0) \cdot 0.0625)$.
4. **`error_rate` (Reliability Metric)**:
   - $\text{error\_fraction} = \frac{\text{errors}}{\text{total}}$
   - $\text{error\_score} = \max(0.0, 1.0 - \text{error\_fraction} \cdot 5.0)$ (a 20% error rate completely collapses the dimension score to 0.0).
5. **`dharma` (Ethical/Constitutional Alignment)**:
   - Queried dynamically from `get_dharma_system(with_audit=False).get_ethical_score()`. If the Dharma module was absent, it defaulted optimistically to 1.0.
6. **`karma_debt` (Side-Effect Fidelity)**:
   - Tracked contract violations where a tool declared `declared_safety == "READ"`, but executed `actual_writes > 0`.
   - Each mismatch added +1.0 to cumulative `_karma_debt_total`.
   - $\text{karma\_score} = \max(0.0, 1.0 - \frac{\text{debt}}{10.0})$ (10 mismatches dropped the score to 0.0). Debt decayed gradually via `decay_karma_debt(0.1)`.
7. **`energy` (Runtime & Memory Vitality Proxy)**:
   - Blended runtime health with memory retention topology:
     - $\text{runtime\_energy} = \max(0.0, 1.0 - 2 \cdot \frac{N_{\text{duration} > 5s}}{N_{\text{total}}})$
     - $\text{galactic\_vitality} = \sum (\text{zone\_weight} \cdot \text{count}) / \text{total}$ (CORE=1.0, INNER_RIM=0.8, MID_BAND=0.5, OUTER_RIM=0.2, FAR_EDGE=0.05).
     - $\text{energy} = 0.6 \cdot \text{runtime\_energy} + 0.4 \cdot \text{galactic\_vitality}$.
8. **Composite `harmony_score`**:
   - Weighted sum with default weights: `error_rate: 0.20`, `balance: 0.15`, `latency: 0.15`, `dharma: 0.15`, `karma_debt: 0.15`, `throughput: 0.10`, `energy: 0.10`.
   - Pushed lock-free to the shared-memory `StateBoard` (<100ns access).

### B. Corrective Actions Attempted by the Gen1 Homeostatic Loop (`whitemagic/harmony/homeostatic_loop.py`)
Operating asynchronously on the temporal scheduler's MEDIUM lane (every 10s), the loop evaluated scores against a 4-level graduated ladder: `OBSERVE` $\to$ `ADVISE` $\to$ `CORRECT` $\to$ `INTERVENE`.
- **High error rate (`error_rate < 0.4`)**: Emitted a Gan Ying resonance event `WARNING_ISSUED` onto the internal event bus.
- **High karma debt (`karma_debt < 0.4`)**: Emitted a Gan Ying resonance event `BOUNDARY_VIOLATED`.
- **Low energy (`energy < 0.3`)**: Spawned an unthrottled background thread running `mgr.run_sweep()` (memory lifecycle sweep / mindful forgetting).
- **Low dharma (`dharma < 0.4`)**: Tightened the Dharma rules engine profile to `"secure"`.
- **High latency (`latency < 0.5`)**: Logged an advisory string: *"High latency... Check circuit breaker status."*
- **Critical composite (`harmony_score < 0.3`)**: Emitted `SYSTEM_HEALTH_CHANGED` (critical) on the Gan Ying bus.
- **Physical metrics (CPU temp $\ge 80^\circ\text{C} / 90^\circ\text{C}$, RAM $\ge 90\%$, Battery $\le 15\%$)**: Logged warnings or advisories (*"Memory at 90%. Close heavy applications"*).

---

## 2. Why Gen1 Homeostasis and Autoimmunity Failed to Prevent Runaways

1. **Advisory-Only / Non-Interventionist Seam**:
   - Line 20 of `homeostatic_loop.py` explicitly codified the flaw: *"The loop never blocks tool dispatch — it runs asynchronously on the temporal scheduler's MEDIUM lane"*.
   - When tools failed or runaway loops occurred, the loop merely posted event bus notices (`WARNING_ISSUED`) and wrote advisory log entries. It had **no backpressure mechanism**, no token-bucket throttling, no caller suspension, and no dispatch rejection gate. Callers continued hammering the system unimpeded.
2. **Systemic Exception Swallowing (`BLE001`)**:
   - Across `homeostasis.py`, `vector.py`, `homeostatic_loop.py`, `circuit_breaker.py`, and `autoimmune.py`, broad `try...except Exception:` blocks silently swallowed failures: `logger.debug("Swallowed exception", exc_info=True)` or `logger.debug("Exception silenced: %s", e)`.
   - In `homeostasis.py:134`, `get_balance()` defaulted optimistically:
     ```python
     if hv is None:
         return 1.0  # optimistic default when subsystem unavailable
     except Exception:
         return 1.0
     ```
     If the monitoring engine crashed, the system reported a perfect harmony score of `1.0`, blinding the supervisor to active failures!
3. **Ineffective Circuit Breakers (`tools/circuit_breaker.py`)**:
   - The breaker cooldown was artificially lowered to **1.0 second** (`cooldown_seconds = 1.0`, line 69) "for responsiveness".
   - When a service or tool broke, the breaker tripped to `OPEN`, immediately decayed to `HALF_OPEN` after 1000ms, let another request fail, and repeated indefinitely—hammering broken backends in a tight loop.
   - Furthermore, `os.getenv("WM_RD_MODE")` unconditionally invoked `reset_all()` on startup, clearing tripped breakers.
4. **Linter-Only "Autoimmune Defense" (`defense/autoimmune.py`)**:
   - Marketed in docstrings as *"Transform anti-patterns into active defenses"*, the implementation was literally a static Python script matching 4 regex patterns (`Path.home()`, `.expanduser()`, `except Exception: pass`, and `TODO`) in `.py` source files and writing matches to a JSONL file (`autoimmune_findings.jsonl`).
   - It possessed zero runtime dispatch interception, zero anomaly heuristics, zero sandboxing, and zero remediation capability. Ironically, line 77 of `autoimmune.py` itself swallowed exceptions with `except Exception: logger.debug("Swallowed exception")` while looking for `except Exception: pass`.
5. **Self-Aggravating Resource Spawns**:
   - In Gen1, the 4-tier consciousness loop ran without resource constraints, generating 59,411 memories across 47 galaxies (an 11GB SQLite database) and repeating the same 29 insights every 20–40 minutes.
   - When memory pressure dropped the `energy` metric below threshold, the homeostatic loop attempted to correct this by spawning *more* background threads (`threading.Thread(target=mgr.run_sweep, daemon=True)`), causing severe SQLite lock contention and accelerating system collapse.

---

## 3. How Gen2 Hardened the Safety Architecture

Gen2 eliminated Gen1's reliance on voluntary compliance and advisory logging, enforcing safety through deterministic kernel and dispatch seams:

### A. Firebreak: 31 Forbidden Patterns & The Bulk-Scope Law (`wm-governance/src/firebreak.rs`)
1. **The 31 Forbidden Patterns**:
   - **24 Command Patterns**: Hard vetoes against filesystem annihilation (`rm -rf /`, `rm -rf ~`, `rm -rf *`, `rmdir /`, `find -delete`), disk formatting/raw writes (`mkfs.*`, `dd of=/dev/`, `fdisk`, `parted`, `> /dev/sd*`, `> /dev/nvme*`), system corruption (`:(){ :|:& };:`, `chmod -R 777 /`), network attack tools (`nmap -sS`, `hping3`, `ettercap`), and pipe-to-shell exploits (`curl ... | bash`, `wget ... | sh`).
   - **7 Protected Credential Paths**: Dispatches accessing credential stores (`id_rsa`, `id_ed25519`, `.ssh/`, `.gnupg`, `/etc/shadow`, `authorized_keys`, `.aws/credentials`) are treated as exfiltration-shaped and forbidden.
   - **Verdict Ladder**:
     - *Forbidden*: **Blocked unconditionally, even with `confirm: true`**.
     - *Dangerous* (13 patterns like `rm -r`, `git push --force`, `drop table`, plus paths `/etc`, `/bin`, etc.): Blocked unless explicit `confirm: true` is supplied.
     - *Caution* (8 patterns like `sudo`, `mv`, `pip uninstall`): Allowed, but with mandatory audit disclosures.
2. **Irreversible Seam Evaluation**:
   - Scanned *only* at the irreversible boundary (`effects.destructive || effects.spawns || writes.contains(Process | Network | Filesystem)`). Prose and notes (e.g. incident logs in `memory.create`) are intentionally never scanned, preventing false-positive blocking of documentation.
3. **Bulk-Scope Law (P1.6, the Jul-13 Lesson)**:
   - Rooted in the post-mortem of 54,192 memories deleted through an un-scoped backend call on Jul 13, 2026.
   - Enforced by `SCOPE_REGISTRY`: destructive tools (`memory.delete`, `memory.batch_delete`, `galaxy.purge`, `galaxy.transfer`, `galaxy.restore`, `memory.consolidate`, `memory.deduplicate`, `system.flush`) MUST supply an explicit bounding target argument (`id`, `ids`, `galaxy`, `snapshot_id`). Unscoped bulk deletions are rejected before execution.

### B. Yama Resource Rules: Budgets & Anti-Circular Thinking (`wm-governance/src/resource_rules.rs`)
1. **Dynamic Resource Budgets**:
   - Enforces rolling 60-second rate limits on writes (`max_writes_per_minute`: default 120, strict 15), process spawns (`max_spawns_per_minute`: default 10, strict 3), and network calls (`max_network_per_minute`: default 30, strict 10).
   - Budgets scale dynamically with health score: $\text{limit} = \text{cfg\_limit} \cdot \text{health\_scale}$, constricting automatically under stress while maintaining minimal operational floors.
2. **BrainWave Operational Ceilings**:
   - `Delta` (Deep sleep/idle): Writes = 0, spawns = 0, network = 0 (complete write block).
   - `Theta` (Dream/consolidation): Write budget cut to 25%, spawns = 0, network = 0.
   - `Alpha`: Writes cut to 50%, spawns/network cut to 25%.
3. **Novelty Requirement (Anti-Circular Thinking)**:
   - Tracks a rolling window of 50 action signatures (`tool_name` + `args_hash`).
   - If an action signature repeats $\ge 3$ times (`max_repeats`), the action is rejected with `ResourceVerdict::NotNovel`. This cured Gen1's circular loop of generating the same 29 insights repeatedly.
4. **Purpose and Human Review**:
   - Autonomous dispatches (`!user_initiated`) strictly require a declared purpose string (`has_purpose`) and human review authorization (`require_human_review`).

### C. Landlock LSM Confinement (`sandbox_exec.rs` and `landlock_sandbox.rs`)
1. **Kernel-Enforced Sandboxing**:
   - Moves from userspace strings to the Linux Security Module (LSM) Landlock API (ABI V1–V9 ladder), binding filesystem writes at the kernel level.
2. **Whole-Process Confinement (v0)**:
   - `restrict_to_store_root` handles every write-class filesystem right, confining mutations strictly beneath `store_root`, with explicit, minimal white-listed exceptions (`/dev/null` for git subshells, and the `.git` lease ledger for coordination claims).
3. **Scoped-Thread Sandbox Executor (v1 - P-SANDBOX-3)**:
   - For tools declaring `Sandbox::StoreScoped`, dispatches are spawned on a dedicated, fresh OS thread (`std::thread::scope`).
   - Landlock restriction is applied thread-locally before the tool body runs. Because Landlock is irreversible and thread-local, the confined thread exits after the call without contaminating Tokio worker thread pools.
   - Panics inside the tool are contained at the thread boundary and converted to `CoreError::Tool`, ensuring the server process never crashes.
4. **Loud Degradation Doctrine**:
   - If Landlock is unavailable on the host kernel or fails, the process continues unconfined with a loud `WARN` and updates telemetry (`stats().degraded`), preventing silent security failures while preserving operational uptime.

---

## 4. Gen3 Closed-Loop Homeostatic Control Laws Under Environmental Stress

Gen3 should replace disconnected heuristic checks with a continuous, negative-feedback multivariable control law.

### A. State Variable Representation
Let system state be represented as vector $\vec{x}(t)$:
$$\vec{x}(t) = \begin{bmatrix} P_{\text{RAM}}(t) \\ L_{\text{p95}}(t) \\ W_{\text{churn}}(t) \\ C_{\text{ctx}}(t) \\ T_{\text{sys}}(t) \end{bmatrix}$$
Where:
- $P_{\text{RAM}} \in [0, 1]$: Memory pressure (RSS / cgroup limit, page fault rate).
- $L_{\text{p95}} \in [0, \infty)$: p95 tool dispatch and query latency vs target baseline.
- $W_{\text{churn}}$: Uncommitted write volume, WAL size, and Tantivy commit frequency.
- $C_{\text{ctx}} \in [0, 1]$: Token occupancy ratio of active LLM / reasoning context.
- $T_{\text{sys}}$: Host thermal state and CPU load.

The controller computes an error vector $\vec{e}(t) = \vec{x}_{\text{target}} - \vec{x}(t)$, driving a discrete state machine across 4 distinct regimes:
1. `NOMINAL` ($\text{Health} \ge 0.85$): Full fidelity; broad recall; all background transforms active.
2. `CONSERVING` ($0.60 \le \text{Health} < 0.85$): Mild throttling; cache consolidation; background tasks spaced out.
3. `STRESSED` ($0.35 \le \text{Health} < 0.60$): Aggressive actuator engagement; narrowed search; non-essential transforms suspended.
4. `CRITICAL` ($\text{Health} < 0.35$): Complete write shedding; lexical-only recall; forced Theta consolidation.

```
                    ┌─────────────────────────┐
                    │ Environmental Telemetry │
                    │  (RAM, Latency, Churn,  │
                    │   Context, Temperature) │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Multi-Variable Control  │
                    │   Law / State Machine   │
                    └────────────┬────────────┘
         ┌───────────────────────┼───────────────────────┐
         ▼                       ▼                       ▼
┌──────────────────┐   ┌───────────────────┐   ┌──────────────────┐
│  Recall Breadth  │   │  Stellar Mass /   │   │ Cognitive Engine │
│    Actuation     │   │ Memory Tiering    │   │  Sleep States    │
├──────────────────┤   ├───────────────────┤   ├──────────────────┤
│• Top-K: 20 → 5   │   │• Evict Outer Rim  │   │• Suspend Embeds  │
│• Graph Hop: Off  │   │• LMDB Cold Store  │   │• Pause Causal/   │
│• Conformal Alpha │   │• HNSW Cache Trim  │   │  Mining Daemons  │
│• Snippet Compress│   │• Vacuum/WAL Delay │   │• BrainWave Theta │
└──────────────────┘   └───────────────────┘   └──────────────────┘
```

### B. Specific Adaptation Knobs (Actuators)

#### 1. Contracting Recall Breadth (Latency Spikes & Context Window Contraction)
- **Top-K Adaptive Slicing**: Hybrid search limits contract dynamically: $K = 20 \xrightarrow{\text{stressed}} 10 \xrightarrow{\text{critical}} 3$.
- **Graph Expansion Disabling**: In `wm-memory/src/recall.rs`, `graph_weight` controls post-fusion 1-hop expansion through association edges. Under latency stress, $graph\_weight \to 0.0$, eliminating graph-traversal overhead.
- **Conformal Set Tightening**: Tighten miscoverage parameter $\alpha$, discarding low-confidence, borderline recall candidates.
- **Dynamic Content Truncation**: When $C_{\text{ctx}} > 0.85$, retrieved memory payloads are automatically downgraded from full raw bodies to concise lexical snippets or dense summary embeddings before entering context.

#### 2. Cooling Low-Mass Stars (RAM Pressure & Cache Saturation)
- In the Galactic Memory model, memories represent stars situated across radial zones: `CORE`, `INNER_RIM`, `MID_BAND`, `OUTER_RIM`, and `FAR_EDGE`.
- **Selective Memory Eviction**: Under RAM pressure ($P_{\text{RAM}} > 0.80$), low-mass stars (memories in `OUTER_RIM` and `FAR_EDGE` with low importance and low recall frequency) have their in-memory vectors, graph edges, and token caches dropped from RAM into LMDB cold storage.
- **Index Segment Shrinking**: Prune in-memory Tantivy reader caches and in-memory HNSW index structures, preserving hot cache lines only for `CORE` and `INNER_RIM` stars.
- **Accelerate Decay Drift**: Shift inactive, unprotected memories outward to the galactic rim, freeing inner-rim working memory slots.

#### 3. Sleeping Expensive Transforms (CPU, Write Churn, and Thermal Stress)
- **Defer Vector Embeddings**: Ingested memories are persisted to LMDB immediately with text indexing, but embedding generation via local llama.cpp / GPU is queued to disk and delayed.
- **Background Engine Sleep**:
  - Automatically suspend continuous background daemons: causal relationship mining, galaxy cross-clustering, association decay passes, and semantic deduplication sweeps.
  - Delay database index defragmentation and SQLite/LMDB compaction until system idle.
- **Enforced Theta State**: Transition the system's `BrainWave` state from `Gamma`/`Beta` to `Theta`, which automatically clamps Yama write budgets by 75% and bans process spawns and network requests.

---

## 5. Autoimmunity: Trusted/Verified Behavior vs. Harmful State Transitions with Reversible Quarantine

### A. The Failure of Naive Xenophobia
Gen1's defense model represented naive xenophobia:
- **Brittle Regex Blacklists**: Superficial pattern matching (e.g. scanning for `Path.home()` or `except Exception: pass`) produced false positives on legitimate code and false negatives on novel exploits.
- **Scorched-Earth Deletion**: The catastrophic memory wipe of Jul 13 (54,192 memories lost) occurred because destructive actions were executed without scope boundaries or validation gates.
- **Context Blindness**: Lacking execution context, a defensive system cannot distinguish between an agent attempting to execute `rm -rf /` vs. an engineer creating a memory documenting the incident `rm -rf /`.

### B. Autoimmunity as Behavioral Invariant Verification
A mature immune system does not destroy structures merely because they are unfamiliar; it distinguishes between normal cellular operation and destructive pathology based on verified behavioral contracts:
1. **Cryptographic & Provenance Attestation**:
   - Entities must carry valid provenance tokens (`wm-record-attestation`, `wm-release-manifest`). Unsigned or unverified artifacts are refused execution access.
2. **Contract Fidelity (The Karma Principle)**:
   - Verification that declared intent matches observed behavior: if an operation requests read access but attempts state mutations, or declares single-item scope but executes a batch drop, the transition is intercepted.
3. **Seam Invariant Enforcement**:
   - Hard kernel and architectural boundaries (Landlock store-root isolation, Yama rate limits, Firebreak 31 forbidden patterns) enforce immutable constraints regardless of caller role.

### C. Reversible Quarantine: The Core Defensive Primitive
Rather than irrecoverable deletion, Gen2 and Gen3 establish **reversible quarantine** as the foundational defensive response:

1. **Index Corruption Handling (`wm-memory/src/reindex.rs`)**:
   - When a Tantivy search index is corrupt or unopenable, the engine never deletes it. It invokes `quarantine_index`, performing an atomic rename to `{index_name}.corrupt.{timestamp}`. The corrupted artifact remains preserved beside the freshly created index for forensic audit, while recovery proceeds immediately.
2. **Epistemic & Memory Isolation (`voice_audit` & `QuarantineManager`)**:
   - When hallucinated claims or anomalous updates are detected, memories are not purged. They are assigned `memory_type = 'quarantined'`.
   - Quarantined memories are automatically excluded from production search pipelines, graph traversals, and dream consolidations (`WHERE memory_type != 'quarantined'`), eliminating toxic feedback loops while preserving the full record for human inspection and rehabilitation (`release_session`).
3. **Mesh Peer Isolation (`sangha.quarantine`)**:
   - When a node in the distributed mesh displays Byzantine or malicious behavior, `sangha.quarantine` strips its active lock leases and durable scope claims, and refuses incoming messages.
   - The isolation is non-destructive: peer records remain in the quarantine registry, and the node can be restored via `release_quarantine` without database surgery once validated.

### D. Architectural Comparison Matrix

| Capability | Gen1 (v26.0.3 Python) | Gen2 (WMv9 Rust) | Gen3 (Target State) |
|---|---|---|---|
| **Monitoring** | 7D Harmony Vector (Python / StateBoard) | 7D Substrate Harmony + Z-Score Anomaly | Continuous Multi-Variable State Vector $\vec{x}(t)$ |
| **Control Action** | Advisory logging & Gan Ying bus events; dispatch never blocked | Yama write/spawn budgets, BrainWave state gating | Closed-loop PID / negative feedback control laws |
| **Circuit Breakers** | 1.0s cooldown; swallowed exceptions; wiped by `WM_RD_MODE` | In-memory & StateBoard circuit handlers | Adaptive exponential backoff with half-open probe budgets |
| **Execution Sandboxing** | None (in-process Python) | Landlock v0 (process) & v1 (scoped-thread OS LSM) | Per-tool Landlock + seccomp-BPF + memory limits |
| **Command Guardrails** | Voluntary Governor checks | Firebreak: 31 hard-vetoed patterns + bulk-scope law | Semantic AST-level intent verification + capability tickets |
| **Resource Limits** | Unbounded (59k memories, runaway consciousness loops) | Yama rate budgets + novelty detection (anti-circular) | Dynamic load-shedding: top-K contraction, stellar cooling |
| **Autoimmunity** | 4 regex patterns in `.py` files saved to JSONL | Reversible index quarantine & Sangha mesh isolation | Behavioral state verification + reversible quarantine across all layers |

---
*Report compiled from code inspection of Gen1 core and Gen2 WMv9 crates.*
