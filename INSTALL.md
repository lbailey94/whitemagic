# Installing WhiteMagic Gen3 from source

Product binary: `wm` (the `wm-gen3` harness binary is a companion surface, not
the product). Releases ship prebuilt assets for Linux x86-64/arm64, macOS
arm64, and Windows x86_64; this document covers source builds and the model
layer, which is local but not bundled.

## 1. Build

Prerequisites: Rust (see `rust-toolchain.toml`; the pin is rustup-style — a
Homebrew `cargo` ignores it, so either install rustup or match the pinned
version) and a C toolchain.

```sh
git clone https://github.com/lbailey94/whitemagic
cd whitemagic
cargo build --release
target/release/wm --version
```

The build is small (six-crate workspace, no native system libraries). Keep the
target directory on an SSD for faster iteration.

## 2. Store

```sh
wm init --store ~/.local/share/whitemagic-gen3
wm status --store ~/.local/share/whitemagic-gen3
```

Without `--store` the CLI uses its default store location. Gen3 stores are
versioned (`validate_header`); a store written by a different format version
refuses to open rather than migrating silently.

## 3. Model layer (all local, all optional)

### System 0.5 — retrieval organ (potion-base-32M)

Place the Model2Vec checkpoint where the resolver finds it:
`~/.local/share/whitemagic/system05/<model>/`, `~/tools/system05/<model>/`, or
set `WM_GEN3_SYSTEM05_MODEL`. The directory needs `model.safetensors`,
`tokenizer.json`, and `config.json`.

### Dense projection (recall reranking)

Warm the FastEmbed cache once:

```sh
cargo run -p wm-gen3-core --example warm_embed_cache
```

Then enable projection per call or server:

- `wm recall "query" --projection` (or `WM_GEN3_PROJECTION=1`)
- `wm serve --projection --embed-cache <cache-dir>`

The cache is enforced offline; absence fails soft to lexical recall with a
loud message. `WM_GEN3_PROJECTION_GATED=1` restores the margin gate.

### System 1.5 — local SLM deliberator

Install llama.cpp and a GGUF model, then point the harness at them:

```sh
export WM_GEN3_LLAMA_CLI=/path/to/llama-completion
export WM_GEN3_SLM_MODEL=/path/to/qwen2.5-1.5b-instruct-q4_k_m.gguf
wm deliberate "intent" --candidates '["memory.create","session.checkpoint"]'
```

`WM_GEN3_DELIBERATION_STRICT=1` refuses to sign a degraded receipt when the
SLM is unavailable or unparsable.

### System Two — local generative consultant (opt-in)

Any OpenAI-compatible local endpoint (ollama or `llama-server`):

```sh
export WM_SYSTEM2_ENDPOINT=http://127.0.0.1:11434/v1
export WM_SYSTEM2_MODEL=gemma4:e2b
wm system2 ask "what does the store say?" --context @notes.md
```

Defaults: endpoint `http://127.0.0.1:11434/v1`, model `gemma4:e2b`,
`WM_SYSTEM2_MAX_TOKENS=1024` (reasoning models need headroom), timeout 30s.
Reasoning-model responses that exhaust the token budget before emitting
content fail with a clear error. Non-loopback endpoints require
`WM_SYSTEM2_ALLOW_REMOTE=1`; every consultation signs a
`continuity-receipt/2#consultation` with model and prompt version.

## 4. Verify

```sh
wm selftest --json
wm status
WM_GEN3_EMBED_CACHE=<cache> wm recall "smoke query" --projection
cargo test --workspace
```

## 5. Platform notes

- macOS `shm_open` names are limited to 31 bytes including the leading `/`;
  `ShmSubstrate::open_or_create` validates this portably and returns a clear
  `InvalidInput` error instead of `ENAMETOOLONG`.
- Accepted mesh sockets are explicitly set to blocking mode: BSD `accept()`
  inherits `O_NONBLOCK` from the listening socket, unlike Linux.
- Landlock confinement is Linux-only; the relevant tests are gated by
  `#[cfg(target_os = "linux")]`.
