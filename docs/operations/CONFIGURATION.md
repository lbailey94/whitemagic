# WhiteMagic Configuration Reference

All runtime behaviour is controlled through environment variables prefixed `WM_`.
Copy `core/.env.example` to `.env` in the repo root (or `core/`) and override as needed.

---

## Core Paths

| Variable | Default | Description |
|---|---|---|
| `WM_STATE_ROOT` | `~/.whitemagic` | Root directory for all runtime state (memory DB, vault, karma ledger, logs). **Must be set before first import.** |
| `WM_ROOT` | `WM_STATE_ROOT` | Alias for `WM_STATE_ROOT` used by some subsystems. |
| `WM_BASE_PATH` | Repo root | Base directory for resolving relative paths. |
| `WM_CONFIG_ROOT` | `WM_STATE_ROOT/config` | Config YAML/TOML directory. |
| `WM_WORKSPACE_ROOT` | CWD | Working directory for autonomous executor file operations. |
| `WM_FALLBACK_TO_CWD` | `0` | If `1`, fall back to CWD when `WM_ROOT` is not set. |

---

## MCP Server

| Variable | Default | Description |
|---|---|---|
| `WM_MCP_PRAT` | `0` | Enable PRAT mode — exposes 28 Gana meta-tools instead of individual tools. Recommended for Claude Desktop. |
| `WM_MCP_LITE` | `0` | Enable lite mode — reduced toolset for constrained clients. |
| `WM_MCP_CLIENT` | (auto) | Override detected MCP client type (`claude`, `cursor`, `windsurf`, `generic`). |
| `WM_SILENT_INIT` | `0` | Suppress INFO-level startup log messages. Set to `1` in CI or tests. |
| `WM_DEBUG` | `0` | Enable DEBUG-level logging across all subsystems. |

---

## Database & Persistence

| Variable | Default | Description |
|---|---|---|
| `WM_DB_PATH` | `WM_STATE_ROOT/memory/whitemagic.db` | Hot SQLite database path. |
| `WM_DB_PASSPHRASE` | (none) | Passphrase for SQLCipher encryption. If unset, DB is unencrypted. |

---

## Security & Vault

| Variable | Default | Description |
|---|---|---|
| `WM_VAULT_PASSPHRASE` | (none) | Master passphrase for the encrypted secrets vault. If unset, vault prompts interactively or uses OS keychain. |
| `WM_ENCRYPTION_KEY` | (none) | Raw AES-256 key (base64) — alternative to `WM_VAULT_PASSPHRASE`. |
| `WM_SANDBOX_ENABLED` | `1` | Enable shell sandbox (firejail/bwrap) for tool execution. Set to `0` to disable in trusted environments. |
| `WM_ILP_AUTH_TOKEN` | (none) | ILP/Open Payments auth token for `WM_ILP_CONNECTOR_URL`. |
| `WM_ILP_CONNECTOR_URL` | (none) | ILP connector URL for micropayment routing. |
| `WM_ILP_POINTER` | (none) | Payment pointer for this WhiteMagic node (e.g. `$wallet.example.com/alice`). |

---

## Shelter (Microvm/Sandbox Tier)

| Variable | Default | Description |
|---|---|---|
| `WM_SHELTER_TIER` | `process` | Isolation tier: `none`, `process`, `firejail`, `firecracker`. |
| `WM_SHELTER_RUNTIME` | `runc` | Container runtime for `firecracker` tier. |
| `WM_SHELTER_FIRECRACKER` | `0` | Enable Firecracker microVM isolation (requires root). |
| `WM_SHELTER_TIMEOUT_S` | `30` | Default timeout (seconds) for sheltered tool execution. |
| `WM_SHELTER_MAX_CONCURRENT` | `4` | Max concurrent sheltered tool invocations. |

---

## Embedding & AI Models

