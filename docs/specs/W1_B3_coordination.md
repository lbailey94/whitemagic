# Wave-1 spec B3 — Coordination

**Status: DRAFT — compiled 2026-09-17 · NOT frozen.** Compiled per `docs/archive/research/PHASE4_WAVE_PLAN.md`
§7 at WMgen3 tip `309e111` (tree clean), under the frozen nucleus (`docs/NUCLEUS.md`, sha256
`73c5a9cf…`). **Owner: unset — operator assigns at freeze.** Docs-only. Freeze at operator
ratification + `receipts/` entry.

**Row:** Coordination (wave plan §2; `PRESERVE IMPL. → link · E12`).
**Wire:** statutes + journal; lease-ledger link.
**Nucleus touch points:** Part 1 invariant 1 (bounded effects, fail-closed) and 2 (no silent
destructive action); Part 3 statutes; delta §3.3 (typed effects + always-releasable asymmetry).
**Caution carried:** the link **must not bypass typed effects**; v26 advisory-only locks are
excluded (never re-derive locks on the Gen3 side).
**Do not re-raise:** errata A#5 (`sangha_memory_collective` name not attested; the board dirs
are the artifact); the v26 locks' non-usage is established (W1), not in question.

---

## 1. Frozen behavioral spec

### 1.1 The link contract (Gen2 lease ledger is the enforcement surface)

- **Lease fields:** `scope` + **mandatory intent** + `owner_session` + TTL (`claimed_at`,
  `expires_at`, `ttl_secs`); ledger at `<git-common-dir>/wm-leases.json`, visible across
  worktrees (`coordination.rs:46-97`; SOURCE-IMPLEMENTED + live).
- **One writer per scope;** conflicts **name the holder + intent** (never a bare refusal);
  `try_claim` / exact-owner `release`.
- **Typed effects (9.1.8, strict mode):** acquisition/renewal carry `Resource::CoordinationLease`
  and may be **refused** with typed `VIOLATION_AHIMSA` under system stress; **exact-owner release
  is always admitted** (`Resource::CoordinationRelease`) — the asymmetry is part of the contract
  (work may be refused; release never is). (delta §2.1; SOURCE-IMPLEMENTED + tests)
- **Stale is a signal, not a blocker:** TTL expiry means a claim is stale and stealable; a dead
  ceremony does not trap work (RELEASE_CADENCE discipline).
- **Read discipline:** `check`/`list` are **snapshot-readonly** — no lock, no temp file, no
  persisted expiry pruning; expired leases are **logically absent and still reportable**
  (`coordination.rs:225-236,678,902`). A read never mutates the ledger.
- **Root binding:** `release` acts only on the configured root; an alternate/escaping `root` is
  refused when `WM_PROJECT_ROOT` is set (`:750-800`).
- **No-subprocess discovery:** the ledger path resolves via filesystem git-common-dir, never a
  subprocess (9.1.9 F3 discipline; the link must not introduce subprocess discovery).
- **Board rule:** coordination state lives in the ledger + journal as records. **A shared mutable
  JSON blob is the lost-update exemplar and is not inherited** (v26 `shared_context.json` /
  `current_session.json` semantics excluded).
- **Gen3's half:** statutes + journal — the link carries the contract; no lock machinery is
  re-derived on the Gen3 side (preserve link, not port).

### 1.2 Defaults and metrics hygiene

