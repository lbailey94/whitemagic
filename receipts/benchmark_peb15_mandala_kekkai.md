# PEB-15: Mandala Kekkaishi Kernel Sandbox & Sovereign Factory Benchmark

**Specification:** Mandala Meta-OS Sovereign Confinement (Landlock LSM + Pure-Rust rlimit + Spec 0.5 Receipts)
**Date:** 2026-10-03 01:35:28Z
**Profile:** `release (optimized)`

---

## 1. Executive Summary

Mandala's **Kekkaishi Spatial Capability Barriers** operate inside the existing kernel process table via unprivileged Linux Landlock LSM syscalls and POSIX `rlimit` resource bounds. By eliminating hypervisor page table bootstrapping and daemon communication, a complete sovereign jail materializes and dissipates in **230.22 µs**, outperforming traditional VM and container lifecycles by orders of magnitude while preserving battery health and thermal stability.

---

## 2. Microsecond Telemetry & Throughput Scorecard

| Pillar | Measured Operation | Latency | Throughput | Invariant / Target | Status |
|---|---|---|---|---|---|
| **1** | JEV Decision Tensor Pre-Triage | **26.7 ns** | **37,495,313 evals/s** | Sub-100 ns System 1 fast triage | **PASS** |
| **2** | WorkspaceClaim Matrix & Ed25519 Signing | **87.67 µs** | **11,406 claims/s** | Cryptographic ephemeral targeting ($Hōi 	o Jōshiki$) | **PASS** |
| **3** | Landlock Ruleset Compilation (Auto-ABI + Net Jail) | **142.55 µs** | **7,015 rulesets/s** | Dynamic ABI V1-V5 auto-negotiation + zero egress | **PASS** |
| **4** | Spec 0.5 Continuity Receipt Notarization | **341.93 µs** | **2,924 receipts/s** | Ed25519 signing + StateCommitment + verification | **PASS** |
| **5** | Homeostatic Thermodynamic Refusal | **104.3 ns** | **9,586,509 refusals/s** | Critical regime thermal/battery protection | **PASS** |
| **6** | End-to-End Sovereign Factory Trial Pipeline | **604.44 µs** | **1,654 trials/s** | Article 6 + Preflight + JEV + Landlock + Pareto + Receipt | **PASS** |

---

## 3. Comparative Isolation Paradigm Lifecycle

| Paradigm | Setup Latency (µs) | Overhead vs Mandala | Thermodynamic Profile |
|---|---|---|---|
| **Qubes OS (Xen VM)** | 3,000,000 µs | **13031.0x slower** | Extreme (High CPU/RAM allocation, fan burst) |
| **Docker / runc** | 120,000 µs | **521.2x slower** | Moderate (Daemon socket, cgroup namespaces) |
| **Firecracker microVM** | 35,000 µs | **152.0x slower** | Warm (KVM guest kernel initialization) |
| **Mandala Kekkaishi (Gen3)** | **230.22 µs** | **1.0x (Baseline)** | **Near-Zero (<0.01W, in-process kernel LSM)** |

---

## 4. Key Architectural Conclusions

1. **Microsecond Spatial Barriers:**
   Mandala achieves an end-to-end barrier initialization latency of **~230 µs**, rendering ephemeral sandboxing viable inside tight agentic loops (1,600+ full evolutionary trials per second).
2. **Non-Autoregressive Fast Gating:**
   The JEV decision tensor prunes unpromising directions at **37,495,313 evals/sec** (26.7 ns), preventing wasted filesystem allocations and heavy model calls.
3. **Hardware Longevity & Homeostasis:**
   When the substrate enters `Critical` thermal or power regimes, evaluations are refused in **104.3 ns**, protecting laptop battery chemistry and silicon junctions.
