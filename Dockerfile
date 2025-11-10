# Hardened WhiteMagic Docker Image
FROM python:3.10-slim

# Install runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/*

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
ENV PYTHONUNBUFFERED=1 JSON_LOGS=true LOG_LEVEL=INFO WM_BASE_PATH=/data

EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8000/health || exit 1

# Use Python module execution
CMD ["python", "-m", "uvicorn", "whitemagic.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