- Handler/default artifacts (`default_resource`, `"test message"`, `agent_id="system"`) are **not
  usage**; any adoption/replay metric excludes them (v26's registry held exactly one such entry).
- Test-only artifacts stripped, the v26 coordination evidence set collapses to **zero real
  cross-session usage** — the recorded negative control for "the fleet used X" claims.

### 1.3 Failure classes named

- **Degraded lock must be loud:** if locking cannot be provided, the outcome is stated — an
  unenforced lock reporting success is the v26 failure class (`resources.py:31-36`) and is
  forbidden.
- **Two-writer postmortem:** the Gen2 incident is the reference; the contract's answer is
  conflict naming + exact-owner release + `lease_id`-verified baton, not narrative coordination.

### 1.4 Statutory parameters named (Tier-2)

Ledger location (`<git-common-dir>/wm-leases.json`) · TTL semantics (30 s stale steal; caller
TTLs) · strict-mode capability gate (`WM_REQUIRE_CAPABILITIES`) · release-cadence rule (stale
freeze = signal).

### 1.5 Non-goals

No re-derived locks on the Gen3 side · no shared mutable JSON board · no advisory-only
coordination · no subprocess discovery · no removal of the always-releasable asymmetry.

---

## 2. Selection history

**Ancestor (Gen1 v26):** `ResourceManager` advisory-only file locks — **nothing consulted a lock
before editing anything**; silent no-op fallback when `fileio` import failed; `CollectiveMemory`
single-blob board with read-modify-write and no lock (lost updates); `SessionHandoff` single-slot
baton that silently ignored a second session; `list_locks` mutated the registry while listing;
two different lock types shared one class name; the real 2026-07-16 parallel-session interference
was handled in human narration, with no lock/board writes in the record. Live registry held
exactly one default entry (test artifact).

**Selection fate:** advisory locks excluded; functional homology mapped to Gen2 `code.claim`
leases — `reason` → mandatory intent, owner-matched release → exact-owner cleanup, plus the
missing half: **enforcement at the edit seam** + conflict naming (the two-writer fix is a fix for
a failure v26's locks could not have prevented). 9.1.8 hardened the types and the asymmetry.
Board/baton → track ledger + handoff at doc altitude (added), not ported code.

**Evidence levels:** v26 organs SOURCE-IMPLEMENTED; non-usage RUNTIME-OBSERVED (registry/DB
reads); Gen2 leases SOURCE-IMPLEMENTED + live; typed effects delta-verified (9.1.8 §2.1); the
two-writer postmortem document itself remains **UNVERIFIED** (cite the incident, not a document).

---

## 3. Adversarial cases

1. **Lost update on a single-blob board** — two concurrent writers must serialize or be refused
   with a journaled refusal (v26 semantics excluded).
2. **Degraded lock must be loud** — simulate the lock-unavailable fallback; an unenforced lock
   reporting success fails the case.
3. **Stale-lease steal vs live holder** — expired takeover proceeds; a still-held claim refuses
   **naming the holder + intent**.
4. **Read-only listing must not prune** — a read never writes the ledger; expired leases remain
   reportable while logically absent (bytes and reported set differ only in retention).
5. **Default-parameter artifacts** — `default_resource`/`system`/test strings are excluded from
   metrics and replay evidence.
6. **Two-writer case (named acceptance)** — conflict names holder + intent; baton verified via
   `lease_id`.
7. **Strict-mode refusal + asymmetry (9.1.8)** — acquisition refused under stress with typed
   `VIOLATION_AHIMSA`; exact-owner release still admitted.
8. **Root binding** — an alternate/escaping root is refused when `WM_PROJECT_ROOT` is set.
9. **No-subprocess discovery** — ledger discovery is filesystem-only.
10. **Starvation-vs-refusal** — a refused acquisition under load is distinct from "no conflicts";
    reads stay open.

---

## 4. Ablation

| Mechanism | On | Off | Rung evidenced |
|---|---|---|---|
| Coordination link (two-writer replay) | journaled serialization/refusals | on-disk lost updates | EFFECTFUL (journal-only comparison) |
| Prune-on-read vs logically-absent | ledger bytes unchanged; expired reportable | pruned set differs | PERSISTENT |
| Test-artifact strip | zero real usage (negative control) | inflated adoption metrics | EXECUTED (evidence hygiene) |

Not claimed: EXTERNAL (no outside-system consequence for this row).

---

## 5. Acceptance + owner

Wrapper-side:

1. **Two-writer case** — conflict names holder + intent; exact-owner release verified via
   `lease_id`.
2. **Read-only discipline** — `check`/`list` leave ledger bytes unchanged (hash before/after);
   expired leases reportable.
3. **Typed-effect asymmetry** — strict stress refuses acquisition (`VIOLATION_AHIMSA`) and admits
   release.
4. **Root binding** — escaping root refused.
5. **Metrics hygiene** — defaults/test artifacts excluded; generated counts only.

**Owner:** unset — operator assigns at spec time.
**Exit:** frozen spec + wired adversarial cases + demonstrated ablation (where implemented) +
receipt; no inert acceptance test.

---

## 6. Freeze block (to complete)

- [ ] Owner assigned (operator): ______________________
- [ ] Operator ratification (signature below)
- [ ] Receipt landed: `receipts/W1_SPEC_B3_FREEZE_<date>.md`

Operator signature: ______________________  Date: ____________

**Amendment rule:** additive errata only; a new frozen revision with its own receipt. No code is
authorized by this spec alone.
