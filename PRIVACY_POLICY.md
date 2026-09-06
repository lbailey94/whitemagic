# WhiteMagic Privacy Policy

**Effective Date**: 2026-08-13
**Version**: 5.8.0

## Summary

WhiteMagic is a **local-first** memory and session-continuity server for AI
agents. The summary is simple: your data stays on your machine. There is no
account, no cloud backend, and no telemetry.

## What We Collect

Nothing. WhiteMagic does not send any data off your machine:

- **No telemetry.** No usage statistics, crash reports, or analytics leave the
  process.
- **No accounts.** There is no sign-up, no email collection, no API keys
  managed by us.
- **No network calls by default.** The server makes outbound network requests
  only when you explicitly use a network tool (`web.*`, `research.*`) or
  configure an optional embedding/LLM endpoint (`WM_EMBEDDER_ENDPOINT`,
  `WM_LLAMA_ENDPOINT`, `WM_LLM_ENDPOINT`). Those requests go to the endpoints
  you configure.

## What Stays Local

All memory data lives in a local LMDB store (default
`~/.local/share/whitemagic/`) plus a local Tantivy search index. Optional
state files (claims ledger, mutable structure state, friction log) are also
written locally.

Memory records carry privacy flags you control:

- `is_private` — excluded from MCP read/search/list/query responses.
- `model_exclude` — excluded from model context windows and reasoning
  evidence.

## What You Should Know

- **The daemon** (`wm daemon`) performs local background consolidation
  (dream/retention/emergence cycles) on your store. It is optional.
- **Backups are yours to make.** Nothing is uploaded anywhere.
- **Deleting data**: destructive tools require explicit confirmation; the
  transaction tools provide snapshot/rollback. Once you delete a memory and
  later rewrite the store, removed records are gone (LMDB is a local file —
  forensic recovery of deleted data is possible, just like any local file).

## Changes to This Policy

This policy applies to the software as distributed in this repository. If a
hosted service is ever offered, it will have its own separate policy and will
never be silently introduced into the local build.
