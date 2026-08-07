# WhiteMagic v4 build targets

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
    python python/whitemagic_v4_server.py --store .whitemagic/lmdb

# Quickstart demo
quickstart:
    cargo run --release --bin wm -- quickstart

# Doctor (health check)
doctor:
    cargo run --release --bin wm -- doctor

# Brain-wave state
brain-wave:
    cargo run --release --bin wm -- brain-wave
