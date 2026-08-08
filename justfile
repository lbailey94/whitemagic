# WhiteMagic v5 build targets

default: build

build:
    cargo build --release

dev:
    cargo build

test:
    cargo test --all

test-fast:
    cargo test --all -- --test-threads=8

lint:
    cargo clippy --all-targets --all-features

fmt:
    cargo fmt --all

fmt-check:
    cargo fmt --all -- --check

bench:
    cargo bench --all

clean:
    cargo clean

# Polyglot builds
build-julia:
    cargo build --release --features wm-polyglot/julia

build-python:
    cargo build --release --features wm-mcp/python

build-lancedb:
    cargo build --release --features wm-memory/lancedb

# Run MCP server (pure Rust)
serve:
    cargo run --release --bin wm -- serve

# Run MCP server via Python shell
serve-python:
    python python/whitemagic_v5_server.py --store .whitemagic/lmdb

# Quickstart demo
quickstart:
    cargo run --release --bin wm -- quickstart

# Doctor (health check)
doctor:
    cargo run --release --bin wm -- doctor

# Brain-wave state
brain-wave:
    cargo run --release --bin wm -- brain-wave

# Full workspace verification: fmt + clippy + tests
verify:
    cargo fmt --all -- --check
    cargo clippy --all-targets --all-features
    cargo test --all

# Remove all build artifacts (reclaims ~8GB)
prune: clean
    rm -rf .criterion
    rm -rf crates/*/benches/target
    find . -name "*.profraw" -delete 2>/dev/null
    @echo "Build artifacts removed"

# Dependency security audit (RustSec advisories + licenses + duplicate bans)
audit:
    cargo deny check

# Everything: fmt + clippy + tests + dependency audit
verify: fmt-check lint
    cargo test --all
    cargo deny check
