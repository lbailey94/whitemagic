# ═══════════════════════════════════════════════════════════════════════
# WhiteMagic v25.0.0 — Multi-stage Dockerfile (3 targets: seed/core/heavy)
# ═══════════════════════════════════════════════════════════════════════
#
# Targets:
#   docker build --target seed  -t whitemagic:seed  .   # Rust binary only (~20MB)
#   docker build --target core  -t whitemagic:core  .   # Python + fastembed (~200MB)
#   docker build -t whitemagic:heavy .                   # Full ML + polyglot (~1GB)
#
# Run:
#   docker run --rm -i whitemagic:seed                   # MCP stdio (30 tools, zero Python)
#   docker run --rm -i whitemagic:core                   # MCP stdio (Seed mode, 829 tools)
#   docker run --rm -i -e WM_MCP_PRAT=0 whitemagic:core  # MCP classic (801 tools)
#   docker run --rm -p 8770:8770 whitemagic:core \
#     python -m whitemagic.run_mcp_lean --http --port 8770
#
# Persistent state:
#   docker run --rm -i -v ~/.whitemagic:/data/whitemagic whitemagic:core

# ── Stage 1: Rust Builder ────────────────────────────────────────────
FROM rust:1.82-slim AS rust-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY core/whitemagic-rust/ /build/whitemagic-rust/
COPY core/whitemagic-math/ /build/whitemagic-math/

WORKDIR /build/whitemagic-rust

# Build wm-seed binary (statically linked, no Python needed)
RUN cargo build --release --bin wm-seed \
    && cp target/release/wm-seed /build/wm-seed

# Build Python extension wheel (optional, for core/heavy targets)
RUN cargo install maturin --version 1.7.0 2>/dev/null || pip install maturin
RUN maturin build --release --out /build/dist --manylinux off || true

# Ensure dist exists
RUN mkdir -p /build/dist && touch /build/dist/.empty

# ── Stage 2: Seed Runtime (Rust binary only, ~20MB) ──────────────────
FROM debian:bookworm-slim AS seed

LABEL org.opencontainers.image.title="WhiteMagic Seed" \
      org.opencontainers.image.description="Zero-dependency MCP memory server — 30 tools, Rust binary" \
      org.opencontainers.image.version="25.0.0" \
      org.opencontainers.image.source="https://github.com/lbailey94/whitemagic" \
      org.opencontainers.image.licenses="MIT"

COPY --from=rust-builder /build/wm-seed /usr/local/bin/wm-seed

RUN mkdir -p /data/whitemagic/memory

ENV WM_STATE_ROOT=/data/whitemagic \
    WM_DB_PATH=/data/whitemagic/memory/whitemagic.db

HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD wm-seed health || exit 1

CMD ["wm-seed", "serve"]

# ── Stage 3: Core Runtime (Python + fastembed, ~200MB) ───────────────
FROM python:3.12-slim AS core

LABEL org.opencontainers.image.title="WhiteMagic" \
      org.opencontainers.image.description="The Cognitive OS for Agentic AI — 829 MCP tools" \
      org.opencontainers.image.version="25.0.0" \
      org.opencontainers.image.source="https://github.com/lbailey94/whitemagic" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="whitemagic-ai"

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 wm && mkdir -p /data/whitemagic && chown wm:wm /data/whitemagic

# Copy project metadata first (layer caching)
COPY --chown=wm:wm core/pyproject.toml /app/pyproject.toml
COPY --chown=wm:wm core/VERSION /app/VERSION
COPY --chown=wm:wm README.md LICENSE /app/

# Copy Python package
COPY --chown=wm:wm core/whitemagic/ /app/whitemagic/

# Install WhiteMagic with MCP + fastembed + CLI
RUN uv pip install --system --no-cache ".[mcp,cli]"

# Install Rust accelerator wheel (optional, auto-detected)
COPY --from=rust-builder /build/dist/ /tmp/dist/
RUN if ls /tmp/dist/*.whl 2>/dev/null; then uv pip install --system /tmp/dist/*.whl; fi \
    && if [ -f /tmp/dist/wm-seed ]; then cp /tmp/dist/wm-seed /usr/local/bin/wm-seed; fi \
    && rm -rf /tmp/dist

# Copy supporting files
COPY --chown=wm:wm core/scripts/ /app/scripts/
COPY --chown=wm:wm llms.txt /app/llms.txt

USER wm

# Environment
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    WM_STATE_ROOT=/data/whitemagic \
    WM_DB_PATH=/data/whitemagic/memory/whitemagic.db \
    WM_SILENT_INIT=1 \
    WM_MCP_PRAT=2

HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD python -c "from whitemagic.tools.unified_api import call_tool; assert call_tool('capabilities')['status']=='success'" || exit 1

EXPOSE 8770

CMD ["python", "-m", "whitemagic.run_mcp_lean"]

# ── Stage 4: Heavy Runtime (full ML + polyglot, ~1GB) ────────────────
FROM core AS heavy

USER root

# Install heavy ML dependencies
RUN uv pip install --system --no-cache ".[heavy]"

# Copy polyglot source trees (no Mojo — removed in v23.2.0)
COPY polyglot/whitemagic-zig/src/ /app/whitemagic-zig/src/
COPY polyglot/whitemagic-jl/src/ /app/whitemagic-julia/src/
COPY polyglot/whitemagic-hs/src/ /app/haskell/src/
COPY polyglot/elixir/lib/ /app/elixir/lib/

# Install additional Python extras
RUN uv pip install --system --no-cache ".[api,tui]" 2>/dev/null || true

USER wm

CMD ["python", "-m", "whitemagic.run_mcp_lean"]
