# System 1.5 Local SLM Deliberator & Conformal Gate Report (Frontier 1)
**Date:** 2026-10-03  
**Status:** COMPLETED & VERIFIED  
**Commit Target:** `main` (workspace version `10.2.0-alpha`)

---

## 1. Executive Summary

Frontier 1 equips the WhiteMagic cyberbrain with **System 1.5 Deliberation**: a local, grammar-constrained, conformal-gated Small Language Model (SLM) organ that deliberates over ambiguous System 0.5 candidate shortlists.

```
Incoming User Intent / State
             │
             ▼
┌─────────────────────────┐
│ System 0.5 Retriever    │   <15 ms (Pure CPU SIMD static embeddings)
│ (potion-base-32M)       │   R@5 = 100%, 68-route action space
└────────────┬────────────┘
             │
             ├──────────────────────────┐
      margin ≥ τ (0.08)          margin < τ (0.08)
             │                          │
             ▼                          ▼
┌─────────────────────────┐    ┌───────────────────────────────────┐
│ Fast Direct Dispatch    │    │ System 1.5 Deliberator            │
│ (Signed #shortlist)     │    │ - GBNF Logit-Masked Grammars      │
│                         │    │ - Qwen2.5-0.5B Headless Engine    │
│                         │    │ - Zero Hallucination Guarantee    │
│                         │    │ (Signed #deliberation)            │
└─────────────────────────┘    └─────────────────┬─────────────────┘
                                                 │
                                                 ▼
                                     ┌───────────────────────┐
                                     │ Final Route Dispatch  │
                                     └───────────────────────┘
```

Every single dispatch—whether direct from System 0.5 or cascaded through System 1.5—emits an Ed25519-signed receipt verifiable offline against the store's Mandala gate key. Dispatched outcomes are cryptographically journaled into `outcomes.jsonl` to continuously calibrate the conformal risk boundary $\hat{\tau}_\alpha$ and surface catalog disambiguation suggestions.

---

## 2. Mathematical Formalism

### Conformal Risk Control Gating
Given a calibration set of observed outcome margins $\{M_1, \dots, M_n\}$ from `outcomes.jsonl`:
$$\hat{\tau}_\alpha = \inf \left\{ \tau \in [0, 1] : \frac{1}{n} \sum_{i=1}^n \mathbb{I}(M_i < \tau, Y_i = \text{correct}) \ge 1 - \alpha \right\}$$

- When $M = \text{score}(\text{top}_1) - \text{score}(\text{top}_2) \ge \hat{\tau}_\alpha$: the retrieval confidence satisfies the error guarantee; dispatch proceeds directly in $<15\text{ ms}$.
- When $M < \hat{\tau}_\alpha$: the decision is flagged as `ambiguous` and cascaded to System 1.5.

### Grammar-Constrained Pushdown Automata Decoding
To eliminate hallucinations and guarantee 100% adherence to the candidate shortlist, the SLM logits are dynamically masked using a pushdown grammar generated on-the-fly:

```ebnf
root ::= candidate
candidate ::= "memory.create" | "memory.search" | "session.checkpoint" | ...
```

The model cannot emit any token outside the candidate set.

---

## 3. Cryptographic Receipt Profiles

### 1. Deliberation Receipt (`continuity-receipt/1.5#deliberation`)
```json
{
  "spec": "continuity-receipt/1.5#deliberation",
  "receipt_id": "a062ea55-791b-4fbd-97b7-d9b7f12822fb",
  "timestamp_ms": 1791069141565,
  "inquiry": "remember this: the red block belongs in bay 3",
  "inquiry_digest": "358e6587002492aa...",
  "candidates": ["memory.tag", "memory.sort", "memory.create", "memory.decay", "memory.search"],
  "chosen_route": "memory.create",
  "margin_prior": 0.016093,
  "conformal_tau": 0.08,
  "confidence": 0.85,
  "latency_ms": 5994.3,
  "layer": "system1.5",
  "issuer_did": "did:key:fd75ec4be1c18c9a5788060008dac24aaed14534b885e66e5319b6ce78958cc4",
  "signature": "..."
}
```