| Variable | Default | Description |
|---|---|---|
| `WM_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformer model name for embedding generation. |
| `WM_ALLOW_MODEL_DOWNLOAD` | `0` | If `1`, allow automatic HuggingFace model downloads. Disable in airgapped environments. |

---

## Dream / Offline Processing

| Variable | Default | Description |
|---|---|---|
| `WM_DREAM_INSIGHTS` | `5` | Max insights generated per dream cycle. |
| `WM_DREAM_LOG_FILE` | `WM_STATE_ROOT/dream.jsonl` | Dream cycle log path. |
| `WM_DREAM_LOG_MAX_BYTES` | `10485760` (10 MB) | Max size before log rotation. |
| `WM_DREAM_LOG_BACKUPS` | `3` | Number of rotated log backups to keep. |
| `WM_DREAM_LOG_TOTAL_MAX_BYTES` | `31457280` (30 MB) | Max total log storage before oldest are pruned. |

---

## Distributed Mesh

| Variable | Default | Description |
|---|---|---|
| `WM_MESH_ADDRESS` | `localhost:9090` | gRPC listen address for the Go mesh node. |
| `WM_MESH_NODE_ID` | (auto: hostname) | Unique node identifier in the mesh. |
| `WM_AUTO_IPC` | `0` | Auto-start IPC bridge between Python and Go mesh on startup. |

---

## Autonomy & Tooling

| Variable | Default | Description |
|---|---|---|
| `WM_ENABLE_SUTRA_AUTO_EXECUTE` | `0` | Allow the Sutra kernel to auto-execute action recommendations without human approval. **High risk — leave `0` unless intentionally autonomous.** |
| `WM_AUTO_BUILD_RUST_BRIDGE` | `0` | Auto-rebuild the Rust PyO3 extension if the source is newer than the installed wheel. |
| `WM_DHARMA_PROFILE` | `default` | Dharma profile name (controls karma weights and ethical constraints). |
| `WM_TOOL_DISPATCH_TIMEOUT_S` | `30` | Default timeout for all tool dispatch calls. |
| `WM_TOOL_TIMEOUT_LOCAL_GENERATION_S` | `120` | Timeout for local LLM generation tools. |
| `WM_TOOL_TIMEOUT_AGENT_GENERATION_S` | `300` | Timeout for multi-agent generation pipelines. |
| `WM_TOOL_TIMEOUT_COLD_STATUS_S` | `5` | Timeout for cold-status polyglot health checks. |
| `WM_SKIP_HOLO_INDEX` | `0` | Skip loading the holographic HNSW index on startup. Speeds up tests and cold starts. |

---

## Observability

| Variable | Default | Description |
|---|---|---|
| `WM_OTEL_ENABLED` | `0` | Enable OpenTelemetry tracing. Requires `opentelemetry-sdk` to be installed. |
| `WM_PROMETHEUS_ENABLED` | `0` | Expose Prometheus metrics endpoint. |
| `WM_PROMETHEUS_PORT` | `9091` | Port for the Prometheus metrics HTTP server. |
| `WM_BENCHMARK_QUIET` | `0` | Suppress benchmark timing output. |

---

## Session & Identity

| Variable | Default | Description |
|---|---|---|
| `WM_SESSION_ID` | (auto: UUID) | Override the auto-generated session ID. Useful for tracing across restarts. |
| `WM_VERSION__` | (from VERSION file) | Override the reported version string. Set automatically by the build system. |

---

## XRPL / Gratitude Economy

| Variable | Default | Description |
|---|---|---|
| `WM_XRP_ADDRESS` | (none) | Public XRP receive address for tip collection. No private keys stored. |
| `WM_XRP_DEST_TAG` | (none) | Optional destination tag for exchange deposits. |

---

## Zig Bridge

| Variable | Default | Description |
|---|---|---|
| `WM_ZIG_LIB` | (auto-detected) | Path to the compiled Zig shared library (`libwhitemagic.so`). |

---

## Test / CI Overrides

| Variable | Usage |
|---|---|
| `WM_STATE_ROOT` | **Always override** in tests — point to a `tmp_path` to avoid touching the production DB. |
| `WM_SILENT_INIT=1` | Suppress startup noise in CI logs. |
| `WM_SKIP_HOLO_INDEX=1` | Skip HNSW index load (saves 3–30s per test session). |
| `WM_ALLOW_MODEL_DOWNLOAD=0` | Prevent accidental model downloads in CI. |

See `core/tests/conftest.py` for the canonical test environment setup.
