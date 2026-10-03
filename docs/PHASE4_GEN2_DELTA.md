# Phase 4 — Track A: Gen2 capability-source study (9.1.7 → 9.1.8)

**Status:** study · 2026-09-17 · **input to the Phase-4 wave plan.** Read-only research:
assigns no verdicts, changes no WMv9 code, authorizes no migration. Gate reminder: Phase-4
fusion waits on the Phase-3→4 nucleus freeze (`docs/NUCLEUS_FREEZE_CRITERIA.md`).

---

## 0. Reference-pin decision (operator direction, 2026-09-17)

| Role | Version | Why |
|---|---|---|
| **Experimental control** | **9.1.7** (frozen, hash-pinned) | Gen3 was measured against it; re-baselining experiments by accident is forbidden (`HANDOFF.md` §2) |
| **Capability-source reference** | **9.1.8** (latest released) | Phase-4 re-expression targets what Gen2 *is now*; contract regenerated at this release |

Conflating the two roles would quietly re-baseline the A/B. The control stays 9.1.7 forever;
capability dispositions cite 9.1.8 (and later releases as they land, appended below).

## 1. Delta summary

`v9.1.7` (`94b6420`) → `v9.1.8` (`c0e346a`), released 2026-09-17: **15 commits · 45 files ·
+2,855/−216.** Route surface unchanged (302); **declared schemas 70 → 85, undeclared 232 →
217** (contract remediations; manifest internal `version` field lags one release — it reads
`9.1.6` at the v9.1.7 tag and `9.1.7` at v9.1.8).

Themes: **coordination truth (AHIMSA Target A)**, **mesh ingest hardening (phase 1)**,
**onboarding/startup**, **contract declarations**, **truth hygiene**.

## 2. Change ledger

Relevance key: **N** nucleus content check · **T** adversarial-test material for migrations ·
**S** source/capability reference · **—** no Phase-4 relevance.

### 2.1 Coordination truth-up — AHIMSA Target A (`42cb1f5`)

| Change | What / why | Relevance |
|---|---|---|
| Typed coordination effects | `Resource::CoordinationLease` (claim/renew), `Resource::CoordinationRelease` (exact-owner cleanup) replace the generic filesystem declaration; strict mode refuses acquisition/renewal with typed `VIOLATION_AHIMSA` so system stress cannot trap new work; exact-owner release stays admitted so a held lease can always be freed | **N, T** — the "always releasable" asymmetry is exactly the kind of statute the nucleus snapshot must state honestly |
| Genuinely read-only ledger reads | `code.check`/`code.list` use `snapshot_readonly`: no lock, no temp file, no persisted expiry pruning; expired leases are logically absent and still reportable | **T** — read-only-discipline test case for any Gen3 coordination link |
| Root binding | `code.release` refuses an alternate/escaping `root` when `WM_PROJECT_ROOT` is configured; cleanup acts only on the configured repository's fixed ledger | **T** — scope-law case |
| No-discovery checkpoint | `session.checkpoint_nodiscovery` stores exactly the supplied handoff fields (commit, branch, tests_green, next_queue, open_flags, lease_id) with no repository discovery, filesystem reads, or subprocesses; the git-capturing `session.checkpoint` now truthfully declares its reads/spawns | **S, T** — the correct integration point for WMgen3 session rhythm (fixes the observed WMv9-HEAD capture quirk, 2026-09-17) |

### 2.2 Mesh ingest hardening — phase 1 (`8804b53`)

| Change | What / why | Relevance |
|---|---|---|
| Signed-only discovery | `PeerAnnounce` beacons carry and bind the signer key (`peer_id:tcp_addr:timestamp:key`); ingest verifies signatures, enforces `2 × interval` freshness + per-source rate limit, bounded replay cache records only signature-verified observations; TOFU-binds first sight and refuses later key changes for bound peers; legacy keyless beacons are address hints only | **S, T** — reference behavior for the mesh EXPERIMENT's two-gate boundary |
| Key separation | `WM_MESH_KEY` derives purpose-scoped subkeys via HKDF-SHA256 (`wm/mesh-identity/v1`, `wm/record-attestation/v1`; `wm/release-signing/v1` reserved); one-release dual-verify keeps legacy XOR-fold identity + beacon payload during migration | **T** — migration-window discipline (additive, dual-verify, then retire) |

