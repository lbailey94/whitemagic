# WhiteMagic v9 — packages the RELEASED binary, does not compile.
# Tiny build: fetch the static musl build + checksum from the GitHub
# release, verify, install. See docs/DOCKER_HUB_RUNBOOK.md.
#
#   docker build --build-arg WM_VERSION=v9 -t whitemagic:9 .
#   docker buildx build --platform linux/amd64,linux/arm64 --push \
#     --build-arg WM_VERSION=v9 -t whitemagic:9 .
#   docker run --rm whitemagic:9 --version
ARG ALPINE_VERSION=3.21
FROM alpine:${ALPINE_VERSION}

ARG WM_VERSION=v9.2.7
ARG WM_TARGET=musl
# Explicit arch override for classic `docker build`; with buildx, TARGETARCH
# is mapped automatically (amd64 -> x86_64, arm64 -> aarch64).
ARG WM_ARCH=
ARG TARGETARCH

# Required by the official MCP registry (ownership proof for the OCI
# package reference in npm/whitemagic-mcp/server.json).
LABEL io.modelcontextprotocol.server.name="io.github.lbailey94/whitemagic-mcp" \
      org.opencontainers.image.title="WhiteMagic MCP server" \
      org.opencontainers.image.version="9.2.7" \
      org.opencontainers.image.url="https://whitemagic.dev" \
      org.opencontainers.image.source="https://github.com/lbailey94/whitemagic"

RUN set -eu; \
    arch="${WM_ARCH:-}"; \
    if [ -z "$arch" ]; then \
      case "${TARGETARCH:-amd64}" in \
        amd64) arch=x86_64 ;; \
        arm64) arch=aarch64 ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
      esac; \
    fi; \
    asset="wm-linux-${arch}-${WM_TARGET}"; \
    apk add --no-cache curl coreutils; \
    curl -fsSL "https://github.com/lbailey94/whitemagic/releases/download/${WM_VERSION}/${asset}" \
      -o "/tmp/${asset}"; \
    curl -fsSL "https://github.com/lbailey94/whitemagic/releases/download/${WM_VERSION}/${asset}.sha256" \
      -o "/tmp/${asset}.sha256"; \
    (cd /tmp && sha256sum -c "${asset}.sha256"); \
    install -m 0755 "/tmp/${asset}" /usr/local/bin/wm; \
    rm -f "/tmp/${asset}" "/tmp/${asset}.sha256"

# Local install-funnel attribution: the binary records `docker` as the
# arrival channel on-device only (scope 1 — no transport, nothing sent).
ENV WM_INSTALL_CHANNEL=docker

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/wm"]
# Default to the MCP stdio server so `docker run -i <image>` speaks MCP
# directly (registry introspection, Glama checks, MCP clients). Use
# `docker run --rm <image> --version` for the version.
CMD ["serve"]