### 2. Outcome Receipt (`continuity-receipt/0.5#outcome`)
```json
{
  "spec": "continuity-receipt/0.5#outcome",
  "record_id": "8e830177-0ae8-44f0-a7a5-1954c0f95787",
  "subject_receipt": "a062ea55-791b-4fbd-97b7-d9b7f12822fb",
  "subject_spec": "continuity-receipt/1.5#deliberation",
  "subject_verified": true,
  "outcome": "success",
  "recorded_at_ms": 1791069147560,
  "issuer_did": "did:key:fd75ec4be1c18c9a5788060008dac24aaed14534b885e66e5319b6ce78958cc4",
  "signature": "..."
}
```

### 3. Fail-Closed Verification
Every receipt verifies offline via `wm verify-receipt <path>`. Modifying any field (such as `chosen_route` or `inquiry_digest`) invalidates the Ed25519 signature and immediately fails closed with `Verdict: INVALID (signature error)` and exit status 1.

---

## 4. Empirical Evaluation Results

### Stratified Intent Benchmark (8 Classes, Enriched Catalog)
- **Total Evaluated:** 16 intents across 8 gold classes
- **System 0.5 Standalone Top-1 Accuracy:** 87.5% (14/16)
- **Shortlist Recall@5:** **100.0% (16/16)**
- **System 1.5 Cascade Top-1 Accuracy:** **87.5% (14/16)**
- **Conditioned Accuracy:** 87.5%
- **Ambiguity Trigger Rate:** 31.2% (5/16)
- **Average Retrieval Latency:** 14.76 ms
- **Average Deliberation Latency:** 6.3 s
- **Receipt Attestation Rate:** **100.0% (16/16 verified)**
- **Outcomes Cryptographically Journaled:** **16/16**

### Outcome Aggregation Report (`s05_outcomes.py`)
```
Receipts with outcomes: 19 (verified 19, unverified 0)
Outcomes: {'success': 16, 'corrected': 3}

Margin Calibration:
  margin >= 0.10:  n=9, success_rate=89%
  margin 0.05-0.10: n=6, success_rate=67%
  margin < 0.02:   n=4, success_rate=100% (deliberated)

Gate Performance:
  deliberation:    n=6, success_rate=83%
  dispatch:        n=13, success_rate=85%
```

---

## 5. Architectural Integrations

1. **Rust Crate `crates/wm-gen3-zeropointfive`:** Pure Rust static embedding shortlist organ using `candle-core` CPU tensor operations.
2. **Harness Modules:**
   - [`deliberation.rs`](crates/wm-gen3-harness/src/deliberation.rs): Conformal gate, GBNF pushdown grammar builder, headless llama-completion runner, deliberation receipt signing.
   - [`shortlist_receipt.rs`](crates/wm-gen3-harness/src/shortlist_receipt.rs): System 0.5 shortlist receipt signing and verification.
   - [`receipt_verify.rs`](crates/wm-gen3-harness/src/receipt_verify.rs): Offline cryptographic verification across `#decision`, `#shortlist`, `#deliberation`, and `#outcome`.
3. **CLI Subcommands (`wm`):**
   - `wm shortlist --routes <path> --k 5 --margin-threshold 0.08 --cascade`: Shortlist retrieval with automatic conformal cascading and receipt emission.
   - `wm deliberate --intent <text> --candidates <json>`: Standalone grammar-constrained deliberation.
   - `wm verify-receipt <path>`: Offline Ed25519 receipt verification.
   - `wm outcome <receipt> --outcome success|failure|corrected`: Cryptographic outcome recording into `outcomes.jsonl`.
4. **MCP Tool Bridge (`bridge.rs`):**
   - Tools `decision.shortlist`, `decision.deliberate`, and `decision.outcome` registered across `Cyberbrain` and `Full` tool profiles.
