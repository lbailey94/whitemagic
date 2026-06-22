# WhiteMagic v21 - Minimal Production Dockerfile
FROM python:3.11-slim-bookworm

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsqlite3-dev curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy pyproject.toml first for layer caching
COPY pyproject.toml .
RUN pip install --no-cache-dir .

# Copy application code
COPY whitemagic/ ./whitemagic/
COPY whitemagic-rust/ ./whitemagic-rust/

# Install Rust extension if available
RUN if [ -f whitemagic-rust/Cargo.toml ]; then \
    pip install maturin && \
    cd whitemagic-rust && \
    maturin build --release && \
    pip install target/wheels/*.whl; \
    fi

# Environment
ENV PYTHONPATH=/app
ENV WM_DB_PATH=/data/whitemagic.db
ENV WHITEMAGIC_MODE=cloud

# Create data volume
RUN mkdir -p /data

EXPOSE 8000

CMD ["python", "-m", "whitemagic.run_mcp"]
