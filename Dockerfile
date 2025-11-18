# Hardened WhiteMagic Docker Image
FROM python:3.10-slim

# Install system dependencies including Rust
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y \
    && rm -rf /var/lib/apt/lists/*

ENV PATH="/root/.cargo/bin:${PATH}"

# Create non-root user
RUN groupadd -r -g 1000 whitemagic && \
    useradd -r -u 1000 -g whitemagic -s /bin/false whitemagic

# Create directories
RUN mkdir -p /app /data /tmp/whitemagic && \
    chown -R whitemagic:whitemagic /app /data /tmp/whitemagic

WORKDIR /app

# Copy and install WITH api extras
COPY --chown=whitemagic:whitemagic . .
RUN pip install --no-cache-dir ".[api]"

# Switch to non-root
USER whitemagic

# Environment
ENV PYTHONUNBUFFERED=1 JSON_LOGS=true LOG_LEVEL=INFO WM_BASE_PATH=/data PORT=8000

EXPOSE $PORT

# Healthcheck - use PORT env var
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use shell form to allow env var substitution with sh -c
CMD sh -c "uvicorn whitemagic.api.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2"
