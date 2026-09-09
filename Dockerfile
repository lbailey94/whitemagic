# WhiteMagic v9 — packages the RELEASED binary, does not compile.
# Tiny build: fetch the static musl build + checksum from the GitHub
# release, verify, install. See docs/DOCKER_HUB_RUNBOOK.md.
#
#   docker build --build-arg WM_VERSION=v9 -t whitemagic:9 .
#   docker run --rm whitemagic:9 --version
ARG ALPINE_VERSION=3.21
FROM alpine:${ALPINE_VERSION}

ARG WM_VERSION=v9
ARG WM_ARCH=x86_64
ARG WM_TARGET=musl

RUN apk add --no-cache curl coreutils \
 && curl -fsSL \
      "https://github.com/lbailey94/whitemagic/releases/download/${WM_VERSION}/wm-linux-${WM_ARCH}-${WM_TARGET}" \
      -o "/tmp/wm-linux-${WM_ARCH}-${WM_TARGET}" \
 && curl -fsSL \
      "https://github.com/lbailey94/whitemagic/releases/download/${WM_VERSION}/wm-linux-${WM_ARCH}-${WM_TARGET}.sha256" \
      -o "/tmp/wm-linux-${WM_ARCH}-${WM_TARGET}.sha256" \
 && (cd /tmp && sha256sum -c "wm-linux-${WM_ARCH}-${WM_TARGET}.sha256") \
 && install -m 0755 "/tmp/wm-linux-${WM_ARCH}-${WM_TARGET}" /usr/local/bin/wm \
 && rm -f "/tmp/wm-linux-${WM_ARCH}-${WM_TARGET}" "/tmp/wm-linux-${WM_ARCH}-${WM_TARGET}.sha256"

WORKDIR /workspace
ENTRYPOINT ["/usr/local/bin/wm"]
CMD ["--version"]
