# WhiteMagic Workspace Justfile
# Install just: cargo install just || pip install just

set dotenv-load

# Default: show available recipes
default:
    @just --list

# === Setup ===

# Create virtual environment and install dev dependencies (recommended for development)
setup:
    python3 -m venv .venv
    .venv/bin/pip install -e core/.[dev,mcp,cli]
    @echo "✓ Dev environment created. Run: source .venv/bin/activate"

# Lite setup for MCP server only (minimal dependencies)
setup-lite:
    python3 -m venv .venv
    .venv/bin/pip install -e core/.[lite]
    @echo "✓ Lite installation complete. Run: source .venv/bin/activate"

# Full setup with ML stack
setup-heavy:
    python3 -m venv .venv
    .venv/bin/pip install -e core/.[heavy-tier]
    @echo "✓ Full installation complete. Run: source .venv/bin/activate"

# === Running ===

# Start MCP server (full, with all tools)
mcp:
    PYTHONPATH=core .venv/bin/python3 -m whitemagic.run_mcp

# Start lean MCP server (28 PRAT Ganas only, faster startup)
mcp-lean:
    PYTHONPATH=core .venv/bin/python3 -m whitemagic.run_mcp_lean

# Start MCP server with HTTP transport
mcp-http:
    PYTHONPATH=core .venv/bin/python3 -m whitemagic.run_mcp_lean --http

# === Building ===

# Build Rust extension
build-rust:
    cd core/whitemagic-rust && maturin develop --release --features python

# Build WASM math library
build-wasm:
    cd core/whitemagic-math && cargo build --target wasm32-unknown-unknown --release --features wasm

# Build Mojo kernels (requires pixi)
build-mojo:
    cd polyglot/mojo && pixi run mojo build -I src hot_paths.mojo

# === Testing ===

# Run Python test suite (parallel with xdist + progress bar)
test:
    PYTHONPATH=core .venv/bin/python3 -m pytest core/tests/ \
        --ignore=core/tests/archive_v14 \
        --ignore=core/tests/archive_v11 \
        --ignore=core/tests/archive \
        --ignore=core/tests/archive_polyglot \
        --ignore=core/tests/legacy \
        --ignore=core/tests/adhoc \
        --ignore=core/tests/verify \
        --ignore=core/tests/benchmarks \
        --ignore=core/tests/pre_v4.5.0_reorganization \
        --ignore=core/tests/pending \
        --ignore=core/tests/archive_v4.5.0_reorg \
        -n auto --dist=loadgroup \
        --progress \
        --timeout=30 \
        -q

# Run fast subset only (unit tests, fail-fast)
test-fast:
    PYTHONPATH=core .venv/bin/python3 -m pytest core/tests/unit/ \
        -n auto --dist=loadgroup \
        --progress \
        --timeout=5 \
        -x --tb=short -q

# Run test gauntlet: tier1 (unit) → tier2 (integration) → tier3 (full)
test-gauntlet:
    @echo "=== Tier 1: Unit tests (<30s target) ===" && \
    PYTHONPATH=core .venv/bin/python3 -m pytest core/tests/unit/ \
        -n auto --dist=loadgroup --progress --timeout=5 -x --tb=short -q && \
    echo "=== Tier 2: Integration tests (<3min target) ===" && \
    PYTHONPATH=core .venv/bin/python3 -m pytest core/tests/integration/ \
        -n auto --dist=loadgroup --progress --timeout=15 -x --tb=short -q && \
    echo "=== Tier 3: Full suite ===" && \
    PYTHONPATH=core .venv/bin/python3 -m pytest core/tests/ \
        --ignore=core/tests/archive_v14 --ignore=core/tests/archive_v11 \
        --ignore=core/tests/archive --ignore=core/tests/archive_polyglot \
        --ignore=core/tests/legacy --ignore=core/tests/adhoc \
        --ignore=core/tests/verify --ignore=core/tests/benchmarks \
        --ignore=core/tests/pre_v4.5.0_reorganization --ignore=core/tests/pending \
        --ignore=core/tests/archive_v4.5.0_reorg \
        -n auto --dist=loadgroup --progress --timeout=30 -q

# Boost dev environment (compile cache clears and flags)
boost:
    ./core/scripts/dev_env_boost.sh

# Run Python tests with coverage
test-cov:
    PYTHONPATH=core .venv/bin/python3 -m pytest core/tests/ \
        --ignore=core/tests/archive_v14 --ignore=core/tests/archive_v11 \
        --ignore=core/tests/archive --ignore=core/tests/archive_polyglot \
        --ignore=core/tests/legacy --ignore=core/tests/adhoc \
        --ignore=core/tests/verify --ignore=core/tests/benchmarks \
        --ignore=core/tests/pre_v4.5.0_reorganization --ignore=core/tests/pending \
        --ignore=core/tests/archive_v4.5.0_reorg \
        -n auto --dist=loadgroup \
        --cov=whitemagic --timeout=30 -q

# Run Rust tests
test-rust:
    cd core/whitemagic-rust && cargo test --release

# Run all tests
test-all: test test-rust

# Run stub audit
check-stubs:
    cd core && .venv/bin/python3 scripts/check_stubs.py

# Run duplicate code audit
check-duplicates:
    cd core && .venv/bin/python3 scripts/check_duplicates.py

# Run doc drift check
check-docs:
    cd core && .venv/bin/python3 scripts/check_doc_drift.py

# Sync stub registry to allowlist JSON
sync-stubs:
    cd core && .venv/bin/python3 scripts/sync_stub_registry.py

# === Linting ===

# Lint Python code
lint:
    cd core && .venv/bin/python3 -m ruff check whitemagic/ tests/

# Format Python code
format:
    cd core && .venv/bin/python3 -m black whitemagic/ tests/ && .venv/bin/python3 -m isort whitemagic/ tests/

# Type check
typecheck:
    cd core && .venv/bin/python3 -m mypy whitemagic/interfaces/ whitemagic/tools/ --strict

# === Database ===

# Run VACUUM on the working database
vacuum:
    sqlite3 data/whitemagic_working.db "VACUUM;"

# Check database integrity
db-check:
    sqlite3 data/whitemagic_working.db "PRAGMA integrity_check;"

# Show database statistics
db-stats:
    sqlite3 data/whitemagic_working.db "SELECT 'memories', COUNT(*) FROM memories UNION ALL SELECT 'associations', COUNT(*) FROM associations UNION ALL SELECT 'embeddings', COUNT(*) FROM memory_embeddings UNION ALL SELECT 'holographic_coords', COUNT(*) FROM holographic_coords;"

# === Utilities ===

# Generate llms.txt from tool registry
llms-txt:
    PYTHONPATH=core .venv/bin/python3 core/scripts/generate_llms_txt.py

# System health check
doctor:
    @echo "=== Python ===" && python3 --version
    @echo "=== Rust ===" && rustc --version 2>/dev/null || echo "Not installed"
    @echo "=== Node ===" && node --version 2>/dev/null || echo "Not installed"
    @echo "=== Database ===" && sqlite3 data/whitemagic_working.db "PRAGMA integrity_check;" 2>/dev/null || echo "DB not found"
    @echo "=== Venv ===" && test -d .venv && echo "Present" || echo "Missing (run: just setup)"

# Clean build artifacts
clean:
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null
    find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null
    find . -type f -name "*.pyc" -delete 2>/dev/null
    rm -rf core/whitemagic_rust.egg-info/ core/dist/ core/build/
    @echo "✓ Cleaned build artifacts"
