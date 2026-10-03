# Pre-Registration: PEB-15 Amendment for Gate 9D — Alpha Reality Test (Operational Resilience, Migration Integrity & Cut-Point Crash Consistency)

**Document ID:** `PEB-15-AMEND-GATE9D-v1.0`  
**Parent Document:** `PEB-15-PREREG-v1.0` (`docs/PREREGISTRATION_PEB15_PRODUCTION_GRADUATION.md`)  
**Milestone:** WhiteMagic Gen3 — Milestone 9 (Alpha Production Graduation) Gate 9D  
**Authors:** Lucas & Antigravity (with Sangha Peer Review)  
**Date:** September 24, 2026  
**Status:** PREREGISTERED & FROZEN  
**Target Crates:** `crates/wm-gen3-core`, `crates/wm-gen3-harness`  

---

## 1. Problem Statement & Motivation

Following the successful execution of Gate 9B (pure-Rust zero-dependency LMDB reader and production `wm` CLI) and Gate 9C (Lexical Anchor Coherence, calibrated continuous projection, and the re-derivation of 28 Gana recipes as stateless transform policies), the Gen3 kernel is mathematically verified.

However, as established in our architectural memorandum (*System Zero: The Cognitive Substrate & 2026 Frontier AI Synthesis*), an autonomic substrate must withstand the chaotic entropy of real-world operation:
1. **Dirty & Corrupted Stores:** Legacy Gen1/Gen2 data stores contain truncated MessagePack payloads, tampered SHA-256 hashes, invalid UTF-8 sequences, and corrupted database pages. Upgrading must neither crash nor silently swallow errors.
2. **Interrupted Execution & Power Loss:** If power is severed or `SIGKILL` is issued mid-pulse or mid-migration, the system must maintain absolute write-ahead consistency, prevent capability replay attacks, and recover cleanly on reboot.
3. **Idempotency & Re-execution:** Rerunning a migration or re-playing a batch must produce zero duplicate records and zero state drift.
4. **Protocol & Envelope Skew:** Future versions, unknown RPC calls, and malformed network envelopes must fail closed with structured cryptographic clarity rather than memory faults or ambient execution.

Gate 9D subjects the production candidate to this adversarial reality battery.

---

## 2. Formal Hypotheses

### Hypothesis H9D-1: Migration Atomicity, Idempotency, and Data Fidelity
> *Batch migration of legacy Gen2 LMDB stores into Gen3 via chunked sovereign pulses (`wm migrate`) converts 100% of valid records while preserving temporal provenance, original IDs, content hashes, and epistemic kinds. Re-executing the migration against an already-migrated target store is strictly idempotent, creating exactly 0 duplicate records and 0 state drift.*

### Hypothesis H9D-2: Cut-Point Crash Consistency (Power Loss & SIGKILL Emulation)
> *Simulating abrupt process termination at any of the five discrete write lifecycle cut-points (pre-nullifier, post-nullifier fsync, mid-delta application, post-commit pre-receipt, and restart recovery) produces zero corrupted store files, zero unpersisted nullifiers, zero orphan capabilities, and results in clean automatic recovery to the last valid committed epoch upon restart.*

### Hypothesis H9D-3: Dirty Store Tolerance & Forensic Quarantine
> *When ingesting legacy stores with injected corruptions (truncated MessagePack buffers, invalid UTF-8 sequences, SHA-256 content mismatches, and malformed header bytes), the migration engine recovers 100% of uncorrupted records, never panics or aborts ungracefully, diverts 100% of damaged records to an isolated `quarantine.jsonl` with structured forensic error codes, and issues a cryptographic `migration_receipt.json`.*

### Hypothesis H9D-4: Network Envelope Skew & Protocol Defense
> *Exposing the JSON-RPC and envelope interface (`wm serve`) to forward protocol versions, unknown method names, unauthenticated payloads, and malformed JSON-RPC frames results in fail-closed typed error responses with zero panics, zero memory unsafety, and zero ambient state dispatch.*

---

## 3. Frozen Metric Acceptance Thresholds

The following metric thresholds are frozen prior to implementation. Any failure constitutes a gate rejection:

| Metric | Target Threshold | Falsification Condition |
|---|---|---|
| **Clean Record Fidelity** | $100.0\%$ converted | $< 100.0\%$ |
| **Migration Idempotency** | $0$ duplicate records created on re-run | $> 0$ |
| **Crash Invariant (Epoch Rollback/Consistency)** | $100.0\%$ clean recovery on restart | Any store corruption or panic |
| **Orphan Capabilities after Crash** | $0$ | $> 0$ |
| **Unpersisted Nullifiers after Crash** | $0$ | $> 0$ |
| **Dirty Store Quarantine Accuracy** | $100.0\%$ damaged records quarantined | $< 100.0\%$ |
| **Dirty Store Panics / Unhandled Aborts** | $0$ | $> 0$ |
| **Envelope Skew Fail-Closed Ratio** | $100.0\%$ (all malformed/skewed frames rejected) | $< 100.0\%$ |
| **Authoritative Background Loops** | $0$ (Article 4 strict) | $> 0$ |
| **Direct Storage Writers** | $0$ (Article 1 strict) | $> 0$ |
| **Unsafe Blocks Added** | $0$ (`#![forbid(unsafe_code)]`) | $> 0$ |
| **External Dependencies Added** | $0$ (Zero-dependency closure) | $> 0$ |

---

## 4. The 5 Write Lifecycle Cut-Points

To test Hypothesis H9D-2, the crash simulator tests abrupt interruption at:
1. **Cut-Point $\text{CP}_1$ (Pre-Nullifier):** Interruption before the nullifier journal is written. *Expected: capability unburned, state unmutated.*
2. **Cut-Point $\text{CP}_2$ (Post-Nullifier Fsync, Pre-Store Commit):** Interruption after nullifier is synced to disk, before storage commit. *Expected: capability consumed (burned), zero state mutation applied, restart recognizes burned nullifier and rejects replay.*
3. **Cut-Point $\text{CP}_3$ (Mid-Delta Application):** Interruption during atomic store write. *Expected: LMDB transaction rollback, zero partial records committed.*
4. **Cut-Point $\text{CP}_4$ (Post-Commit, Pre-Receipt):** Interruption after commit completes, before receipt file is flushed. *Expected: state is at epoch $E+1$, receipt can be reconstructed deterministically from store event log.*
5. **Cut-Point $\text{CP}_5$ (Restart & Journal Re-open):** Store opened after crash. *Expected: `open_durable` or `Substrate::open` succeeds with `journal_ok() == true` and epoch matching last committed transaction.*

---

## 5. Preregistration Ratification

- **Pre-Registration Timestamp:** 2026-09-25T02:45:00Z  
- **Ratified By:** Antigravity & Lucas  
- **Review Channel:** Sangha Whiteboard Agora (`http://127.0.0.1:8787`)
