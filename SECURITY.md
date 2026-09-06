# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 5.8.x   | :white_check_mark: |
| < 5.8    | :x:                |

## Reporting a Vulnerability

We take the security of WhiteMagic seriously. If you have discovered a
security vulnerability, please report it privately.

**Do NOT file a public issue.**

Instead, please report vulnerabilities by:

1. Opening a GitHub Security Advisory (preferred)
2. Emailing security@whitemagic.dev

Please include:

- Description of the vulnerability
- Steps to reproduce
- Affected versions
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and provide a detailed response
within 7 days.

## Security Model

WhiteMagic v5 is a trusted local single-user process. Its security model:

- **Local-first by default**: all data stays in the local LMDB store; no
  telemetry is sent anywhere.
- **Curated tool surface**: the release profile exposes the memory/session
  workflow; the 229-tool archive surface is opt-in.
- **Destructive confirmation**: 9 destructive tools require an explicit
  `route=` match plus `confirm: true` and are structurally unreachable via
  natural-language routing.
- **Read-only mode**: `--readonly` refuses every tool that declares writes and
  suppresses karma, friction, and mutable-state persistence.
- **Fail-closed compartments**: unknown compartment values get no read or
  write access.
- **Privacy flags**: `is_private` memories never appear in MCP read/search/
  list/query responses; `model_exclude` memories never enter model context or
  reasoning evidence.
- **Exact transactions**: `transaction.begin/rollback` snapshot and restore
  byte-equivalent records; rollback failures stay retryable.
- **Karma chain**: SHA-256 hash chain over dispatch records, with optional
  external Merkle anchors for tamper evidence.
- **Input validation**: request budgets, rate limiting, parameter caps,
  injection filtering, SSRF protection, and path-traversal protection at the
  MCP boundary.

Important: `_meta.user_id` from an MCP client is not an authenticated
identity. Do not deploy the MCP server as a multi-tenant authorization
boundary.
