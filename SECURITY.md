# Security Policy

> NOTE (2026-09-10, Q05 — support window under review): the table below is the
> existing policy statement; its current applicability is unverified in this
> pass and the maintainer's support-window decision is explicitly unresolved.
> Observed package/runtime versions are separate facts: the Q03 accepted gateway
> reports package 9.0.0 (see `docs/V9_3_Q03_ACCEPTANCE.md`), and v9 is the
> latest public release line. A newer package version does not establish the
> maintenance policy of an older release.

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
  workflow; the tool archive surface is opt-in (registered total 237 at the
  v5.8.0 release gate, 2026-08-20 — a dated figure, not today's exposure;
  current-build exposure is profile-selected per the Q03 generated manifest,
  with per-tool dispositions under Q04 audit).
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

## Host Identity and Delegation Stance (2026-09-10)

Context: Glama MCP-security series (MCP Dev Summit Mumbai 2026) —
host-as-identity-blind-spot (2026-07-25), confused-deputy HR demo
(2026-07-02), execution sandboxing (2026-06-30). Tracked as
`rsi:proposal:active` P-OBO-1 / P-DEPUTY-2.

- **Single-user local process.** WhiteMagic has no OAuth / OBO token
  issuance or validation, no SPIFFE workload identity, and no per-user
  scoping. The mesh node key (`WM_MESH_KEY` Ed25519, signed heartbeats)
  names a *device/node*, never a user. See
  `docs/S9_SECURITY_BRIEF_2026-09-10.md` for mesh-identity gaps and the
  pending key-separation ruling.
- **Server enforces, callers assert.** Human approval (`confirm: true`)
  is not authorization: every destructive dispatch is re-checked
  server-side (Dharma/Yama gates, firebreak veto + bulk-scope law,
  compartment checks). Routing scope (gateway top-level `scope=`) and
  tool-payload scope (inner `args.scope`, e.g. `code.claim` lease scope)
  are separate namespaces — inner scope never re-routes (Q03 regression
  `pinned_proxy_preserves_inner_args_scope`).
- **Audit carries both ends where known.** Write-audit journal entries
  record the dispatch actor from server-side context plus optional
  OBO-shaped delegation fields (`actor_act`, `actor_on_behalf_of`,
  `delegation_chain` — opaque, server-asserted, absent by default).
  Client-supplied identity claims are never trusted for authorization.
- **Four-A's self-check** (per deployment, answer honestly):
  Administer — can you name/suspend/deprovision every node holding
  credentials? Authenticate — short-lived node keys with rotation, or
  standing keys? Authorize — least-privilege profiles per store,
  destructive surface enumerated? Audit — can you replay who did what,
  through which agent, last Tuesday, from the karma chain + journal
  alone? Any "not really" is a known gap, not a silent assumption.
