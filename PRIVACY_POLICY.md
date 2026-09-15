# WhiteMagic Privacy Policy

**Effective Date**: 2026-08-13
**Version**: 9.1.6

## Summary

WhiteMagic is a **local-first** memory and session-continuity server for AI
agents. The summary is simple: your data stays on your machine. There is no
account, no cloud backend, and no telemetry transmitted off-device. Local
diagnostic evidence (e.g., RSI friction records) is recorded on-device and
stays there unless you explicitly share it.

## What We Collect

Nothing is uploaded by default. WhiteMagic does not send your data off your
machine:

- **No telemetry transmitted.** No usage statistics, crash reports, prompts,
  memories, or analytics are sent to us or to any third party. WhiteMagic does
  keep local diagnostic evidence on-device for its own self-observation; it
  never leaves the machine unless you explicitly opt in to sharing.
- **No accounts.** There is no sign-up, no email collection, no API keys
  managed by us.
- **Update checks are the only default outbound request.** `wm grimoire` and
  `wm update check` fetch a public, static release manifest; no identifiers,
  memories, or usage data are attached. All other outbound requests happen
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
