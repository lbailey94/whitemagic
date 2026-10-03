# Gate 9A article-evidence round — 2026-09-22

Status: article/attempt/regression evidence round by the continuation lane (opencode). Gate 9A
remains **OPEN** pending independent review and the closure verdict. All work is uncommitted on
top of `981b0bf`; candidate fingerprint:
`receipts/gate9a_article_evidence_20260922/source-manifest.sha256` (37/37 verified). Logs:
`receipts/gate9a_article_evidence_20260922/logs/`.

## What landed

Code and executable evidence (no production behavior changes beyond the derived-cache key):
- Evil Gana attempts 2/5/7: compile-fail doctests (`Store` has no public raw writer;
  `RemoteStimulus` has no authority conversion; the hologram has no method accepting a `Store`).
- Article 2: production admission refusal test (stimulus payload without local authority) and the
  production trace documented (transport accept → ingress schema → Ed25519 identity → lanes; the
  spawned thread holds no commit path).
- Article 3: no-bridge compile-fail plus a runtime test that committed remote-reported records
  never enter the calibration pool.
- Article 5 / attempt 6: `socket_address_never_authenticates_identity` (unregistered socket label
  refused, impersonated label refused, TOFU key positive).
- Article 7 / attempt 7: derived hologram canonical-invariance test with a real LMDB store;
  versioned derived-cache keys (`MODEL_ID:v{format}:{content hash}`) with invalidation, canonical
  invariance and projection-off no-write tests; policy in `docs/DERIVED_CACHE_POLICY.md`.
- Article 9: three acceptance tests — audit failure after commit (journal `/dev/full`), lost
  acknowledgement recovery with identical receipt, and no JSONL ledgers from production commits.
- Article 4: closure scan extended to `[3/3]` — no `thread::spawn`/`rayon::spawn` outside
  `transport.rs`.
- AMBER 2: explicit no-panic feasibility-accessor test (accessors were already `Option`/`Result`).
- Driver fix: `driver_peb9_5` count-robust assertion (matched capability set grew 4 → 10).

## Evidence

- Workspace suite (reference-models, ratified skips): 194 + 3 + 3 + 10 + 1 + 1 + 2 + 18 passed,
  0 failed, 1 ignored, 5 filtered — `logs/workspace-tests.log`.
- Focused: sweep 6, store 13, cache 3, identity 1, accessors 1, sizing 1, sweep acceptance 10,
  article9 acceptance 3 — `logs/focused-tests.log`.
- Driver form: **17/17 core drivers PASS** — `logs/drivers/summary.txt` (+ per-driver logs).
- Harness process-boundary scenarios: 9/9 — `logs/harness-scenarios.log`.
- Closure static scans PASS (now three rules) — `logs/closures.log`; no-default check and release
  build captured; `git diff --check` clean.
- Manifest 37/37 verified.

## Documents

- `docs/GATE_9A_COVERAGE_MAP_UPDATE_2026-09-22.md` — per-article/attempt/writer status update with
  executable evidence and AMBER dispositions.
- `docs/GATE_9A_M0_M8_DISPOSITIONS.md` — driver-form results and formal exclusions.
- `docs/DERIVED_CACHE_POLICY.md` — Article 7 cache boundary resolved as derived policy.
- `docs/GATE_9A_EXTERNAL_EFFECT_BOUNDARIES.md` — sweep row, cache resolution, acceptance items
  closed, hashes refreshed.
- `docs/PHASE4_ERRATA.md` batch N.1 (#67) — completion-claim conflict for the verdict to reconcile.

## Remaining before a verdict

1. Independent review of this round and the acceptance receipts (reviewer role).
2. Closure verdict reconciling historical "RATIFIED/COMPLETE" claims (errata #67), stating
   model/evolution exclusions, the compiler-module trust boundary, and the PEB-15 §8.2 split.
3. Registered follow-ons (not closure blockers): 9C cache GC/model migration/projection
   requalification and evolution receipts; 9D migration/power-loss qualification.

No commit or push was performed.
