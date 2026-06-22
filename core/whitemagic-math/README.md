# WhiteMagic Math

A pure-Rust, dependency-lite math library for WhiteMagic intelligence kernels.

## Overview

This crate houses the heavy numeric kernels of WhiteMagic, decoupled from OS-level dependencies like Rayon and PyO3. This enables:
1. **WASM Distribution**: Compiles to `wasm32-unknown-unknown` for web-based agents.
2. **Lightweight Integration**: Faster build times and smaller binary footprints for core logic.

## Modules

- `minhash`: Near-duplicate detection using MinHash and LSH.
- `holographic_encoder_5d`: 5D coordinate encoding for multi-dimensional memory indexing.
- `holographic`: 4D spatial index using K-D Trees.
- `embedding_minhash`: Fast duplicate detection directly on embedding vectors.

## WASM Build

```bash
cargo build --target wasm32-unknown-unknown --release --features wasm
```

The resulting `.wasm` file is optimized for size and contains no POSIX/IPC dependencies.
