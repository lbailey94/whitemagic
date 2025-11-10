FROM python:3.10-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml setup.py VERSION ./
COPY whitemagic/ ./whitemagic/
RUN pip install --no-cache-dir --prefix=/install .

FROM python:3.10-slim
RUN apt-get update && apt-get install -y libpq5 curl && rm -rf /var/lib/apt/lists/*
RUN groupadd -r -g 1000 whitemagic && useradd -r -u 1000 -g whitemagic -s /bin/false whitemagic
RUN mkdir -p /app /data /tmp/whitemagic && chown -R whitemagic:whitemagic /app /data /tmp/whitemagic
WORKDIR /app
COPY --from=builder --chown=whitemagic:whitemagic /install /usr/local
COPY --chown=whitemagic:whitemagic . .
USER whitemagic
ENV PYTHONUNBUFFERED=1 JSON_LOGS=true LOG_LEVEL=INFO WM_BASE_PATH=/data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --retries=3 CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "whitemagic.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
