# RECEIPT — Docs sweep batch 3 (milestone-era consistency audit) — 2026-09-19

**Status: audit landed (register-only; no artifact edited).** Operator authorization
(in-session): *"Docs fixes + errata log"*, *"Commit + receipt per update"*, *"let's continue on
with batches 2 and 3."* No verdict, claim, gate, or threshold movement.

---

## 1. Scope and method

- **Audited (8 registered artifacts, read-only):** `docs/GEN3_PHYSICS_AND_PHENOTYPE_EMERGENCE.md`
  (v1.2) · `docs/BENCHMARK_AND_VERIFICATION_PROTOCOL.md` (v1.0) ·
  `docs/MILESTONE_0_EXECUTION_MANIFEST.md` (sealed) · `docs/PREREGISTRATION_PEB13/14A/14B/14C/15_*.md`.
- **Evidence base:** `receipts/BENCHMARK_*.md` + `receipts/benchmark_*.json`, `benchmarks/`
  drivers, crate doc-comments/implementations (transport, ganying, hologram, relativity,
  geometry, bicameral, capability, contract, pulse, catuskoti, dream).
- **Method:** agent-assisted audit; the session spot-verified every high-impact claim before
  logging — `g3-crb-1` tag = `9cb10942a5c202140cf07d7038448482c4af2e11`; cited manifest commit
  `9cb109404c0ec54181f0bdf20067644917fa9f34` is a bad object in both repos; `#[test]` count at
  HEAD = 148 (no revision yields 143); `DIRICHLET_ALPHA_0 = 0.05` fixed; scenario-1 transport
  buffer = 1024 bytes (receipt "1024/1024"; "23 partial chunks"); bicameral fast path = composite
  `M ≥ 0.85` (no `top1−top2` anywhere).
- **Why no edits:** all eight are registered texts (frozen/sealed/ratified by commit + receipt;
  none carries a 64-hex pin). In-place edits would rewrite registrations; corrections require
  errata entries and, where substance is involved, explicit amendments (PEB-14A v1.1 precedent).

## 2. Landed

`docs/PHASE4_ERRATA.md` — section **K** added (items #48–52, covering the physics-spec drift,
protocol identity/scale issues, M0-host execution divergences, PEB-13/14A/14B/14C prereg-vs-
execution divergences, and PEB-15/Gate 9A status), plus an **operator disposition owed** list.
Title updated (batches A–K). sha256: `a648d1f3…` → `735ee7a5…`.

## 3. Disclosures / limits

- Audit coverage: ~23 candidate findings were consolidated into 5 register items; cosmetic-only
  candidates (e.g. prospective `src/bin/wm.rs` target) are noted inside items, not inflated.
- Milestone ratifications were operator acts; they stand unchanged until disposition — this audit
  changes no verdict by itself (`WEAK stays WEAK`).
- Nothing was re-run, re-tuned, or rebuilt; no store touched.
- The audit did not inspect `receipts/` bundles' internal evidence beyond their receipt texts and
  the referenced code paths.

## 4. Attestation

AI session (WMgen3 docs sweep, 2026-09-19) prepared this receipt; operator present and authorizing
in-session. Append-only; corrections create a new receipt referencing it.
