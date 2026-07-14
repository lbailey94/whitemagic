# ═══════════════════════════════════════════════════════════════════════
# WhiteMagic v25.0.0 — Multi-stage Dockerfile
# ═══════════════════════════════════════════════════════════════════════
#
# Targets:
#   docker build -t whitemagic:heavy .                    # Full Heavy (all polyglot cores)
#   docker build --target slim -t whitemagic:slim .       # Slim (Python + Rust only)
#
# Run:
#   docker run --rm -i whitemagic:heavy                   # MCP stdio (PRAT mode)
#   docker run --rm -i -e WM_MCP_PRAT=0 whitemagic:heavy # MCP classic (462 tools)
#   docker run --rm -p 8765:8765 whitemagic:heavy \
#     python -m whitemagic.interfaces.nexus_api           # REST API
#   docker run --rm whitemagic:heavy wm status            # CLI
#
# Persistent state:
#   docker run --rm -i -v ~/.whitemagic:/data/whitemagic whitemagic:heavy

# ── Stage 1: Rust Builder ────────────────────────────────────────────
FROM python:3.12-slim AS rust-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

RUN pip install --no-cache-dir maturin

COPY core/whitemagic-rust/ /build/whitemagic-rust/
COPY core/whitemagic-math/ /build/whitemagic-math/
WORKDIR /build/whitemagic-rust

# Build Python extension wheel + seed binary
# --manylinux off: we're building for this container's Python, not for PyPI distribution
RUN maturin build --release --out /build/dist --manylinux off || true
RUN (cargo build --release --bin wm-seed && cp target/release/wm-seed /build/dist/wm-seed) || true
# Ensure /build/dist exists for COPY --from to not fail
RUN mkdir -p /build/dist && touch /build/dist/.empty

# ── Stage 2: Go Builder (mesh networking) ────────────────────────────
FROM golang:1.22-bookworm AS go-builder

COPY polyglot/whitemagic-go/mesh/ /build/mesh/
WORKDIR /build/mesh
RUN go build -o /build/whitemagic-mesh .

# ── Stage 3: Slim Runtime (Python + Rust only, ~200MB) ───────────────
FROM python:3.12-slim AS slim

LABEL org.opencontainers.image.title="WhiteMagic" \
      org.opencontainers.image.description="The Tool Substrate for Agentic AI — 729 MCP tools" \
      org.opencontainers.image.version="25.0.0" \
      org.opencontainers.image.source="https://github.com/whitemagic-ai/whitemagic" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="whitemagic-ai"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first (layer caching)
COPY core/pyproject.toml /app/pyproject.toml
COPY README.md VERSION LICENSE /app/

# Copy Python package
COPY core/whitemagic/ /app/whitemagic/

# Install WhiteMagic with MCP + CLI support
RUN pip install --no-cache-dir ".[mcp,cli]"

# Install Rust acceleration and seed binary (optional)
COPY --from=rust-builder /build/dist/ /tmp/dist/
RUN if ls /tmp/dist/*.whl 2>/dev/null; then pip install --no-cache-dir /tmp/dist/*.whl; fi \
    && if [ -f /tmp/dist/wm-seed ]; then cp /tmp/dist/wm-seed /usr/local/bin/wm-seed; fi \
    && rm -rf /tmp/dist

# Copy supporting files
COPY core/scripts/ /app/scripts/
COPY core/eval/ /app/eval/
COPY llms.txt /app/llms.txt
COPY skill.md /app/skill.md

# Create state directory
RUN mkdir -p /data/whitemagic/memory /data/whitemagic/sessions \
             /data/whitemagic/logs /data/whitemagic/gratitude

# Environment
ENV PYTHONPATH=/app \
    WM_STATE_ROOT=/data/whitemagic \
    WM_DB_PATH=/data/whitemagic/memory/whitemagic.db \
    WM_SILENT_INIT=1 \
    WM_MCP_PRAT=1

# Health check
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "from whitemagic.tools.unified_api import call_tool; assert call_tool('capabilities')['status']=='success'" || exit 1

EXPOSE 8765

CMD ["python", "-m", "whitemagic.run_mcp_lean"]

# ── Stage 4: Heavy Runtime (all polyglot cores, ~800MB) ──────────────
FROM slim AS heavy

# Install mesh networking binary (Go)
COPY --from=go-builder /build/whitemagic-mesh /usr/local/bin/whitemagic-mesh

# Copy polyglot source trees (for reference / hot-loading)
COPY polyglot/whitemagic-zig/src/ /app/whitemagic-zig/src/
COPY polyglot/mojo/src/ /app/whitemagic-mojo/src/
COPY polyglot/whitemagic-jl/src/ /app/whitemagic-julia/src/
COPY polyglot/whitemagic-hs/src/ /app/haskell/src/
COPY polyglot/elixir/lib/ /app/elixir/lib/
COPY polyglot/whitemagic-go/ /app/whitemagic-go/
COPY sdk/ /app/sdk/
COPY app-layer/nexus/ /app/nexus/

# Install additional Python extras for full experience
RUN pip install --no-cache-dir ".[api,tui]" 2>/dev/null || true

CMD ["python", "-m", "whitemagic.run_mcp_lean"]
