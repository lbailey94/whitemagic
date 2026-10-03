# RECEIPT — A/B engineering budget (opened at pre-registration freeze)

**Opened:** 2026-09-16 · controlled by `experiments/contradiction/PRE_REGISTRATION.md` §5.
Clock starts at the Phase-1 gate (= the pre-registration freeze, `PREREG_FREEZE_2026-09-16.md`).
Phase 0/1 construction work is pre-gate and **not charged**.

Rules: one session = one working block ≤ 4 h wall-clock, start/end recorded. 10 sessions per
arm. Overruns ≤ 2 sessions are permitted with a receipt (still match-eligible); beyond +2 =
loss on budget grounds. Same machine class, same data copies, same restart points, same harness.

| # | Arm | Date | Start–End | Duration | What ran | Note |
|---|---|---|---|---|---|---|
| 1 | control | 2026-09-16 | 17:01–17:02 EDT | ~0:05 | 5-seed A/B (T8 T1 T6 T2 T9), per-case | within budget |
| 2 | candidate | 2026-09-16 | 17:01–17:05 EDT | ~0:10 | 5-seed A/B + journal joins + analysis | within budget |
| — | — | — | — | — | — | *1 of 10 sessions used per arm; clock opened at freeze; construction pre-gate, not charged* |

## P2B — GEN3-P2B-PROJECTION-001 (clock opens at plan freeze, 2026-09-16)

Budget: 1 session per cell + 1 analysis (5 total); overruns ≤ 1 session; inconclusive within
30 days → paused, not extended.

| # | Cell | Date | Start–End | Duration | What ran | Note |
|---|---|---|---|---|---|---|
| 3 | C00 | 2026-09-16 | 17:28–17:31 EDT | ~0:04 | 5-seed cell (T8 T1 T6 T2) | within cap |
| 4 | C01 | 2026-09-16 | 17:31–17:36 EDT | ~0:05 | 5-seed cell + reproduction gate | within cap |
| 5 | C10 | 2026-09-16 | 17:36–17:42 EDT | ~0:06 | 5-seed cell | within cap |
| 6 | C11 | 2026-09-16 | 17:42–17:49 EDT | ~0:07 | 5-seed cell | within cap |
| 7 | analysis | 2026-09-16 | 17:49–17:50 EDT | ~0:02 | M1–M5 joins + report | within cap |
| flag | implementation | 2026-09-16 | ~16:55–17:26 EDT | ~0:30 | primitive build, battery, C01 reproduction, freeze | recorded outside the 5-session cell cap — flagged for operator accounting preference |

## P2C — GEN3-P2C-INTERACTION-001 (clock opens at plan+holdout freeze, 2026-09-16)

Budget: 4 cells × 5 holdout seeds + declared reproduction + analysis = 5 sessions; overruns
≤ 1; inconclusive within 30 days → paused. Implementation unchanged (no implementation session).

| # | Scope | Date | Start–End | Duration | What ran | Note |
|---|---|---|---|---|---|---|
| 1 | holdout cells | 2026-09-16 | ~18:00–18:05 EDT | ~0:06 | C00–C11 × seeds 6–10 | within cap |
| 2 | reproduction cells | 2026-09-16 | ~18:05–18:10 EDT | ~0:06 | C00–C11 × seeds 1–5 | within cap |
| 3 | analysis + report | 2026-09-16 | ~18:10–18:12 EDT | ~0:02 | interaction I, decomposition, costs | within cap |

## P2D — GEN3-P2D-ARBITRATION-001 (clock opens at plan+holdout freeze, 2026-09-16)

Budget: B0+B1+B2 × 5 seeds (11–15) + analysis = 4 sessions; overruns ≤ 1; inconclusive within
30 days → paused. Implementation session recorded separately (flagged), as in P2B.

| # | Scope | Date | Start–End | Duration | What ran | Note |
|---|---|---|---|---|---|---|
| 1 | B0/B1/B2 cells | 2026-09-16 | ~18:38–18:50 EDT | ~0:12 | 3 cells × seeds 11–15 | within cap |
| 2 | analysis + report | 2026-09-16 | ~18:50–18:53 EDT | ~0:03 | ΔReach/ΔOrdering + downstream | within cap |
| flag | implementation | 2026-09-16 | ~18:30–18:37 EDT | ~0:07 | arbitration selector + tests + regression proof + freeze | flagged outside cap |

## P2E — GEN3-P2E-DISPERSION-001 (clock opens at plan+holdout+audit freeze, 2026-09-16)

Budget: D0/D1 × 5 seeds (16–20) + analysis = 3 sessions; overruns ≤ 1; inconclusive within
30 days → paused. Implementation session recorded separately (flagged). R1 paused.

| # | Scope | Date | Start–End | Duration | What ran | Note |
|---|---|---|---|---|---|---|
| 1 | D0/D1 cells | 2026-09-16 | ~19:05–19:17 EDT | ~0:12 | 2 cells × seeds 16–20 | within cap |
| 2 | analysis (raw + adjudicated) | 2026-09-16 | ~19:17–19:22 EDT | ~0:05 | P1/P2, audit joins, swaps | within cap |
| flag | implementation | 2026-09-16 | ~18:55–19:04 EDT | ~0:09 | dispersion weighting + tests + regression + freeze | flagged outside cap |