### 2.3 Contract declarations (`bac3fda`, `1ead0bb`, regenerations `3b892b7`/`62936b6`/`fd24acc`)

| Change | What / why | Relevance |
|---|---|---|
| `agent.*` schemas + meta-boundary enforcement | declares agent.* input schemas; enforces `name`/`agent_id` at the meta boundary | **S** — declared-surface truth for km/tools |
| `web.*`, `code.graph`/`query`/`affected_by` schemas | closes undeclared routes | **S** |
| `kg.query` `entity` required | declared unconditional read | — |
| Manifest regenerations | route schema manifest regenerated after each declaration batch | **S** — 85 declared is the new baseline for surface comparisons |

### 2.4 Onboarding / startup (`c4bcbde`, `cff34a0`)

| Change | What / why | Relevance |
|---|---|---|
| `wm grimoire load` + startup guidance | ingest ledger surfaced; `wm ingest --source <folder> --dry-run` → `--redact`; path named in quickstart/status/MCP instructions/skill.md; loading optional, never gates readiness | **S** — the stranger-lane/first-run mechanics (metabolism); not substrate |
| Startup-under-stress fixtures | spawned-binary healthy start; governance refusal (`VIOLATION_AHIMSA`) and first-run starvation (typed `WM_HOMEOSTASIS_FROZEN`) kept distinct; reads open under starvation | **T** — stress-behavior fixtures worth mirroring in Gen3 adversarial suites |

### 2.5 Truth hygiene (`65152f9`, `82926f0`, `6e51365`, `e1ea07f`)

Changelog corrections (9.1.7 report entry, test-count reconciled to the release manifest), a
docs-vs-shipped truth pass, and a guard allowlist for the RFC 5869 HKDF test vector. Relevance
**—**, except as a reminder that quoted counts must come from generated artifacts (the project's
oldest failure mode).

## 3. Phase-4 implications

1. **Nucleus content check (N):** align the statutory baseline with the 9.1.8 coordination
   semantics — typed effects for coordination, strict refusal of acquisition, always-admitted
   exact-owner release, read-only ledger reads, root binding. If the nucleus §1 statutory
   section cannot state these, the snapshot is incomplete.
2. **Adversarial test material (T):** the designated 9.1.7 fix list gains 9.1.8 cases —
   strict-mode refusal behavior, no-subprocess discovery (9.1.9 F3), checkpoint-nodiscovery
   semantics, signed-only beacon ingest, read-only discipline, starvation-vs-refusal
   distinction. Each migration's frozen spec should include these.
3. **Migration notes by verdict (S):**
   - Coordination (PRESERVE→link): the link must not bypass typed effects; the asymmetry rule
     (work may be refused under stress, release never is) is part of the contract.
   - Sessions (PRESERVE→link): adopt `session.checkpoint_nodiscovery` in the WMgen3 session
     rhythm — ends the WMv9-HEAD capture quirk.
   - Mesh (EXPERIMENT): phase-1 hardening is the reference behavior for the two-gate boundary.
   - Surfaces generally: 85-declared is the truth baseline for comparisons.
4. **9.1.9 watch list:** F3 (`code.*` git-common-dir resolution without subprocess; effect-row
   truth) and F4 (release tooling orchestration). Append on release.

## 4. What this study does not do

No WMv9 writes; no verdict changes; no control re-baseline; no migration authorization.
Track B (`PHASE4_GEN1_TREE.md`) supplies the source-side tree; the wave plan joins them.
