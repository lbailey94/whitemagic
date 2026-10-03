# RECEIPT — Dependency exception: local embeddings (semantic projection primitive)

**Date:** 2026-09-16 · **Status:** approved by the operator with the successor experiment ·
**Scope:** GEN3-P2B-PROJECTION-001 only (all other work keeps the manifest's embedding deferral).
Authority: `docs/DEPENDENCY_MANIFEST.md` §5 — any addition to the allowed surface requires a
contamination-boundary exception receipt naming the dependency, the need, the alternative
considered, and the expected effect on the experiment.

---

## 1. Dependency named

| Item | Version / identity |
|---|---|
| Crate | `fastembed` 5.17.4 (+ `ort` 2.0.0-rc.13, `ort-sys` 2.0.0-rc.13, `tokenizers` 0.22.2) — offline cargo cache |
| Model | `Qdrant/bge-small-en-v1.5-onnx-Q`, snapshot ref `52398278842ec682c6f32300af41344b1c0b0bb2`, local fastembed cache |
| Execution | fully local/offline; CLS pooling as implemented by fastembed for BGE-small; 384-dim; L2-normalized; cosine similarity; **brute force over cached vectors — no ANN** |

### Pinned artifact hashes

| File | sha256 |
|---|---|
| `model_optimized.onnx` | `51f1bd0addd6e859e42c2c8021a5e5461385bb676a649f4b269aa445449f2431` |
| `tokenizer.json` | `d241a60d5e8f04cc1b2b3e9ef7a4921b27bf526d9f6050ab90f9267a1f9e5c66` |
| `config.json` | `13582bcf2effc85b7bf3d3f5532e686bc1c9ce86bb009d10f0ec33cbe92299dd` |
| `tokenizer_config.json` | `0b29c7bfc889e53b36d9dd3e686dd4300f6525110eaa98c76a5dafceb2029f53` |
| `special_tokens_map.json` | `5d5b662e421ea9fac075174bb0688ee0d9431699900b90662acd44b2a350503a` |

Disallowed: fine-tuning; test-corpus vocabulary augmentation; query rewriting; benchmark labels
or fixture metadata; ANN infrastructure; any second model; any parameter tuned on benchmark
outcomes (thresholds are calibrated on the pre-registered genericity battery only).

## 2. Need

Phase 2 falsified the substitution claim and localized the gap: lexical reach produced T8 0/15
(zero query/corpus token overlap) and T1/T6 R@5 80 % vs R@1 50 %; relation candidacy had 89.7 %
recall / 1.06 % precision over ~61 k pairs/seed. The successor hypothesis tests whether a
**corpus-independent semantic projection** improves both sides of the same geometric deficiency.
Evaluating that hypothesis requires a semantic geometry; the manifest defers embeddings, so this
exception exists precisely for the case where empirical evidence demands the addition.

## 3. Alternative considered

- **PPMI/SVD geometry fitted on the evaluation corpus** — no new dependency, but fitted on the
  test distribution; would undercut the corpus-independence claim before it is tested. Deferred
  as a separate future question (developmental representation learning), not used here.
- **ANN index (HNSW/FAISS)** — rejected: adds a second retrieval mechanism and parameters; the
  corpus is small enough for exact cosine scans.
- **No projection (defer)** — rejected: leaves the identified primitive untested.

## 4. Expected effect on the experiment

- One new primitive only, behind `WM_GEN3_PROJECTION` (default off); frozen cells C00/C01 (S-off)
  are unchanged code paths.
- Ingest/query cost increases from embedding computation; measured separately **and** included in
  end-to-end totals, so the projection cannot appear to win by externalizing compute.
- Storage: vectors cached per record (content-hash keyed) inside the Gen3 store; no change to
  record/relation semantics; provenance and closure properties unaffected (embedding is an index
  artifact, not evidence).
- Contamination boundary: none of the forbidden Gen2 behavioral machinery is imported; the
  embedding dependency is infrastructure (allowed-surface addition), not behavior under test.

## 5. Rules recorded

1. This exception is scoped to GEN3-P2B-PROJECTION-001; other work remains under the manifest's
   deferral until a separate revision.
2. Any change to the model artifact, runtime versions, pooling/normalization, or the pinned
   thresholds re-baselines the experiment (new implementation-freeze receipt).
3. The model files are referenced in place from the local cache and hash-pinned; no network
   access is used at run time.
